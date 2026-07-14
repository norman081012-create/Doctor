# ==========================================
# project_doctor_app.py (v2.5 修復顯示版)
# ==========================================
import streamlit as st
import project_doctor_config as config
import project_doctor_engine as engine

LOCK_MESSAGE = "本次問診的資料收集已經完成，謝謝您的配合。請您先回候診區稍候，詳細的診斷結果與後續處置，將由診間醫師當面為您說明。"

def setup_page():
    st.set_page_config(page_title="Doubt-Driven 臨床認知博弈控制台", layout="wide", initial_sidebar_state="expanded")

def render_sidebar():
    with st.sidebar:
        st.title("⚙️ 臨床博弈控制台")
        api_key = st.text_input("🔑 Gemini API 金鑰", value="", type="password", placeholder="請貼上您的 API 金鑰")
        
        selected_model = None
        if api_key:
            if "available_models" not in st.session_state or not st.session_state.available_models:
                with st.spinner("正在向 Google 請求可用模型..."):
                    st.session_state.available_models = engine.fetch_available_models(api_key)

            if st.session_state.available_models:
                default_idx = 0
                for i, m in enumerate(st.session_state.available_models):
                    if "gemini-3.1-pro-preview" in m.lower():
                        default_idx = i
                        break
                    elif "gemini-1.5-pro" in m.lower() and default_idx == 0:
                        default_idx = i
                
                selected_model = st.selectbox("🤖 選擇運算核心 (Model)", st.session_state.available_models, index=default_idx)
            else:
                st.error("未發現可用模型，請確認 API 金鑰是否正確。")
        
        st.markdown("---")
        st.markdown("### 📋 病患基本生理與病史背景")
        age = st.number_input("年齡", min_value=0, max_value=120, value=40, step=1)
        gender = st.selectbox("性別", ["男性", "女性", "多元性別"], index=0)
        history_presets = st.multiselect("既往病史項目 (預設無)", ["無", "高血壓", "高血糖", "高血脂", "糖尿病", "心臟疾病", "氣喘"], default=["無"])
        history_custom = st.text_input("自訂其他既往病史", value="")
        active_histories = [h for h in history_presets if h != "無"]
        if history_custom.strip():
            active_histories.append(history_custom.strip())
        final_history = "、".join(active_histories) if active_histories else "無特殊病史"
        habits_presets = st.multiselect("生活習慣 / 接觸史", ["吸菸史", "飲酒史", "嚼檳榔史"], default=[])
        final_habits = "、".join(habits_presets) if habits_presets else "無特殊不良嗜好"
        chief_complaint = st.text_area("⚠️ 病患主訴 (必填)", value="", placeholder="例：胸悶且陣發性心悸兩天...")

        return (api_key, selected_model, age, gender, final_history, final_habits, chief_complaint)

def build_chat_context():
    """完整對話（僅供病歷生成使用）"""
    return "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])

def build_last_turn_context():
    """僅取上一輪醫師提問（引擎推演使用；累積記憶由 XML 承載）"""
    for m in reversed(st.session_state.messages):
        if m["role"] == "assistant":
            return f"醫師上一句提問：{m['content']}"
    return "無 (初診啟動)"

def generate_medical_record(api_key, selected_model, age, gender, medical_history, habits):
    record_prompt = config.get_medical_record_prompt(
        age=age, gender=gender, medical_history=medical_history, habits=habits,
        chat_history=build_chat_context(),
        soap_xml=st.session_state.current_soap_xml
    )
    return engine.generate_raw_text(api_key, selected_model, config.MEDICAL_RECORD_SYSTEM_PROMPT, record_prompt)

