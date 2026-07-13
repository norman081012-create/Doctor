# ==========================================
# project_doctor_app.py (v2.4 無病歷/純推演版)
# ==========================================
import streamlit as st
import project_doctor_config as config
import project_doctor_engine as engine

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

def run_engine_turn(api_key, selected_model, age, gender, medical_history, habits, user_input, physical_tags="無"):
    sys_prompt = config.get_system_prompt(mode="v2_4_engine")
    
    # 讀取「全部」歷史對話
    chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
    
    # v2.4 已移除 previous_soap 參數
    forced_prompt = config.get_forced_template(
        age=age, 
        gender=gender, 
        medical_history=medical_history, 
        habits=habits,
        chat_history=chat_context,
        user_input=user_input,
        physical_tags=physical_tags
    )
    
    raw_response = engine.generate_raw_text(api_key, selected_model, sys_prompt, forced_prompt)
    parsed_reply = engine.parse_chat_response(raw_response)
    
    # v2.4 引擎回傳的是 engine_status，不再是 parsed_dash
    if "engine_status" in parsed_reply:
        st.session_state.engine_status = parsed_reply["engine_status"]
        
    return parsed_reply["chat_text"]

def main():
    setup_page()
    
    if "initialized" not in st.session_state: st.session_state.initialized = False
    if "messages" not in st.session_state: st.session_state.messages = []
    # 移除 current_soap_xml 與 parsed_dash，改為追蹤 engine_status
    if "engine_status" not in st.session_state: st.session_state.engine_status = {}
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_left, col_right = st.columns([3, 1])
    
    # ==========================================
    # 【左側欄位】動態問診
    # ==========================================
    with col_left:
        st.title("🩺 臨床動態問診工作區")
        st.caption("基於 Doubt-Driven 五階段問診引擎 v2.4")
        st.divider()
        
        if not st.session_state.initialized:
            st.info("💡 請於左側填寫病患基本背景與**主訴**，隨後啟動初始推演。")
            if st.button("🚀 啟動 Doubt-Driven 引擎", use_container_width=True, type="primary"):
                if not api_key or not selected_model or not chief_complaint.strip():
                    st.error("❌ 請確保已輸入 API 金鑰、選擇模型並填寫主訴！")
                else:
                    with st.spinner("引擎啟動中，進行症狀頻譜展延..."):
                        st.session_state.messages.append({"role": "user", "content": f"【主訴】{chief_complaint.strip()}"})
                        reply_text = run_engine_turn(
                            api_key, selected_model, age, gender, medical_history, habits,
                            user_input=chief_complaint.strip(), physical_tags="無 (初診狀態)"
                        )
                        st.session_state.messages.append({"role": "assistant", "content": reply_text})
                        st.session_state.initialized = True
                        st.rerun()
        else:
            # --- 病患對話輸入區 ---
            if prompt := st.chat_input("請在此輸入病患的回覆..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.spinner("底層決策博弈推演中..."):
                    reply_text = run_engine_turn(
                        api_key, selected_model, age, gender, medical_history, habits,
                        user_input=prompt, 
                        physical_tags="無新數據"
                    )
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                
                st.rerun()

            # --- 渲染歷史對話 (越新的在越下方) ---
            st.markdown("### 💬 對話紀錄")
            for msg in st.session_state.messages:
                if msg["role"] == "system":
                    st.caption(f"🔧 _{msg['content']}_")
                else:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

    # ==========================================
    # 【右側欄位】引擎狀態即時監控
    # ==========================================
    with col_right:
        st.subheader("⚙️ 引擎底層監控")
        st.caption("即時顯示五段式問診進度")
        st.divider()
        
        if st.session_state.initialized:
            e_status = st.session_state.engine_status
            
            # 顯示當前問診階段 (Phase)
            st.markdown("**🚨 引擎運行階段**")
            current_phase = e_status.get("current_phase", "等待推演...")
            st.info(current_phase)
            
            # 顯示 OPQRST 狀態
            st.markdown("**📋 OPQRST 收集進度**")
            opqrst_status = e_status.get("opqrst_status", "等待推演...")
            st.success(opqrst_status)
            
        st.divider()
        
        if st.session_state.initialized:
            if st.button("🔄 重置病患狀態，啟動全新問診", use_container_width=True):
                st.session_state.initialized = False
                st.session_state.messages = []
                st.session_state.engine_status = {}
                st.rerun()

if __name__ == "__main__":
    main()
