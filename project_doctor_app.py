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
    """渲染側邊欄：控制台參數輸入與動態閾值設定"""
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
                for i, m in enumerate(st.session_state.available_models):
                    if "gemini-2.0-flash" in m.lower():
                        default_idx = i
                        break
                    elif "gemini-1.5-flash" in m.lower() and default_idx == 0:
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
        
        # 1. 年紀預設 40
        age = st.number_input("年齡", min_value=0, max_value=120, value=40, step=1)
        
        # 2. 性別預設男性
        gender = st.selectbox("性別", ["男性", "女性", "多元性別"], index=0)
        
        # 3. 既往病史預設「無」，提供三高等常見預設
        history_presets = st.multiselect(
            "既往病史項目 (預設無)", 
            ["無", "高血壓", "高血糖", "高血脂", "糖尿病", "心臟疾病", "氣喘"], 
            default=["無"]
        )
        history_custom = st.text_input("自訂其他既往病史 (自由輸入)", value="")
        
        # 統合病史文字
        active_histories = [h for h in history_presets if h != "無"]
        if history_custom.strip():
            active_histories.append(history_custom.strip())
        final_history = "、".join(active_histories) if active_histories else "無特殊病史"
        
        # 4. 菸酒檳榔史配置（預設直接全選滿足使用者規格）
        habits_presets = st.multiselect(
            "生活習慣 / 接觸史", 
            ["吸菸史", "飲酒史", "嚼檳榔史"], 
            default=["吸菸史", "飲酒史", "嚼檳榔史"]
        )
        final_habits = "、".join(habits_presets) if habits_presets else "無特殊不良嗜好"

        # 5. 主訴 (必填欄位)
        chief_complaint = st.text_area("⚠️ 病患主訴 (必填)", value="", placeholder="例：胸悶且陣發性心悸兩天...", help="此處為病患最初就診時的病情切入描述。")
        
        st.markdown("---")
        st.markdown("### 📡 載入本輪動態實體標籤")
        client_integrity = st.select_slider("病患誠信度 (Integrity)", options=["極低", "低", "中", "高", "完全透明"], value="中")
        client_emotion = st.selectbox("病患當前情緒 (Emotion)", ["平靜", "焦慮甩鍋", "強烈質疑", "消極怠工", "極端非理性"])
        
        st.markdown("---")
        st.markdown("### 🚨 認知防禦臨界設定")
        bd_lower_limit = st.slider("B-D 邊界防禦安全下限", min_value=0, max_value=100, value=40, step=5)
        mf_upper_limit = st.slider("MF 顧問面具疲勞上限", min_value=0, max_value=100, value=85, step=5)

        st.markdown("---")
        st.markdown("### 📦 醫療診療模組速查庫")
        category = st.selectbox("選擇模組分類", list(config.MODULES_FOR_UI.keys()))
        for mod_name, mod_desc in config.MODULES_FOR_UI[category].items():
            with st.expander(f"🔹 {mod_name}"):
                st.caption(mod_desc)

        return (api_key, selected_model, client_integrity, client_emotion, 
                bd_lower_limit, mf_upper_limit, age, gender, final_history, final_habits, chief_complaint)

def render_chat_history():
    """渲染對話紀錄介面（對話區域僅呈現 Step 8：最終演繹）"""
    st.title("🩺 醫師互動診療室")
    st.caption("基於 Doubt-Driven 醫病動態認知博弈引擎，對話區域僅呈現【Step 8: 最終演繹】")
    st.divider()
    
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

