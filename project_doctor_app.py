# ==========================================
# project_doctor_app.py
# ==========================================
import streamlit as st
import project_doctor_config as config
import project_doctor_engine as engine

def setup_page():
    st.set_page_config(
        page_title="Project Doctor Command Center", 
        layout="wide", 
        initial_sidebar_state="expanded"
    )

def render_sidebar():
    """渲染側邊欄：控制台參數輸入與動態閾值設定"""
    with st.sidebar:
        st.title("⚙️ Project Doctor 控制台")
        api_key = st.text_input("🔑 Gemini API 金鑰", value=config.DEFAULT_API_KEY, type="password")
        
        selected_model = None
        if api_key:
            # 檢查或請求可用模型
            if "available_models" not in st.session_state or not st.session_state.available_models:
                with st.spinner("正在向 Google 請求可用模型..."):
                    st.session_state.available_models = engine.fetch_available_models(api_key)

            if st.session_state.available_models:
                # 🎯 預設自動尋找並選擇 gemini-3.5-flash 邏輯
                default_idx = 0
                for i, m in enumerate(st.session_state.available_models):
                    if "gemini-3.5-flash" in m.lower():
                        default_idx = i
                        break
                    elif "3.5-flash" in m.lower() and default_idx == 0:
                        default_idx = i
                    elif "flash" in m.lower() and default_idx == 0:
                        default_idx = i
                
                selected_model = st.selectbox(
                    "🤖 選擇運算核心核心 (Model)", 
                    st.session_state.available_models, 
                    index=default_idx
                )
                st.info(f"當前核心：{selected_model}")
            else:
                st.error("未發現可用模型，請確認 API 金鑰是否正確。")
        
        st.markdown("---")
        st.markdown("### 📡 載入本輪實體標籤")
        client_integrity = st.select_slider("客戶資訊誠信度 (Integrity)", options=["極低", "低", "中", "高", "完全透明"], value="中")
        client_emotion = st.selectbox("客戶當前情緒 (Emotion)", ["平靜", "焦慮甩鍋", "強烈質疑", "消極怠工", "極端非理性"])
        
        # 🛠️ 新增：決策臨界防禦下限與上限滑桿
        st.markdown("---")
        st.markdown("### 🚨 認知防禦臨界設定")
        bd_lower_limit = st.slider("B-D 邊界防禦安全下限", min_value=0, max_value=100, value=40, step=5)
        st.caption(f"💡 低於 {bd_lower_limit} 分時，防禦機制將強行突破專業面具進行攤牌。")
        
        mf_upper_limit = st.slider("MF 顧問面具疲勞上限", min_value=0, max_value=100, value=85, step=5)
        st.caption(f"💡 高於 {mf_upper_limit} 分時，解構溫和引導模式，自動啟動邏輯毒打。")

        st.markdown("---")
        st.markdown("### 📦 診療模組速查庫")
        category = st.selectbox("選擇模組分類", list(config.MODULES_FOR_UI.keys()))
        for mod_name, mod_desc in config.MODULES_FOR_UI[category].items():
            with st.expander(f"🔹 {mod_name}"):
                st.caption(mod_desc)

        return api_key, selected_model, client_integrity, client_emotion, bd_lower_limit, mf_upper_limit

def render_chat_history():
    """渲染對話紀錄介面"""
    st.title("🩺 專案診療控制台")
    # 將 API 通訊用的歷程轉譯為 UI 渲染
    for msg in st.session_state.chat_history:
        # 轉換角色名稱符合 Streamlit 規範
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

