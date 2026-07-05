# ==========================================
# project_doctor_app.py
# ==========================================
import streamlit as st
import project_doctor_config as config
import project_doctor_engine as engine

def setup_page():
    st.set_page_config(
        page_title="Doubt-Driven 臨床認知博弈控制台", 
        layout="wide", 
        initial_sidebar_state="expanded"
    )

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
                
                selected_model = st.selectbox(
                    "🤖 選擇運算核心 (Model)", 
                    st.session_state.available_models, 
                    index=default_idx
                )
            else:
                st.error("未發現可用模型，請確認 API 金鑰是否正確。")
        
        st.markdown("---")
        st.markdown("### 📋 病健基本生理與病史背景")
        
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

def main():
    setup_page()
    
    # 初始化獨立的工作記憶體狀態
    if "clinical_summary" not in st.session_state:
        st.session_state.clinical_summary = ""
    if "doubt_list" not in st.session_state:
        st.session_state.doubt_list = []
    if "raw_diagnosis_text" not in st.session_state:
        st.session_state.raw_diagnosis_text = ""
    if "soap_record" not in st.session_state:
        st.session_state.soap_record = {}
    if "available_models" not in st.session_state:
        st.session_state.available_models = []
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = "1. 問診"
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    # 重新切分中間欄位與右側欄位
    col_mid, col_right = st.columns([3, 2])
    
    # ==========================================
    # 【中間欄位】Clinical Summary & 鑑別診斷
    # ==========================================
    with col_mid:
        st.title("🩺 臨床推演工作區")
        st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v2.3")
        st.divider()
        
        st.subheader("📋 臨床摘要 (Clinical Summary)")
        if st.session_state.clinical_summary:
            st.info(st.session_state.clinical_summary)
        else:
            st.caption("💡 尚未生成臨床摘要。請配置左側參數並啟動推演。")
            
        st.divider()
        
        st.subheader("🎯 鑑別診斷 (Differential Diagnosis)")
        if st.session_state.doubt_list:
            for item in st.session_state.doubt_list:
                # 初始狀態收束，標題僅顯示包含百分比與疾病名稱，點開才顯示內部對齊說明
                with st.expander(f"[{item['prob']}] {item['title']}", expanded=False):
                    st.markdown(f"**診斷推演細節**\n\n{item['desc']}")
        else:
            st.caption("💡 尚未產生診斷推演。")
            
        st.markdown("\n\n")
        if st.button("🚀 開始臨床推演（生成鑑別診斷）", use_container_width=True, type="primary"):
            if not api_key:
                st.error("❌ 請先輸入 Gemini API 金鑰！")
            elif not selected_model:
                st.error("❌ 無法載入模型，請確認 API 金鑰是否正確。")
            elif not chief_complaint.strip():
                st.error("❌ 主訴為必填欄位！")
            else:
                with st.spinner("臨床博弈引擎深度推演（診斷生成中）..."):
                    sys_prompt = config.get_system_prompt(mode="diagnosis")
                    forced_prompt = config.get_forced_template(
                        user_input=chief_complaint.strip(),
                        age=age,
                        gender=gender,
                        medical_history=medical_history,
                        habits=habits,
                        current_stage=st.session_state.current_stage,
                        mode="diagnosis"
                    )
                    
                    result = engine.process_doctor_turn(
                        api_key=api_key,
                        selected_model=selected_model,
                        system_prompt=sys_prompt,
                        forced_template_text=forced_prompt
                    )
                    
                    dash = result["parsed_dash"]
                    st.session_state.clinical_summary = dash.get("clinical_summary", "無摘要說明")
                    st.session_state.raw_diagnosis_text = dash.get("doubt_assessment", "")
                    st.session_state.doubt_list = engine.parse_doubt_assessment(st.session_state.raw_diagnosis_text)
                    st.session_state.soap_record = {}  # 重新推演診斷時，重置舊病歷
                    st.rerun()

    # ==========================================
    # 【右側欄位】標準病歷工作區
    # ==========================================
    with col_right:
        st.subheader("📍 當前看診階段")
        st.session_state.current_stage = st.radio(
            "切換階段 (由醫師手動推進流程)",
            ["1. 問診", "2. 理學", "3. 檢驗/檢查"],
            horizontal=True,
            label_visibility="collapsed"
        )
        st.divider()
        
        st.subheader("📝 臨床標準病歷紀錄 (SOAP)")
        
        if st.session_state.doubt_list:
            if st.session_state.soap_record:
                d = st.session_state.soap_record
                
                with st.expander("S (Subjective) - 主觀主訴與現病史", expanded=True):
                    st.markdown(d.get("soap_s", "無資料"))
                    
                with st.expander("O (Objective) - 客觀數據與理學檢查", expanded=True):
                    st.markdown(d.get("soap_o", "無資料"))
                    
                with st.expander("A (Assessment) - 評估與診斷 (已100%對齊)", expanded=True):
                    st.markdown(d.get("soap_a", "無資料"))
                    
                with st.expander("P (Plan) - 處置計畫", expanded=True):
                    st.markdown(d.get("soap_p", "無資料"))
                    
                st.markdown("---")
                if st.button("🔄 重新同步生成病歷", use_container_width=True):
                    st.session_state.soap_record = {}
                    st.rerun()
            else:
                st.info("💡 鑑別診斷已確立。請點擊下方按鈕以生成完全對齊的防禦性標準病歷。")
                if st.button("🧬 生成病歷", use_container_width=True, type="primary"):
                    with st.spinner("正在同步歷史診斷，編織結構化 SOAP 病歷中..."):
                        sys_prompt = config.get_system_prompt(mode="soap")
                        forced_prompt = config.get_forced_template(
                            user_input=chief_complaint.strip(),
                            age=age,
                            gender=gender,
                            medical_history=medical_history,
                            habits=habits,
                            current_stage=st.session_state.current_stage,
                            mode="soap",
                            clinical_summary=st.session_state.clinical_summary,
                            doubt_text=st.session_state.raw_diagnosis_text
                        )
                        
                        result = engine.process_doctor_turn(
                            api_key=api_key,
                            selected_model=selected_model,
                            system_prompt=sys_prompt,
                            forced_template_text=forced_prompt
                        )
                        
                        st.session_state.soap_record = result["parsed_dash"]
                        st.rerun()
        else:
            st.info("💡 請先在中央工作區啟動臨床推演生成鑑別診斷。")

if __name__ == "__main__":
    main()
