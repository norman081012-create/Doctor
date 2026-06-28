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
    """渲染側邊欄：控制台參數輸入與動態閾值設定[cite: 6]"""
    with st.sidebar:
        st.title("⚙️ 醫病博弈控制台")
        api_key = st.text_input("🔑 Gemini API 金鑰", value=config.DEFAULT_API_KEY, type="password")
        
        selected_model = None
        if api_key:
            if "available_models" not in st.session_state or not st.session_state.available_models:
                with st.spinner("正在向 Google 請求可用模型..."):
                    st.session_state.available_models = engine.fetch_available_models(api_key)

            if st.session_state.available_models:
                default_idx = 0
                # 優先匹配全新的預設核心：gemini-3.5-flash
                for i, m in enumerate(st.session_state.available_models):
                    if "gemini-3.5-flash" in m.lower():
                        default_idx = i
                        break
                    elif "gemini-2.0-flash" in m.lower() and default_idx == 0:
                        default_idx = i
                    elif "flash" in m.lower() and default_idx == 0:
                        default_idx = i
                
                selected_model = st.selectbox(
                    "🤖 選擇運算核心 (Model)", 
                    st.session_state.available_models, 
                    index=default_idx
                )
                st.info(f"當前核心：{selected_model}")
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
            default=["吸菸史", "飲酒史", "嚼檳榔史"]
        )
        final_habits = "、".join(habits_presets) if habits_presets else "無特殊不良嗜好"

        chief_complaint = st.text_area("⚠️ 病患主訴 (必填)", value="", placeholder="例：胸悶且陣發性心悸兩天...")
        
        st.markdown("---")
        st.markdown("### 📡 載入本輪動態實體標籤")
        client_integrity = st.select_slider("病患誠信度 (Integrity)", options=["極低", "低", "中", "高", "完全透明"], value="中")
        client_emotion = st.selectbox("病患當前情緒 (Emotion)", ["平靜", "焦慮甩鍋", "強烈質疑", "消極怠工", "極端非理性"])
        
        st.markdown("---")
        st.markdown("### 📦 醫療診療模組速查庫")
        category = st.selectbox("選擇模組分類", list(config.MODULES_FOR_UI.keys()))
        for mod_name, mod_desc in config.MODULES_FOR_UI[category].items():
            with st.expander(f"🔹 {mod_name}"):
                st.caption(mod_desc)

        return (api_key, selected_model, client_integrity, client_emotion, 
                age, gender, final_history, final_habits, chief_complaint)

def render_chat_history():
    """渲染對話紀錄介面（對話區域僅呈現 Step 5：實際醫師回覆）[cite: 4, 6]"""
    st.title("🩺 醫師互動診療室")
    st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v2.1，主視窗呈現【Step 5: 簡短醫師回覆】[cite: 4, 6]")
    st.divider()
    
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

def render_dashboard():
    """右側實時動態分析板：完全客製化重構，只純粹顯示臨床標準 SOAP 病歷[cite: 4, 6]"""
    st.subheader("📋 臨床標準病歷紀錄 (SOAP Note)")
    st.markdown("*(擷取自臨床引擎 `Step 4` 即時自動生成數據)*[cite: 4, 6]")
    st.divider()
    
    latest_assistant_msg = None
    for msg in reversed(st.session_state.chat_history):
        if msg["role"] == "model" and "parsed_dash" in msg:
            latest_assistant_msg = msg
            break
            
    if latest_assistant_msg:
        d = latest_assistant_msg["parsed_dash"]
        soap_content = d.get("soap", "未解析到病歷資料")
        
        # 以清晰獨立的高級容器渲染標準病歷
        st.markdown(soap_content)
    else:
        st.info("💡 等待診斷室建立首輪對話後，系統將在此同步生成標準臨床 SOAP 病歷。[cite: 4, 6]")

def main():
    setup_page()
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "available_models" not in st.session_state:
        st.session_state.available_models = []
        
    (api_key, selected_model, integrity, emotion, 
     age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_chat, col_dash = st.columns([3, 2])
    
    with col_chat:
        render_chat_history()
        
        if len(st.session_state.chat_history) == 0:
            st.info("💡 請先在左側填妥『病患資料與必填主訴』後，點擊下方按鈕啟動博弈對話室。[cite: 6]")
            if st.button("🚀 送出初始主訴並建立病例對話", use_container_width=True):
                if not chief_complaint.strip():
                    st.error("❌ 主訴為必填欄位！請在左側控制台填寫後再行啟動。[cite: 6]")
                elif not api_key or not selected_model:
                    st.error("❌ 請確認左側已配置正確的 Gemini API 金鑰與模型。[cite: 6]")
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
            st.error("請在側邊欄配置正確的 API 金鑰與運算核心核心後再行輸入。[cite: 6]")
        else:
            with col_chat:
                with st.chat_message("assistant"):
                    with st.spinner("臨床博弈引擎深度推演中...[cite: 6]"):
                        
                        last_user_input = st.session_state.chat_history[-1]["content"]
                        
                        sys_prompt = config.get_system_prompt(
                            priority_goal="防禦性醫療紀錄與根本原因鑑別",
                            active_modules=[]
                        )
                        forced_prompt = config.get_forced_template(
                            user_input=last_user_input,
                            integrity=integrity,
                            emotion=emotion,
                            age=age,
                            gender=gender,
                            medical_history=medical_history,
                            habits=habits
                        )
                        
                        api_history = []
                        for msg in st.session_state.chat_history[:-1]:
                            text = msg.get("raw_text", msg["content"]) if msg["role"] == "model" else msg["content"]
                            text = text.strip() if text else ""
                            if not text:
                                text = "*(無回應)*"
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
