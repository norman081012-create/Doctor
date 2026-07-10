# ==========================================
# project_doctor_app.py (動態對話與手動中斷結案版)
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
        
        st.markdown("---")
        st.markdown("### 📦 醫療診療模組速查庫")
        category = st.selectbox("選擇模組分類", list(config.MODULES_FOR_UI.keys()))
        for mod_name, mod_desc in config.MODULES_FOR_UI[category].items():
            with st.expander(f"🔹 {mod_name}"):
                st.caption(mod_desc)

        return (api_key, selected_model, age, gender, final_history, final_habits, chief_complaint)

def main():
    setup_page()
    
    # 核心動態對話狀態管理
    if "initialized" not in st.session_state: st.session_state.initialized = False
    if "interrogation_ended" not in st.session_state: st.session_state.interrogation_ended = False
    if "messages" not in st.session_state: st.session_state.messages = []
    
    if "clinical_summary" not in st.session_state: st.session_state.clinical_summary = ""
    if "doubt_list" not in st.session_state: st.session_state.doubt_list = []
    if "raw_diagnosis_text" not in st.session_state: st.session_state.raw_diagnosis_text = ""
    if "soap_record" not in st.session_state: st.session_state.soap_record = {}
    if "available_models" not in st.session_state: st.session_state.available_models = []
    if "current_stage" not in st.session_state: st.session_state.current_stage = "1. 問診"
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_left, col_right = st.columns([3, 2])
    
    # ==========================================
    # 【左側欄位】動態問診對話流工作區
    # ==========================================
    with col_left:
        st.title("🩺 臨床動態問診工作區")
        st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v2.8 (動態對話系統)")
        st.divider()
        
        if not st.session_state.initialized:
            st.info("💡 請於左側配置病患基本背景並填寫**主訴**，隨後點擊下方按鈕啟動認知博弈問診流程。")
            if st.button("🚀 啟動 Doubt-Driven 動態問診系統", use_container_width=True, type="primary"):
                if not api_key or not selected_model or not chief_complaint.strip():
                    st.error("❌ 請確保已輸入 API 金鑰、選擇模型並填寫主訴！")
                else:
                    with st.spinner("正在啟動推演核心，進行風險與症狀頻譜展延..."):
                        # 1. 運行初期診斷模式獲取 Baseline
                        sys_prompt = config.get_system_prompt(mode="diagnosis")
                        forced_prompt = config.get_forced_template(
                            user_input=chief_complaint.strip(),
                            age=age, gender=gender, medical_history=medical_history, habits=habits,
                            current_stage=st.session_state.current_stage, mode="diagnosis"
                        )
                        result = engine.process_doctor_turn(api_key, selected_model, sys_prompt, forced_prompt)
                        dash = result["parsed_dash"]
                        st.session_state.clinical_summary = dash.get("clinical_summary", "無摘要說明")
                        st.session_state.raw_diagnosis_text = dash.get("doubt_assessment", "")
                        st.session_state.doubt_list = engine.parse_doubt_assessment(st.session_state.raw_diagnosis_text)
                        
                        # 2. 注入第一軌對話歷史
                        st.session_state.messages.append({"role": "user", "content": f"【主訴初始化】{chief_complaint.strip()}"})
                        
                        # 3. 引導引擎產生第一句追加高收益問診
                        sys_prompt_chat = config.get_system_prompt(mode="chat_loop")
                        chat_context = f"user: 【主訴初始化】{chief_complaint.strip()}"
                        forced_prompt_chat = config.get_forced_template(
                            age=age, gender=gender, medical_history=medical_history, habits=habits,
                            current_stage=st.session_state.current_stage, mode="chat_loop",
                            clinical_summary=st.session_state.clinical_summary, chat_context=chat_context
                        )
                        first_reply = engine.generate_raw_text(api_key, selected_model, sys_prompt_chat, forced_prompt_chat)
                        parsed_reply = engine.parse_chat_response(first_reply)
                        
                        st.session_state.messages.append({"role": "assistant", "content": parsed_reply["chat_text"]})
                        st.session_state.initialized = True
                        st.rerun()
        else:
            # 渲染動態對話紀錄
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # 判斷是否被醫師中斷結案
            if not st.session_state.interrogation_ended:
                if prompt := st.chat_input("請在此輸入患者的回覆以推進推演..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                        
                    with st.chat_message("assistant"):
                        with st.spinner("博弈引擎深度推演與全局狀態修正中..."):
                            chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                            sys_prompt_chat = config.get_system_prompt(mode="chat_loop")
                            forced_prompt_chat = config.get_forced_template(
                                age=age, gender=gender, medical_history=medical_history, habits=habits,
                                current_stage=st.session_state.current_stage, mode="chat_loop",
                                clinical_summary=st.session_state.clinical_summary, chat_context=chat_context
                            )
                            reply = engine.generate_raw_text(api_key, selected_model, sys_prompt_chat, forced_prompt_chat)
                            parsed_reply = engine.parse_chat_response(reply)
                            
                            st.markdown(parsed_reply["chat_text"])
                            st.session_state.messages.append({"role": "assistant", "content": parsed_reply["chat_text"]})
                            
                            # 靜默更新右側即時狀態監控變數
                            dash = parsed_reply["parsed_dash"]
                            if dash.get("clinical_summary"):
                                st.session_state.clinical_summary = dash["clinical_summary"]
                            if dash.get("doubt_assessment"):
                                st.session_state.raw_diagnosis_text = dash["doubt_assessment"]
                                st.session_state.doubt_list = engine.parse_doubt_assessment(dash["doubt_assessment"])
                    st.rerun()
            else:
                st.success("🔒 問診流程已由醫師人為中斷結案。對話功能已鎖定，請檢視右側結構化病歷。")

    # ==========================================
    # 【右側欄位】引擎狀態即時監控與 SOAP 病歷區
    # ==========================================
    with col_right:
        st.subheader("📍 當前看診階段")
        st.session_state.current_stage = st.radio(
            "切換階段 (由醫師手動推進流程)", ["1. 問診", "2. 理學", "3. 檢驗/檢查"],
            horizontal=True, label_visibility="collapsed"
        )
        st.divider()
        
        st.subheader("📋 即時臨床摘要 (Clinical Summary)")
        if st.session_state.clinical_summary:
            st.info(st.session_state.clinical_summary)
        else:
            st.caption("💡 等待推演啟動...")
            
        st.divider()
        
        st.subheader("🎯 動態鑑別診斷排序 (Real-time DDx)")
        if st.session_state.doubt_list:
            for item in st.session_state.doubt_list:
                with st.expander(f"[{item['prob']}] {item['title']}", expanded=False):
                    st.markdown(f"**診斷推演細節**\n\n{item['desc']}")
        else:
            st.caption("💡 尚未產生診斷推演。")
            
        st.divider()
        
        # 醫師人為判定中斷控制器
        if st.session_state.initialized and not st.session_state.interrogation_ended:
            st.warning("👉 當您觀察上方鑑別診斷列表，認為資訊量已足夠明確時，請點擊下方按鈕結案。")
            if st.button("🛑 診斷已明確，手動結束問診並生成病歷", type="primary", use_container_width=True):
                st.session_state.interrogation_ended = True
                st.rerun()
                
        # 結案後，自動調度 SOAP 生成核心
        if st.session_state.interrogation_ended:
            st.subheader("📝 臨床標準病歷紀錄 (SOAP)")
            if not st.session_state.soap_record:
                with st.spinner("正在同步動態問診歷史，編織結構化 SOAP 防禦性病歷..."):
                    sys_prompt_soap = config.get_system_prompt(mode="soap")
                    forced_prompt_soap = config.get_forced_template(
                        age=age, gender=gender, medical_history=medical_history, habits=habits,
                        current_stage=st.session_state.current_stage, mode="soap",
                        clinical_summary=st.session_state.clinical_summary, doubt_text=st.session_state.raw_diagnosis_text
                    )
                    result_soap = engine.process_doctor_turn(api_key, selected_model, sys_prompt_soap, forced_prompt_soap)
                    st.session_state.soap_record = result_soap["parsed_dash"]
                    st.rerun()
            
            d = st.session_state.soap_record
            with st.expander("S (Subjective) - 已建立對話對齊", expanded=True): st.markdown(d.get("soap_s", "無資料"))
            with st.expander("O (Objective) - 陽性與高價值陰性體徵", expanded=True): st.markdown(d.get("soap_o", "無資料"))
            with st.expander("A (Assessment) - 症狀群與 R/O 映射", expanded=True): st.markdown(d.get("soap_a", "無資料"))
            with st.expander("P (Plan) - 臨床臨床防禦性處置方針", expanded=True): st.markdown(d.get("soap_p", "無資料"))
            
            st.markdown("---")
            if st.button("🔄 重置病患狀態，啟動全新問診", use_container_width=True):
                st.session_state.initialized = False
                st.session_state.interrogation_ended = False
                st.session_state.messages = []
                st.session_state.clinical_summary = ""
                st.session_state.doubt_list = []
                st.session_state.raw_diagnosis_text = ""
                st.session_state.soap_record = {}
                st.rerun()

if __name__ == "__main__":
    main()
