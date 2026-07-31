# ==========================================
# project_doctor_app.py (v4.0 — 整合六階段鑑別診斷推演鏈)
# ==========================================
import time
import streamlit as st
from google.api_core.exceptions import ResourceExhausted
import project_doctor_config as config
import project_doctor_engine as engine

LOCK_MESSAGE = "本次問診的資料收集已經完成，謝謝您的配合。請您先回候診區稍候，詳細的診斷結果與後續處置，將由診間醫師當面為您說明。"
QUOTA_MESSAGE = (
    "⛔ **API 配額耗盡（429 ResourceExhausted）**，已重試多次仍失敗。\n\n"
    "第一次呼叫就撞 429，通常代表：\n"
    "1. 該模型的**當日免費配額 (RPD) 已用完** — 等到太平洋時間午夜重置，或改用付費金鑰；\n"
    "2. 所選模型（pro / preview 系列）free-tier 額度極低 — 建議左側改選 **flash 系列**模型再試。\n\n"
    "本輪輸入未被消耗，狀態已保留，可直接重試。"
)

DX_CHAIN_STAGES = [
    ("agent1", "① 急症篩查"),
    ("agent2", "② 受累系統"),
    ("agent3", "③ 臆診"),
    ("step4", "④ 病理機轉"),
    ("step5", "⑤ 側向機轉擴展"),
    ("step6", "⑥ 機轉導向鑑別"),
]

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
    """完整對話（病歷生成 + Dx Chain 皆使用此完整紀錄）"""
    return "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])

def format_dx_chain_output(chain_result):
    """把六階段結果串成一個文字區塊，餵給主引擎 Phase 2 narrowing 使用，也供病歷生成參考。"""
    if not chain_result or not any(chain_result.values()):
        return ""
    parts = []
    for key, label in DX_CHAIN_STAGES:
        val = (chain_result.get(key) or "").strip()
        if val:
            parts.append(f"【{label}】\n{val}")
    return "\n\n".join(parts)

def run_dx_chain(api_key, selected_model, age, gender, medical_history, habits):
    """
    鑑別診斷推演鏈：六個獨立 Agent 依序呼叫，每個 Agent 都能看到完整醫病對話紀錄
   （而非 rolling XML 摘要），後一階段的輸入包含前面所有階段的輸出，形成鏈式依賴。
    fail-soft：任一階段失敗即在該階段中斷，回傳已取得的部分結果，不阻斷主流程
    （主引擎會在鏈輸出不完整甚至全空時，退回「依 Phase 1 所見自行初步列出候選」）。
    """
    chat_history = build_chat_context()
    result = {"agent1": "", "agent2": "", "agent3": "", "step4": "", "step5": "", "step6": ""}

    try:
        result["agent1"] = engine.generate_raw_text(
            api_key, selected_model, config.DX_CHAIN_AGENT1_SYSTEM_PROMPT,
            config.get_dx_chain_agent1_prompt(age, gender, medical_history, habits, chat_history)
        )
    except Exception:
        return result

    try:
        result["agent2"] = engine.generate_raw_text(
            api_key, selected_model, config.DX_CHAIN_AGENT2_SYSTEM_PROMPT,
            config.get_dx_chain_agent2_prompt(age, gender, medical_history, habits, chat_history, result["agent1"])
        )
    except Exception:
        return result

    try:
        result["agent3"] = engine.generate_raw_text(
            api_key, selected_model, config.DX_CHAIN_AGENT3_SYSTEM_PROMPT,
            config.get_dx_chain_agent3_prompt(age, gender, medical_history, habits, chat_history, result["agent1"], result["agent2"])
        )
    except Exception:
        return result

    try:
        result["step4"] = engine.generate_raw_text(
            api_key, selected_model, config.DX_CHAIN_STEP4_SYSTEM_PROMPT,
            config.get_dx_chain_step4_prompt(age, gender, medical_history, habits, chat_history, result["agent3"])
        )
    except Exception:
        return result

    try:
        result["step5"] = engine.generate_raw_text(
            api_key, selected_model, config.DX_CHAIN_STEP5_SYSTEM_PROMPT,
            config.get_dx_chain_step5_prompt(age, gender, medical_history, habits, chat_history, result["step4"])
        )
    except Exception:
        return result

    try:
        result["step6"] = engine.generate_raw_text(
            api_key, selected_model, config.DX_CHAIN_STEP6_SYSTEM_PROMPT,
            config.get_dx_chain_step6_prompt(age, gender, medical_history, habits, chat_history, result["step5"])
        )
    except Exception:
        return result

    return result

