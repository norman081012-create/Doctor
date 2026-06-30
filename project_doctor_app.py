# ==========================================
# project_doctor_app.py
# ==========================================
import streamlit as st
import project_doctor_config as config
import project_doctor_engine as engine

def setup_page():
    st.set_page_config(
        page_title="Doubt-Driven 醫病動態認知博弈控制台", 
        layout="wide", 
        initial_sidebar_state="expanded"
    )

def render_sidebar():
    with st.sidebar:
        st.title("⚙️ 醫病博弈控制台")
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
                
                selected_model = st.selectbox(
                    "🤖 選擇運算核心 (Model)", 
                    st.session_state.available_models, 
                    index=default_idx
                )
            else:
                st.error("未發現可用模型，請確認 API 金鑰是否正確。")
        
        st.markdown("---")
        st.markdown("### 📋 病患基本生理與病史背景")
        
        age = st.number_input("年齡", min_value=0, max_value=120, value=40, step=1)
        gender = st.selectbox("性別", ["男性", "女性", "多元性別"], index=0)
        
        history_presets = st.multiselect(
            "既往病史項目 (預設無)", 
            ["無", "高血壓", "高血糖", "高血脂", "糖尿病", "心臟疾病", "氣喘"], 
            default=["無"]
        )
        history_custom = st.text_input("自訂其他既往病史", value="")
        
        active_histories = [h for h in history_presets if h != "無"]
        if history_custom.strip():
            active_histories.append(history_custom.strip())
        final_history = "、".join(active_histories) if active_histories else "無特殊病史"
        
        habits_presets = st.multiselect(
            "生活習慣 / 接觸史", 
            ["吸菸史", "飲酒史", "嚼檳榔史"], 
            default=[]
        )
        final_habits = "、".join(habits_presets) if habits_presets else "無特殊不良嗜好"

        chief_complaint = st.text_area("⚠️ 病患主訴 (必填)", value="", placeholder="例：胸悶且陣發性心悸兩天...")
        
        st.markdown("---")
        st.markdown("### 📦 醫療診療模組速查庫")
        category = st.selectbox("選擇模組分類", list(config.MODULES_FOR_UI.keys()))
        for mod_name, mod_desc in config.MODULES_FOR_UI[category].items():
            with st.expander(f"🔹 {mod_name}"):
                st.caption(mod_desc)

        return (api_key, selected_model, age, gender, final_history, final_habits, chief_complaint)

def render_chat_history():
    st.title("🩺 醫師互動診療室")
    st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v2.2")
    st.divider()
    
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

def render_dashboard():
    # --- 新增階段切換 UI ---
    st.subheader("📍 當前看診階段")
    st.session_state.current_stage = st.radio(
        "切換階段 (由醫師手動推進流程)",
        ["1. 問診", "2. 理學", "3. 檢驗/檢查"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.divider()
    # -----------------------

    st.subheader("🎯 當前可能診斷與鑑別診斷")
    st.caption("*(依照 Step 3 內部引擎推演之 Doubt 懷疑度由高至低排序)*")
    
    latest_assistant_msg = None
    for msg in reversed(st.session_state.chat_history):
        if msg["role"] == "model" and "parsed_dash" in msg:
            latest_assistant_msg = msg
            break
            
    if latest_assistant_msg:
        d = latest_assistant_msg["parsed_dash"]
        
        st.info(d.get("doubt_assessment", "尚未產生評估"))
        st.divider()
        
        st.subheader("📋 臨床標準病歷紀錄 (SOAP)")
        
        with st.expander("S (Subjective) - 主觀主訴與現病史"):
            st.markdown(d.get("soap_s", "無資料"))
            
        with st.expander("O (Objective) - 客觀數據與理學檢查"):
            st.markdown(d.get("soap_o", "無資料"))
            
        with st.expander("A (Assessment) - 評估與診斷"):
            st.markdown(d.get("soap_a", "無資料"))
            
        with st.expander("P (Plan) - 處置計畫"):
            st.markdown(d.get("soap_p", "無資料"))
            
    else:
        st.info("💡 尚未產生診斷推演。等待首輪對話後，系統將在此顯示 Doubt 排序與 SOAP 病歷。")

def main():
    setup_page()
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "available_models" not in st.session_state:
        st.session_state.available_models = []
    # --- 初始化階段狀態 ---
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = "1. 問診"
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_chat, col_dash = st.columns([3, 2])
    
    with col_chat:
        render_chat_history()
        
        if len(st.session_state.chat_history) == 0:
            st.info("💡 請先在左側填寫『病患主訴』與『API 金鑰』後啟動對話。")
            if st.button("🚀 送出初始主訴並建立病例對話", use_container_width=True):
                if not api_key:
                    st.error("❌ 請先輸入 Gemini API 金鑰！")
                elif not selected_model:
                    st.error("❌ 無法載入模型，請確認 API 金鑰是否正確。")
                elif not chief_complaint.strip():
                    st.error("❌ 主訴為必填欄位！")
                else:
                    st.session_state.chat_history.append({"role": "user", "content": chief_complaint.strip()})
                    st.rerun()
        else:
            if user_input := st.chat_input("請輸入病患進一步的追問、回答或回應..."):
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.rerun()

    with col_dash:
        render_dashboard()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        if not api_key or not selected_model:
            st.error("請確認 API 金鑰與模型配置正確。")
        else:
            with col_chat:
                with st.chat_message("assistant"):
                    with st.spinner("臨床博弈引擎深度推演中..."):
                        
                        last_user_input = st.session_state.chat_history[-1]["content"]
                        sys_prompt = config.get_system_prompt()
                        
                        # --- 提取上一輪的 SOAP 紀錄 ---
                        previous_soap_text = ""
                        for msg in reversed(st.session_state.chat_history[:-1]):
                            if msg["role"] == "model" and "parsed_dash" in msg:
                                d = msg["parsed_dash"]
                                previous_soap_text = f"S: {d.get('soap_s', '無')}\nO: {d.get('soap_o', '無')}\nA: {d.get('soap_a', '無')}\nP: {d.get('soap_p', '無')}"
                                break
                        # --------------------------------
                        
                        forced_prompt = config.get_forced_template(
                            user_input=last_user_input,
                            age=age,
                            gender=gender,
                            medical_history=medical_history,
                            habits=habits,
                            previous_record=previous_soap_text,
                            current_stage=st.session_state.current_stage # --- 傳遞當前階段 ---
                        )
                        
                        api_history = []
                        for msg in st.session_state.chat_history[:-1]:
                            text = msg.get("raw_text", msg["content"]) if msg["role"] == "model" else msg["content"]
                            text = text.strip() if text else "*(無回應)*"
                            api_history.append({"role": msg["role"], "parts": [text]})
                        
                        result = engine.process_doctor_turn(
                            api_key=api_key,
                            selected_model=selected_model,
                            system_prompt=sys_prompt,
                            history_for_api=api_history,
                            forced_template_text=forced_prompt
                        )
                        
                        st.session_state.chat_history.append({
                            "role": "model",
                            "content": result["output"],
                            "raw_text": result["raw_full_text"],
                            "parsed_dash": result["parsed_dash"]
                        })
                        st.rerun()

if __name__ == "__main__":
    main()