def render_dashboard():
    """右側實時動態分析板"""
    st.subheader("📊 臨床決策動態分析板")
    st.markdown("*(擷取自臨床引擎 `<clinical_engine>` 內部推演數據)*")
    st.divider()
    
    latest_assistant_msg = None
    for msg in reversed(st.session_state.chat_history):
        if msg["role"] == "model" and "parsed_dash" in msg:
            latest_assistant_msg = msg
            break
            
    if latest_assistant_msg:
        d = latest_assistant_msg["parsed_dash"]
        
        st.markdown("**1. 醫病空間定位**")
        st.info(f"📍 當前定位：{d.get('location', '無')}  |  📈 變化趨向：{d.get('trend', '無')}")
        
        st.markdown("**2. 臨床推演精確指標**")
        st.write(f"**3.1 主訴與風險萃取：** {d.get('cc_extract', '無')}")
        st.write(f"**3.2 全局懷疑度標籤：** {d.get('doubt_tagging', '無')}")
        st.write(f"**3.3 反向鑑別診斷：** {d.get('differential', '無')}")
        st.caption(f"**3.4 執行模組與庫存結算：**\n{d.get('modules', '無')}")
        
        st.markdown("**3. 心理防禦指標結算 (Dashboard)**")
        with st.expander(f"SAI (主導權感知): {d.get('sai', 'N/A')}"):
            st.caption("🔍 50 為舒適。過高代表壓迫，過低代表遭情緒勒索。")
        with st.expander(f"MF (面具疲勞度): {d.get('mf', 'N/A')}"):
            st.caption("🔍 數值越高專業假象越難維持。若超越設定上限，將放棄溫和引導。")
        with st.expander(f"B-D (邊界防禦不適感): {d.get('bd', 'N/A')}"):
            st.caption("🔍 真實內在感受。100 為安全，若低於設定下限，內在防禦機制將會啟動。")
            
        st.markdown("**4. 內在真實想法與策略 (True Inner OS)**")
        with st.expander("👁️ 展開脫下白袍後的底層反射"):
            st.markdown(f"**真實反射 (底層 OS)：**\n{d.get('true_reflex', '無資料')}")
            st.markdown(f"**內在策略：**\n{d.get('inner_strategy', '無資料')}")
            
        st.markdown("**5. 專業形象應對策略 (Disguise)**")
        with st.expander("💼 展開外顯專業偽裝層"):
            st.markdown(f"**表面專業偽裝：**\n{d.get('disguise', '無資料')}")
            st.markdown(f"**外顯處置策略：**\n{d.get('external_strategy', '無資料')}")
            
        st.markdown("**6. 綜合最終策略 (Harmonized Decision)**")
        st.success(d.get("fusion", "無"))
        
        st.markdown("**7. 下輪準備 (Next Prep)**")
        st.write(f"**目標庫存：** {d.get('goal_stock', '無')}")
        st.warning(f"**下輪策略 (D)：** {d.get('next_strategy', '無')}")
        
        st.divider()
        st.caption("⚙️ 引擎底層監控")
        with st.expander("🔍 展開底層原始運算 Log (Raw Data)", expanded=False):
            st.code(latest_assistant_msg.get("raw_text", "無資料"), language="markdown")
    else:
        st.caption("等待首輪對話產生臨床診斷結果...")

def main():
    setup_page()
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "available_models" not in st.session_state:
        st.session_state.available_models = []
        
    (api_key, selected_model, integrity, emotion, bd_limit, mf_limit, 
     age, gender, medical_history, habits, chief_complaint) = render_sidebar()
    
    col_chat, col_dash = st.columns([3, 2])
    
    with col_chat:
        render_chat_history()
        
        # 第一輪對話控制：當歷史紀錄為空時，強制由左側主訴按鈕觸發
        if len(st.session_state.chat_history) == 0:
            st.info("💡 請先在左側填妥『病患資料與必填主訴』後，點擊下方按鈕啟動博弈對話室。")
            if st.button("🚀 送出初始主訴並建立病例對話", use_container_width=True):
                if not chief_complaint.strip():
                    st.error("❌ 主訴為必填欄位！請在左側控制台填寫後再行啟動。")
                elif not api_key or not selected_model:
                    st.error("❌ 請確認左側已配置正確的 Gemini API 金鑰與模型。")
                else:
                    st.session_state.chat_history.append({"role": "user", "content": chief_complaint.strip()})
                    st.rerun()
        else:
            # 後續對話：開放一般聊天框自由問答
            if user_input := st.chat_input("請輸入病患進一步的追問、回答或回應..."):
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.rerun()

    with col_dash:
        render_dashboard()

    # 驅動核心引擎運算
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        if not api_key or not selected_model:
            st.error("請在側邊欄配置正確的 API 金鑰與運算核心核心後再行輸入。")
        else:
            with col_chat:
                with st.chat_message("assistant"):
                    with st.spinner("臨床博弈引擎深度推演中..."):
                        
                        last_user_input = st.session_state.chat_history[-1]["content"]
                        
                        sys_prompt = config.get_system_prompt(
                            priority_goal="防禦性醫療紀錄與根本原因鑑別",
                            active_modules=[],
                            bd_limit=bd_limit,
                            mf_limit=mf_limit
                        )
                        # 注入所有採集自左側面板的背景參數
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
                            api_history.append({"role": msg["role"], "parts": [msg["content"]]})
                        
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