def run_engine_turn(api_key, selected_model, age, gender, medical_history, habits, user_input, physical_tags="無"):
    sys_prompt = config.get_system_prompt(mode="v2_5_engine")
    
    # 只讀上一句醫師提問；完整累積記憶改由 rolling XML 承載
    chat_context = build_last_turn_context()
    
    forced_prompt = config.get_forced_template(
        age=age, gender=gender, medical_history=medical_history, habits=habits,
        previous_soap=st.session_state.current_soap_xml,
        chat_history=chat_context,
        user_input=user_input,
        physical_tags=physical_tags
    )
    
    raw_response = engine.generate_raw_text(api_key, selected_model, sys_prompt, forced_prompt)
    parsed_reply = engine.parse_chat_response(raw_response)
    
    if parsed_reply["raw_xml"]:
        st.session_state.current_soap_xml = parsed_reply["raw_xml"]
        st.session_state.parsed_dash = parsed_reply["parsed_dash"]
    
    chat_text = parsed_reply["chat_text"]
    dash = parsed_reply["parsed_dash"]
    st.session_state.form_round += 1
    
    # ===== 攔截層 1：Phase 4 完成旗標 =====
    if dash.get("consultation_complete"):
        st.session_state.locked = True
        st.session_state.current_questions = []
        _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits)
        return LOCK_MESSAGE
    
    # ===== 攔截層 2：守門員 Agent（僅於 Phase 3 / Phase 4 啟動，節省配額）=====
    current_phase = dash.get("current_phase", "")
    if ("Phase 3" in current_phase or "Phase 4" in current_phase) and chat_text.strip():
        if engine.run_diagnosis_guard(api_key, selected_model, chat_text):
            st.session_state.locked = True
            st.session_state.current_questions = []
            _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits)
            return LOCK_MESSAGE
    
    # ===== Stage 2：問句掃描器 — 把口語回覆拆解成表單題目 =====
    scanner_sys = getattr(config, "QUESTION_SCANNER_SYSTEM_PROMPT", None)
    scanner_builder = getattr(config, "get_question_scanner_prompt", None)
    if scanner_sys and scanner_builder:
        st.session_state.current_questions = engine.run_question_scanner(
            api_key, selected_model, scanner_sys, scanner_builder(chat_text)
        )
    else:
        # config 版本過舊（缺 Stage 2 prompt）：退回自由文字作答，不讓整個 app 掛掉
        st.session_state.current_questions = []
        st.warning("⚠️ config 版本過舊，未找到 Stage 2 問句掃描器 prompt，本輪退回文字作答。請更新 project_doctor_config.py。")
    
    return chat_text

def _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits):
    """鎖定時自動生成病歷。失敗不阻斷鎖定流程，可事後手動按鈕重生。"""
    try:
        st.session_state.medical_record = generate_medical_record(
            api_key, selected_model, age, gender, medical_history, habits
        )
    except Exception:
        pass

def render_answer_form():
    """緊鄰最後一輪對話的作答區：是非題用勾選、補述用打字、送出必須按鈕。
    回傳組好的病患回覆字串；未送出則回傳 None。"""
    questions = st.session_state.get("current_questions", [])
    rnd = st.session_state.get("form_round", 0)

    st.markdown("---")
    st.markdown("#### 📝 請回覆上述問題")

    with st.form(key=f"answer_form_{rnd}", clear_on_submit=False):
        answers = []

        if questions:
            for i, q in enumerate(questions):
                if q["type"] == "yn":
                    choice = st.radio(
                        f"**{i+1}. {q['text']}**",
                        options=["是", "否", "不確定"],
                        index=None,
                        horizontal=True,
                        key=f"q_{rnd}_{i}",
                    )
                    extra = st.text_input(
                        "補充說明（可留空）",
                        key=f"qx_{rnd}_{i}",
                        placeholder="若需補述細節請在此填寫",
                        label_visibility="collapsed",
                    )
                    answers.append({"text": q["text"], "ans": choice, "extra": extra})
                else:
                    val = st.text_area(
                        f"**{i+1}. {q['text']}**",
                        key=f"q_{rnd}_{i}",
                        height=80,
                        placeholder="請在此描述…",
                    )
                    answers.append({"text": q["text"], "ans": val, "extra": ""})
        else:
            # 防呆：模型未輸出結構化問題時，退回純文字作答
            st.caption("（本輪未取得結構化題目，請直接以文字回覆）")
            val = st.text_area("您的回覆", key=f"q_{rnd}_free", height=100)
            answers.append({"text": "自由回覆", "ans": val, "extra": ""})

        supplement = st.text_area(
            "其他想補充的事（可留空）",
            key=f"supp_{rnd}",
            height=68,
            placeholder="任何上面沒問到、但您覺得該讓醫師知道的事",
        )

        submitted = st.form_submit_button("✅ 送出回覆", use_container_width=True, type="primary")

    if not submitted:
        return None

    # 驗證：是非題必須作答
    unanswered = [a["text"] for a in answers if a["ans"] is None or str(a["ans"]).strip() == ""]
    if unanswered:
        st.error("⚠️ 以下問題尚未回答：\n\n" + "\n".join(f"- {t}" for t in unanswered))
        return None

    lines = []
    for a in answers:
        line = f"{a['text']} → {a['ans']}"
        if a["extra"].strip():
            line += f"（補充：{a['extra'].strip()}）"
        lines.append(line)
    if supplement.strip():
        lines.append(f"【其他補充】{supplement.strip()}")

    return "\n".join(lines)