def generate_medical_record(api_key, selected_model, age, gender, medical_history, habits):
    dx_chain_summary = format_dx_chain_output(st.session_state.get("dx_chain_result", {}))
    record_prompt = config.get_medical_record_prompt(
        age=age, gender=gender, medical_history=medical_history, habits=habits,
        chat_history=build_chat_context(),
        soap_xml=st.session_state.current_soap_xml,
        dx_chain_summary=dx_chain_summary
    )
    return engine.generate_raw_text(api_key, selected_model, config.MEDICAL_RECORD_SYSTEM_PROMPT, record_prompt)

def run_engine_turn(api_key, selected_model, age, gender, medical_history, habits, user_input):
    sys_prompt = config.get_system_prompt(mode="v4_engine")

    # ===== 若上一輪已回報進入 Phase 2，本輪先跑鑑別診斷推演鏈（六階段），
    #       鏈輸出（本輪、基於完整對話紀錄重新生成）餵給主引擎做 narrowing =====
    prev_phase = st.session_state.get("parsed_dash", {}).get("current_phase", "")
    dx_chain_text = ""
    if "Phase 2" in prev_phase:
        chain_result = run_dx_chain(api_key, selected_model, age, gender, medical_history, habits)
        st.session_state.dx_chain_result = chain_result
        dx_chain_text = format_dx_chain_output(chain_result)

    # 累積記憶完全由 rolling XML 承載；病患回覆已內含對應題目（問題 → 答案）
    forced_prompt = config.get_forced_template(
        age=age, gender=gender, medical_history=medical_history, habits=habits,
        previous_soap=st.session_state.current_soap_xml,
        user_input=user_input,
        dx_chain_output=dx_chain_text
    )
    
    raw_response = engine.generate_raw_text(api_key, selected_model, sys_prompt, forced_prompt)
    parsed_reply = engine.parse_chat_response(raw_response)
    
    if parsed_reply["raw_xml"]:
        st.session_state.current_soap_xml = parsed_reply["raw_xml"]
        st.session_state.parsed_dash = parsed_reply["parsed_dash"]
    
    chat_text = parsed_reply["chat_text"]
    dash = parsed_reply["parsed_dash"]
    st.session_state.form_round += 1
    
    # ===== 攔截層 1：問診完成旗標 =====
    if dash.get("consultation_complete"):
        st.session_state.locked = True
        st.session_state.current_questions = []
        _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits)
        return LOCK_MESSAGE
    
    # ===== 攔截層 2：守門員 Agent（Phase 2 才會涉及鑑別診斷 narrowing，才有洩漏風險，於此啟動）=====
    current_phase = dash.get("current_phase", "")
    if "Phase 2" in current_phase and chat_text.strip():
        if engine.run_diagnosis_guard(api_key, selected_model, chat_text):
            st.session_state.locked = True
            st.session_state.current_questions = []
            _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits)
            return LOCK_MESSAGE
    
    # ===== Stage 2：問句掃描器 — 把口語回覆拆解成表單題目 =====
    scanner_sys = getattr(config, "QUESTION_SCANNER_SYSTEM_PROMPT", None)
    scanner_builder = getattr(config, "get_question_scanner_prompt", None)
    if scanner_sys and scanner_builder:
        qs = engine.run_question_scanner(
            api_key, selected_model, scanner_sys, scanner_builder(chat_text)
        )
        if not qs:
            # 機械保險：scanner 失敗（解析失敗或配額耗盡）時，直接從口語抓問句
            qs = engine.extract_questions_from_chat(chat_text)
        st.session_state.current_questions = qs
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


def render_chat_history():
    """渲染對話紀錄；醫師回覆下方顯示該輪引擎推演耗時。"""
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            st.caption(f"🔧 _{msg['content']}_")
        else:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("elapsed") is not None:
                    st.caption(f"⏱️ 本輪推演耗時 {msg['elapsed']:.1f} 秒")


