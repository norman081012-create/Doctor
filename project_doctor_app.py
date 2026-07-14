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
    return "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])

def generate_medical_record(api_key, selected_model, age, gender, medical_history, habits):
    record_prompt = config.get_medical_record_prompt(
        age=age, gender=gender, medical_history=medical_history, habits=habits,
        chat_history=build_chat_context(),
        soap_xml=st.session_state.current_soap_xml
    )
    return engine.generate_raw_text(api_key, selected_model, config.MEDICAL_RECORD_SYSTEM_PROMPT, record_prompt)

def run_engine_turn(api_key, selected_model, age, gender, medical_history, habits, user_input, physical_tags="無"):
    sys_prompt = config.get_system_prompt(mode="v2_5_engine")
    
    # 讀取「全部」歷史對話
    chat_context = build_chat_context()
    
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
    
    # ===== 攔截層 1：Phase 4 完成旗標 =====
    if dash.get("consultation_complete"):
        st.session_state.locked = True
        _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits)
        return LOCK_MESSAGE
    
    # ===== 攔截層 2：守門員 Agent（僅於 Phase 3 / Phase 4 啟動，節省配額）=====
    current_phase = dash.get("current_phase", "")
    if ("Phase 3" in current_phase or "Phase 4" in current_phase) and chat_text.strip():
        if engine.run_diagnosis_guard(api_key, selected_model, chat_text):
            st.session_state.locked = True
            _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits)
            return LOCK_MESSAGE
        
    return chat_text

def _auto_generate_record(api_key, selected_model, age, gender, medical_history, habits):
    """鎖定時自動生成病歷。失敗不阻斷鎖定流程，可事後手動按鈕重生。"""
    try:
        st.session_state.medical_record = generate_medical_record(
            api_key, selected_model, age, gender, medical_history, habits
        )
    except Exception:
        pass

def main():
    setup_page()
    
    if "initialized" not in st.session_state: st.session_state.initialized = False
    if "messages" not in st.session_state: st.session_state.messages = []
    if "current_soap_xml" not in st.session_state: st.session_state.current_soap_xml = ""
    if "parsed_dash" not in st.session_state: st.session_state.parsed_dash = {}
    if "locked" not in st.session_state: st.session_state.locked = False
    if "medical_record" not in st.session_state: st.session_state.medical_record = ""
        
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
                st.rerun()

    # ===== 頁面底部固定輸入框 =====
    # st.chat_input 在頂層呼叫時會自動釘在視窗最下方；放進 column 內會變成內嵌元件。
    if st.session_state.initialized and not st.session_state.locked:
        if prompt := st.chat_input("請在此輸入病患的回覆..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("四維度透視引擎掃描中..."):
                reply_text = run_engine_turn(
                    api_key, selected_model, age, gender, medical_history, habits,
                    user_input=prompt,
                    physical_tags="無新數據"
                )
                st.session_state.messages.append({"role": "assistant", "content": reply_text})
            st.rerun()

if __name__ == "__main__":
    main()