def render_dashboard():
    """右側實時動態分析板"""
    st.subheader("📊 實時專案動態分析板")
    st.markdown("*(擷取自最新一輪認知引擎運算結果)*")
    st.divider()
    
    # 取得最新一輪的助理回應數據
    latest_assistant_msg = None
    for msg in reversed(st.session_state.chat_history):
        if msg["role"] == "model" and "parsed_dash" in msg:
            latest_assistant_msg = msg
            break
            
    if latest_assistant_msg:
        d = latest_assistant_msg["parsed_dash"]
        
        st.markdown("**1. 顧問客戶空間定位**")
        st.info(f"📍 當前定位：{d.get('location', '無')}  |  📈 變化趨向：{d.get('trend', '無')}")
        
        st.markdown("**2. 執行模組與標籤庫存**")
        st.write(f"**常駐執行：** {d.get('modules', '無')}")
        st.caption(f"**本輪結算庫存：**\n{d.get('tags', '無')}")
        
        st.markdown("**3. 心理防禦指標結算 (Dashboard)**")
        with st.expander(f"SAI (主導權感知): {d.get('sai', 'N/A')}"):
            st.caption("🔍 50 為舒適。過高代表過度微觀管理，過低代表遭情緒勒索。")
        with st.expander(f"MF (顧問面具疲勞度): {d.get('mf', 'N/A')}"):
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
        st.caption("⚙️ 開發者底層監控")
        with st.expander("🔍 展開底層原始運算 Log (Raw Data)", expanded=False):
            st.code(latest_assistant_msg.get("raw_text", "無資料"), language="markdown")
    else:
        st.caption("等待首輪對話產生專案診斷結果...")

def main():
    setup_page()
    
    # 初始化歷史紀錄 (採用 Google API 規範的 role 格式: 'user' 與 'model')
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "available_models" not in st.session_state:
        st.session_state.available_models = []
        
    # 渲染 Sidebar 並接回所有控制項參數
    api_key, selected_model, integrity, emotion, bd_limit, mf_limit = render_sidebar()
    
    # 建立主視窗雙欄佈局 (左側對話 60%, 右側即時儀表板 40%)
    col_chat, col_dash = st.columns([3, 2])
    
    with col_chat:
        render_chat_history()
        
        # 接收使用者輸入
        if user_input := st.chat_input("請輸入當前專案情境或客戶對話..."):
            # 1. 儲存使用者原始對話 (供畫面渲染)
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.rerun()

    with col_dash:
        render_dashboard()

    # 觸發大模型後台運算
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        if not api_key or not selected_model:
            st.error("請在側邊欄配置正確的 API 金鑰與運算核心核心後再行輸入。")
        else:
            with col_chat:
                with st.chat_message("assistant"):
                    with st.spinner("專案診療引擎深度推演中..."):
                        
                        # 1. 提取使用者剛剛輸入的話
                        last_user_input = st.session_state.chat_history[-1]["content"]
                        
                        # 2. 獲取動態注入限制與標籤後的系統提示詞與模板
                        sys_prompt = config.get_system_prompt(
                            priority_goal="專案稽核與根本原因分析",
                            active_modules=[],
                            bd_limit=bd_limit,
                            mf_limit=mf_limit
                        )
                        forced_prompt = config.get_forced_template(
                            user_input=last_user_input,
                            integrity=integrity,
                            emotion=emotion
                        )
                        
                        # 3. 準備發送給 API 的歷史（不包含本輪已被改寫成強製範本的最後一條）
                        # 注意：此處深拷貝 API 歷程，並將最後一條覆寫為結構化模板發送
                        api_history = []
                        for msg in st.session_state.chat_history[:-1]:
                            api_history.append({"role": msg["role"], "parts": [msg["content"]]})
                        
                        # 4. 調度引擎運算
                        result = engine.process_doctor_turn(
                            api_key=api_key,
                            selected_model=selected_model,
                            system_prompt=sys_prompt,
                            history_for_api=api_history,
                            forced_template_text=forced_prompt
                        )
                        
                        # 5. 將結果更新至全域 Session 狀態
                        st.session_state.chat_history.append({
                            "role": "model",
                            "content": result["output"],
                            "raw_text": result["raw_full_text"],
                            "parsed_dash": result["parsed_dash"]
                        })
                        st.rerun()

if __name__ == "__main__":
    main()
