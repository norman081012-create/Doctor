# ==========================================
# project_doctor_app.py
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
    sys_prompt = config.get_system_prompt(mode="v2_1_engine")
    
    # 讀取「全部」歷史對話
    chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
    
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
        
    return parsed_reply["chat_text"]

def main():
    setup_page()
    
    if "initialized" not in st.session_state: st.session_state.initialized = False
    if "messages" not in st.session_state: st.session_state.messages = []
    if "current_soap_xml" not in st.session_state: st.session_state.current_soap_xml = ""
    if "parsed_dash" not in st.session_state: st.session_state.parsed_dash = {}
    # 新增：用於動態清空實體標籤輸入框的 Key
    if "pe_key" not in st.session_state: st.session_state.pe_key = 0
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_left, col_right = st.columns([3, 2])
    
    # ==========================================
    # 【左側欄位】動態問診與實體標籤空投區
    # ==========================================
    with col_left:
        st.title("🩺 臨床動態問診工作區")
        st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v2.1")
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
        else:
            # --- 實體標籤空投區 (固定於左上) ---
            with st.expander("💉 實體標籤空投區 (Objective Findings)", expanded=True):
                # 使用動態 Key，每次 pe_key 改變，這就會變成一個全新空白的輸入框
                physical_input = st.text_input(
                    "輸入理學檢查 (PE) 或檢驗數據 (Lab)", 
                    key=f"physical_input_widget_{st.session_state.pe_key}",
                    placeholder="例：BP 180/100, EKG: ST elevation in V1-V3..."
                )
                
                if st.button("⚡ 強制載入標籤並觸發推演 (無需等候病患回覆)", use_container_width=True):
                    if physical_input.strip():
                        st.session_state.messages.append({"role": "system", "content": f"【操作者強制載入實體標籤】：{physical_input.strip()}"})
                        with st.spinner("載入新實體標籤，觸發反向鑑別與動態閥值更新..."):
                            reply_text = run_engine_turn(
                                api_key, selected_model, age, gender, medical_history, habits,
                                user_input="[病患無新發言，系統基於新實體標籤重新評估]", 
                                physical_tags=physical_input.strip()
                            )
                            st.session_state.messages.append({"role": "assistant", "content": reply_text})
                            
                            # 觸發清空輸入框：讓 pe_key + 1
                            st.session_state.pe_key += 1
                            st.rerun()
            st.divider()

            # --- 病患對話輸入區 ---
            if prompt := st.chat_input("請在此輸入病患的回覆..."):
                # 直接讀取上面的 physical_input 變數
                current_physical = physical_input.strip() if physical_input.strip() else "無新數據"
                
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.spinner("四維度透視引擎掃描中..."):
                    reply_text = run_engine_turn(
                        api_key, selected_model, age, gender, medical_history, habits,
                        user_input=prompt, 
                        physical_tags=current_physical
                    )
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                
                # 如果對話時有夾帶實體標籤，送出後也順便清空實體標籤欄位
                if current_physical != "無新數據":
                    st.session_state.pe_key += 1
                
                st.rerun()

            # --- 渲染歷史對話 (越新的在越上方) ---
            st.markdown("### 💬 對話紀錄")
            for msg in reversed(st.session_state.messages):
                if msg["role"] == "system":
                    st.caption(f"🔧 _{msg['content']}_")
                else:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

    # ==========================================
    # 【右側欄位】引擎狀態即時監控 (Rolling SAP)
    # ==========================================
    with col_right:
        st.subheader("⚙️ 引擎底層認知狀態 (Live SAP)")
        st.caption("即時解析 Step 1~4 的內部推演結果")
        st.divider()
        
        d = st.session_state.parsed_dash
        
        with st.expander("S (Subjective) - 歷史全局統整與主訴", expanded=True):
            st.markdown(d.get("soap_s", "等待推演..."))
            
        with st.expander("A (Assessment) - 動態鑑別診斷 (DDx)", expanded=True):
            st.markdown(d.get("soap_a", "等待推演..."))
            
        with st.expander("P (Plan) - 處置與防禦性策略", expanded=True):
            st.markdown(d.get("soap_p", "等待推演..."))
            
        st.divider()
        
        if st.session_state.initialized:
            if st.button("🔄 重置病患狀態，啟動全新問診", use_container_width=True):
                st.session_state.initialized = False
                st.session_state.messages = []
                st.session_state.current_soap_xml = ""
                st.session_state.parsed_dash = {}
                st.session_state.pe_key = 0
                st.rerun()

if __name__ == "__main__":
    main()