def main():
    setup_page()
    
    if "initialized" not in st.session_state: st.session_state.initialized = False
    if "messages" not in st.session_state: st.session_state.messages = []
    if "current_soap_xml" not in st.session_state: st.session_state.current_soap_xml = ""
    if "parsed_dash" not in st.session_state: st.session_state.parsed_dash = {}
    if "locked" not in st.session_state: st.session_state.locked = False
    if "medical_record" not in st.session_state: st.session_state.medical_record = ""
    if "current_questions" not in st.session_state: st.session_state.current_questions = []
    if "form_round" not in st.session_state: st.session_state.form_round = 0
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.title("🩺 臨床動態問診工作區")
        st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v2.5")
        st.divider()
        
        if not st.session_state.initialized:
            st.info("💡 請於左側填寫病患基本背景與**主訴**，隨後啟動初始推演。")
            if st.button("🚀 啟動 Doubt-Driven 引擎", use_container_width=True, type="primary"):
                if not api_key or not selected_model or not chief_complaint.strip():
                    st.error("❌ 請確保已輸入 API 金鑰、選擇模型並填寫主訴！")
                else:
                    with st.spinner("正在建立認知空間並進行症狀頻譜展延..."):
                        st.session_state.messages.append({"role": "user", "content": f"【主訴】{chief_complaint.strip()}"})
                        reply_text = run_engine_turn(
                            api_key, selected_model, age, gender, medical_history, habits,
                            user_input=chief_complaint.strip(), physical_tags="無 (初診狀態)"
                        )
                        st.session_state.messages.append({"role": "assistant", "content": reply_text})
                        st.session_state.initialized = True
                        st.rerun()
        elif st.session_state.locked:
            st.warning("🔒 **問診已鎖定** — 資料收集完成或引擎嘗試對病患下診斷，已由守門員攔截。請病患繼續候診，後續以診間醫師為主。")
            st.markdown("### 💬 對話紀錄")
            for msg in st.session_state.messages:
                if msg["role"] == "system":
                    st.caption(f"🔧 _{msg['content']}_")
                else:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
        else:
            st.markdown("### 💬 對話紀錄")
            for msg in st.session_state.messages:
                if msg["role"] == "system":
                    st.caption(f"🔧 _{msg['content']}_")
                else:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            # ===== 作答區：緊鄰最後一輪對話 =====
            patient_reply = render_answer_form()
            if patient_reply:
                st.session_state.messages.append({"role": "user", "content": patient_reply})
                with st.spinner("四維度透視引擎掃描中..."):
                    reply_text = run_engine_turn(
                        api_key, selected_model, age, gender, medical_history, habits,
                        user_input=patient_reply,
                        physical_tags="無新數據"
                    )
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                st.rerun()

    with col_right:
        st.subheader("⚙️ 引擎底層認知狀態")
        st.caption("即時解析內部推演結果")
        st.divider()
        
        d = st.session_state.parsed_dash
        current_phase = d.get("current_phase", "等待推演...")
        
        st.markdown(f"**當前判定階段：** `{current_phase}`")
        
        with st.expander("內部推演原始碼 (Internal XML)", expanded=True):
            # 【修復點】：改用 st.code() 並直接調用完整的 session_state.current_soap_xml
            raw_xml = st.session_state.get("current_soap_xml", "")
            if raw_xml.strip():
                st.code(raw_xml, language="xml")
            else:
                st.info("尚無推演資料")
            
        st.divider()
        
        if st.session_state.initialized:
            # ===== 病歷生成區 =====
            st.subheader("📄 病歷 (SOAP)")
            if st.button("✍️ 依目前對話生成病歷", use_container_width=True):
                with st.spinner("病歷書寫引擎彙整中..."):
                    try:
                        st.session_state.medical_record = generate_medical_record(
                            api_key, selected_model, age, gender, medical_history, habits
                        )
                    except Exception as e:
                        st.error(f"病歷生成失敗：{e}")
            
            if st.session_state.medical_record:
                with st.expander("候診預問診病歷", expanded=True):
                    st.markdown(st.session_state.medical_record)
                st.download_button(
                    "⬇️ 下載病歷 (Markdown)",
                    data=st.session_state.medical_record,
                    file_name="pre_consultation_record.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            st.divider()
            if st.button("🔄 重置病患狀態，啟動全新問診", use_container_width=True):
                st.session_state.initialized = False
                st.session_state.messages = []
                st.session_state.current_soap_xml = ""
                st.session_state.parsed_dash = {}
                st.session_state.locked = False
                st.session_state.medical_record = ""
                st.session_state.current_questions = []
                st.session_state.form_round = 0
                st.rerun()

if __name__ == "__main__":
    main()
