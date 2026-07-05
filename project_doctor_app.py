# ==========================================
# project_doctor_app.py (新增下拉選單與追加問診 UI)
# ==========================================
import streamlit as st
import project_doctor_config as config
import project_doctor_engine as engine

def setup_page():
    st.set_page_config(page_title="Doubt-Driven 臨床認知博弈控制台", layout="wide", initial_sidebar_state="expanded")

def render_sidebar():
    # ...(與先前完全相同，維持不變，此處略過以節省篇幅)
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
    
    # 狀態管理
    if "clinical_summary" not in st.session_state: st.session_state.clinical_summary = ""
    if "doubt_list" not in st.session_state: st.session_state.doubt_list = []
    if "raw_diagnosis_text" not in st.session_state: st.session_state.raw_diagnosis_text = ""
    if "soap_record" not in st.session_state: st.session_state.soap_record = {}
    if "available_models" not in st.session_state: st.session_state.available_models = []
    if "current_stage" not in st.session_state: st.session_state.current_stage = "1. 問診"
    
    # --- 新增儲存追加問診結果的變數 ---
    if "followup_result" not in st.session_state: st.session_state.followup_result = ""
        
    (api_key, selected_model, age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_mid, col_right = st.columns([3, 2])
    
    # ==========================================
    # 【中間欄位】Clinical Summary & 鑑別診斷 & 追加問診
    # ==========================================
    with col_mid:
        st.title("🩺 臨床推演工作區")
        st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎 v2.8")
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
                with st.expander(f"[{item['prob']}] {item['title']}", expanded=False):
                    st.markdown(f"**診斷推演細節**\n\n{item['desc']}")
            
            # --- 新增區塊：針對特定鑑別診斷產生追加問診 ---
            st.divider()
            st.subheader("💡 鑑別診斷追加問診 (High-Yield History Taking)")
            
            # 萃取診斷清單供使用者選擇
            diag_options = [f"[{item['prob']}] {item['title']}" for item in st.session_state.doubt_list]
            selected_diag = st.selectbox("選擇要針對哪一項診斷產生追加問診：", diag_options)
            
            if st.button("❓ 根據選定診斷與摘要產生追加問診", use_container_width=True):
                with st.spinner(f"正在針對鎖定診斷生成高收益問診..."):
                    sys_prompt = config.get_system_prompt(mode="followup")
                    forced_prompt = config.get_forced_template(
                        mode="followup",
                        clinical_summary=st.session_state.clinical_summary,
                        target_diagnosis=selected_diag
                    )
                    
                    st.session_state.followup_result = engine.generate_raw_text(
                        api_key, selected_model, sys_prompt, forced_prompt
                    )
            
            # 顯示追加問診結果
            if st.session_state.followup_result:
                st.success(st.session_state.followup_result)

        else:
            st.caption("💡 尚未產生診斷推演。")
            
        st.markdown("\n\n")
        if st.button("🚀 開始臨床推演（生成鑑別診斷）", use_container_width=True, type="primary"):
            if not api_key or not selected_model or not chief_complaint.strip():
                st.error("❌ 請確保已輸入 API 金鑰、選擇模型並填寫主訴！")
            else:
                with st.spinner("臨床博弈引擎深度推演（診斷生成中）..."):
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
                    
                    # 重置病歷與追加問診
                    st.session_state.soap_record = {}
                    st.session_state.followup_result = "" 
                    st.rerun()

    # ==========================================
    # 【右側欄位】標準病歷工作區 (維持先前 v2.7 版本邏輯)
    # ==========================================
    with col_right:
        st.subheader("📍 當前看診階段")
        st.session_state.current_stage = st.radio(
            "切換階段 (由醫師手動推進流程)", ["1. 問診", "2. 理學", "3. 檢驗/檢查"],
            horizontal=True, label_visibility="collapsed"
        )
        st.divider()
        
        st.subheader("📝 臨床標準病歷紀錄 (SOAP)")
        
        if st.session_state.doubt_list:
            if st.session_state.soap_record:
                d = st.session_state.soap_record
                with st.expander("S (Subjective)", expanded=True): st.markdown(d.get("soap_s", "無資料"))
                with st.expander("O (Objective)", expanded=True): st.markdown(d.get("soap_o", "無資料"))
                with st.expander("A (Assessment) - (已對齊)", expanded=True): st.markdown(d.get("soap_a", "無資料"))
                with st.expander("P (Plan)", expanded=True): st.markdown(d.get("soap_p", "無資料"))
                    
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
                            age=age, gender=gender, medical_history=medical_history, habits=habits,
                            current_stage=st.session_state.current_stage, mode="soap",
                            clinical_summary=st.session_state.clinical_summary, doubt_text=st.session_state.raw_diagnosis_text
                        )
                        
                        result = engine.process_doctor_turn(api_key, selected_model, sys_prompt, forced_prompt)
                        st.session_state.soap_record = result["parsed_dash"]
                        st.rerun()
        else:
            st.info("💡 請先在中央工作區啟動臨床推演生成鑑別診斷。")

if __name__ == "__main__":
    main()