def render_dx_chain_panel():
    """右側面板：顯示本輪鑑別診斷推演鏈的六階段輸出。"""
    with st.expander("🔗 鑑別診斷推演鏈（六階段）", expanded=False):
        chain = st.session_state.get("dx_chain_result", {})
        if chain and any(chain.values()):
            for key, label in DX_CHAIN_STAGES:
                val = (chain.get(key) or "").strip()
                if val:
                    st.markdown(f"**{label}**")
                    st.code(val, language="text")
        else:
            st.info("尚未啟動 — Phase 1 完成、進入 Phase 2 後，下一輪會自動執行。")


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
    if "dx_chain_result" not in st.session_state: st.session_state.dx_chain_result = {}
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.title("🩺 臨床動態問診工作區")
        st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v4.0（含六階段鑑別診斷推演鏈）")
        st.divider()
        
        if not st.session_state.initialized:
            st.info("💡 請於左側填寫病患基本背景與**主訴**，隨後啟動初始推演。")
            if st.button("🚀 啟動 Doubt-Driven 引擎", use_container_width=True, type="primary"):
                if not api_key or not selected_model or not chief_complaint.strip():
                    st.error("❌ 請確保已輸入 API 金鑰、選擇模型並填寫主訴！")
                else:
                    with st.spinner("正在建立認知空間並進行症狀頻譜展延..."):
                        st.session_state.messages.append({"role": "user", "content": f"【主訴】{chief_complaint.strip()}"})
                        t0 = time.perf_counter()
                        try:
                            reply_text = run_engine_turn(
                                api_key, selected_model, age, gender, medical_history, habits,
                                user_input=chief_complaint.strip()
                            )
                        except ResourceExhausted:
                            st.session_state.messages.pop()  # 回滾，避免重試時主訴重複入列
                            st.error(QUOTA_MESSAGE)
                        else:
                            elapsed = time.perf_counter() - t0
                            st.session_state.messages.append({"role": "assistant", "content": reply_text, "elapsed": elapsed})
                            st.session_state.initialized = True
                            st.rerun()
        elif st.session_state.locked:
            st.warning("🔒 **問診已鎖定** — 資料收集完成或引擎嘗試對病患下診斷，已由守門員攔截。請病患繼續候診，後續以診間醫師為主。")
            st.markdown("### 💬 對話紀錄")
            render_chat_history()
        else:
            st.markdown("### 💬 對話紀錄")
            render_chat_history()

            # ===== 作答區：緊鄰最後一輪對話 =====
            patient_reply = render_answer_form()
            if patient_reply:
                st.session_state.messages.append({"role": "user", "content": patient_reply})
                with st.spinner("四維度透視引擎掃描中（Phase 2 起會先跑六階段鑑別診斷推演鏈）..."):
                    t0 = time.perf_counter()
                    try:
                        reply_text = run_engine_turn(
                            api_key, selected_model, age, gender, medical_history, habits,
                            user_input=patient_reply
                        )
                    except ResourceExhausted:
                        st.session_state.messages.pop()  # 回滾，rolling XML 未被更新，狀態一致
                        st.error(QUOTA_MESSAGE)
                    else:
                        elapsed = time.perf_counter() - t0
                        st.session_state.messages.append({"role": "assistant", "content": reply_text, "elapsed": elapsed})
                        st.rerun()

    with col_right:
        st.subheader("⚙️ 引擎底層認知狀態")
        st.caption("即時解析內部推演結果")
        st.divider()
        
        d = st.session_state.parsed_dash
        current_phase = d.get("current_phase", "等待推演...")
        
        st.markdown(f"**當前判定階段：** `{current_phase}`")
        
        with st.expander("內部推演原始碼 (Internal XML)", expanded=True):
            raw_xml = st.session_state.get("current_soap_xml", "")
            if raw_xml.strip():
                st.code(raw_xml, language="xml")
            else:
                st.info("尚無推演資料")

        render_dx_chain_panel()

        st.divider()
        
        if st.session_state.initialized:
            # ===== 病歷生成區 =====
            st.subheader("📄 病歷 (SOAP)")
            if st.button("✍️ 依目前對話生成病歷", use_container_width=True):
                with st.spinner("病歷書寫引擎彙整中..."):
                    try:
                        t0 = time.perf_counter()
                        st.session_state.medical_record = generate_medical_record(
                            api_key, selected_model, age, gender, medical_history, habits
                        )
                        st.toast(f"⏱️ 病歷生成完成，耗時 {time.perf_counter() - t0:.1f} 秒")
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
                st.session_state.dx_chain_result = {}
                st.rerun()

if __name__ == "__main__":
    main()
