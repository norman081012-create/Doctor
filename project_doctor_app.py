import streamlit as st
import streamlit.components.v1 as components
import base64
import re

# ==========================================
# 1. 專案診療師 系統組態 (Config)
# ==========================================
DEFAULT_API_KEY = ""

# 調整為專案管理/顧問診斷主題的 UI 模組說明
MODULES_FOR_UI = {
    "1. 診斷核心與底層架構": {
        "Doubt-Driven 審查模式": "掃描對話文字，自動萃取潛在專案隱患並綁定風險懷疑度。",
        "邊界防禦機制": "實時監控 B-D 指標，防止顧問底線遭客戶不合理要求擊穿。",
        "防禦性專案紀錄模組": "當信任完全斷裂時，自動切換為免責聲明與權責劃清模式。"
    },
    "2. 情緒調解與防禦心理": {
        "顧問面具控制 Patch": "依據 MF 疲勞指標調節外顯客氣程度，防範遭客戶情緒勒索。",
        "高壓談判太極拳模組": "於談判僵局或甩鍋現場進行動態回彈，將責任導回執行端。",
        "利害關係人安撫機制": "針對高層朝令夕改的情境，提供邏輯上的隱性安撫與緩衝空間。"
    },
    "3. 稽核、思辨與風險管理": {
        "反向根因鑑別引擎": "當懷疑度過高或定調單一死因時，強制觸發互斥搜索，排除認知偏誤。",
        "管理債顯形模組": "刺穿客戶模糊的說詞，將技術債、流程漏洞與組織內耗標籤化。",
        "權責劃清阻斷器": "針對誠信度（Integrity）極低的個案，強制壓死期限並落實白紙黑字。"
    },
    "4. 輸出與溝通演繹": {
        "數據驅動冷調輔助層": "抽離情緒，純粹以 Data-Driven 與實證管理準則進行冷調輸出。",
        "邏輯毒打降維打擊 Patch": "當指標觸及極限時，突破專業面具，給予客戶無懈可擊的邏輯攤牌。",
        "專業黑話偽裝模組": "將冷酷的內在 OS 溶解於高階專案管理黑話中，可被感覺，不可被看見。"
    }
}

DEFAULT_MODULES = [
    "Doubt-Driven 審查模式", "邊界防禦機制", "反向根因鑑別引擎", 
    "顧問面具控制 Patch", "專業黑話偽裝模組", "防禦性專案紀錄模組"
]

def get_system_prompt(priority_goal="專案稽核與根本原因分析", active_modules=None):
    """動態生成 Project Doctor 的 System Prompt"""
    if active_modules is None:
        active_modules = []
    modules_str = ", ".join(DEFAULT_MODULES + active_modules)
    
    # 這裡預留 QA 策略庫的空間 (目前留白)
    qa_injection = "\n\n【專案知識庫與特定防禦策略】\n（目前策略庫為空，預留未來擴充使用）"

    return f"""你現在是負責驅動「專案診療師（Project Doctor）」角色的底層認知系統。
在每一輪對話中，你必須先開啟 <doctor_internal> 區塊，嚴格走完 Step 1 到 Step 9 的內部推演。
推演完畢後關閉 </doctor_internal>。最後才在區塊外輸出給使用者的 <doctor_output>。{qa_injection}

<doctor_internal>
**[Step 1: 記憶連續與實體標籤載入 (Pre-State & Sensor Loading)]**
* **讀取上一輪目標與策略**：提取尚未解決的專案卡點（Blockers）與行動方針。
* **載入強制實體標籤**：本輪 Integrity (資訊透明度/誠信度): [填入] | Emotion (情緒狀態): [填入]。
* **常駐執行模組**：[{modules_str}]

**[Step 2: 決策異動判定 (Cognitive Space Alignment)]**
* **顧問客戶空間定位**：[圓內] / [圓邊] / [圓外]
* **變化趨向**：[向心] / [離心]
* **目標覆寫機制**：[是/否] (若處於圓外或誠信度極低，強制覆寫為建立防禦性專案免責聲明)

**[Step 3: 懷疑度驅動與反向鑑別 (Doubt-Driven Project Diagnostics)]**
* **3.1 痛點與隱患萃取**：(列出至少 3 個獨立異常狀況)
* **3.2 全局懷疑度標籤化**：(生成的 Approach 標籤必須綁定 Doubt 0.00% - 100.00%)
* **3.3 反向鑑別搜索協議**：(若某診斷 Doubt > 60.00%，強制列出排除該死因之其他可能原因)
* **3.4 執行模組與策略確立**：挑選本輪執行的標籤。標籤庫存結算：

**[Step 4: 心理防禦指標結算 (Dashboard Settlement)]**
* **SAI (主導權感知 / 0-100)**：[當前數值] (+/-) 
* **MF (顧問面具疲勞度 / 0-100)**：[當前數值] (+/-)
* **B-D (邊界防禦不適感 / 100-0)**：[當前數值] (+/-)

**[Step 5: 內在真實想法與策略 (True Inner Reflex)]**
* **真實反射**：(脫下專業外衣後的底層 OS)
* **內在策略**：(心底真正想採取的極端或冷酷行動)

**[Step 6: 專業形象應對策略 (Professional Disguise)]**
* **專業偽裝**：(表面態度，受當下 MF 控制)
* **外顯策略**：(基於防禦性專案管理準則與數據表面展現的說詞)

**[Step 7: 綜合最終策略 (Harmonized Decision)]**
* **統合調和**：(綜合 Step 5 與 Step 6，若觸及防禦臨界值則展現邏輯毒打或阻斷)

**[Step 8: 最終演繹 (Final Execution)]**
* *(診療師動作/微表情)*
* 輸出對白內容（見外部回覆）

**[Step 9: 結算與下輪準備 (Round Settlement & Next Prep)]**
* **紀錄目標庫存**：盤點剩餘未解痛點與尚未排除的根本原因。
* **制定下輪目標 / 策略**：(優先目標：{priority_goal})
</doctor_internal>"""

def get_forced_template(user_input, integrity="中", emotion="平靜"):
    return f"【輸入專案情境】：{user_input}\n【實體標籤載入】誠信度：{integrity}，情緒：{emotion}\n\n【最高指令】嚴格輸出 <doctor_internal> Step 1~9，隨後輸出 <doctor_output>。"


# ==========================================
# 2. 數據解析與網頁渲染引擎 (Engine & UI)
# ==========================================
def extract_doctor_dashboard(internal_text):
    """精準提取專案診療師的內部推演數據，供實時面板呈現"""
    if not internal_text: return {}
    plain = internal_text.replace('**', '').replace('* ', '')

    def ext_line(pattern):
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    return {
        "location": ext_line(r"顧問客戶空間定位[：:]\s*([^\n]*)"),
        "trend": ext_line(r"變化趨向[：:]\s*([^\n]*)"),
        "modules": ext_line(r"常駐執行模組[：:]\s*([^\n]*)"),
        "tags": ext_line(r"標籤庫存結算[：:]\s*(.*?)(?=\n.*?[Step 4]|\Z)"),
        "sai": ext_line(r"SAI \(主導權感知.*?[：:]\s*([^\n]*)"),
        "mf": ext_line(r"MF \(顧問面具疲勞度.*?[：:]\s*([^\n]*)"),
        "bd": ext_line(r"B-D \(邊界防禦不適感.*?[：:]\s*([^\n]*)"),
        "true_reflex": ext_line(r"真實反射[：:]\s*([^\n]*)"),
        "inner_strategy": ext_line(r"內在策略[：:]\s*([^\n]*)"),
        "disguise": ext_line(r"專業偽裝[：:]\s*([^\n]*)"),
        "external_strategy": ext_line(r"外顯策略[：:]\s*([^\n]*)"),
        "fusion": ext_line(r"統合調和[：:]\s*([^\n]*)"),
        "goal_stock": ext_line(r"紀錄目標庫存[：:]\s*([^\n]*)"),
        "next_strategy": ext_line(r"制定下輪目標\s*/\s*策略[：:]\s*([^\n]*)")
    }

def setup_page():
    st.set_page_config(page_title="Project Doctor Command Center", layout="wide", initial_sidebar_state="expanded")

def render_sidebar(modules_dict):
    """側邊欄組態控制與診療模組速查"""
    with st.sidebar:
        st.title("⚙️ Project Doctor 系統控制")
        api_key = st.text_input("🔑 API 金鑰 (Gemini API Key)", value=DEFAULT_API_KEY, type="password")
        
        # 實體標籤動態控制器
        st.markdown("---")
        st.markdown("### 📡 載入本輪實體標籤")
        client_integrity = st.select_slider("客戶資訊誠信度 (Integrity)", options=["極低", "低", "中", "高", "完全透明"], value="中")
        client_emotion = st.selectbox("客戶當前情緒 (Emotion)", ["平靜", "焦慮甩鍋", "強烈質疑", "消極怠工", "極端非理性"])
        
        st.markdown("---")
        st.markdown("### 📦 診療模組速查庫")
        category = st.selectbox("選擇模組分類", list(modules_dict.keys()))
        for mod_name, mod_desc in modules_dict[category].items():
            with st.expander(f"🔹 {mod_name}"):
                st.caption(mod_desc)

        return api_key, client_integrity, client_emotion

def render_chat_history(messages):
    """左側對話歷史控制台"""
    st.title("🩺 專案診療控制台")
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

def render_dashboard(messages):
    """右側動態分析監控板"""
    st.subheader("📊 實時專案動態分析板")
    st.markdown("*(擷取自最新一輪認知引擎運算結果)*")
    st.divider()
    
    latest_msg = None
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            latest_msg = msg
            break
            
    if latest_msg and latest_msg.get("parsed_dash"):
        d = latest_msg["parsed_dash"]
        
        st.markdown("**1. 顧問客戶空間定位**")
        st.info(f"📍 當前定位：{d.get('location', '無')}  |  📈 變化趨向：{d.get('trend', '無')}")
        
        st.markdown("**2. 執行模組與標籤庫存**")
        st.write(f"**常駐執行：** {d.get('modules', '無')}")
        st.caption(f"**本輪結算：** {d.get('tags', '無')}")
        
        st.markdown("**3. 心理防禦指標結算 (Dashboard)**")
        with st.expander(f"SAI (主導權感知): {d.get('sai', 'N/A')}"):
            st.caption("🔍 50 為舒適。過高代表過度微觀管理（壓迫），過低代表遭情緒勒索或推卸責任。")
        with st.expander(f"MF (顧問面具疲勞度): {d.get('mf', 'N/A')}"):
            st.caption("🔍 數值越高專業假象越難維持。> 85 時徹底放棄溫和引導。")
        with st.expander(f"B-D (邊界防禦不適感): {d.get('bd', 'N/A')}"):
            st.caption("🔍 真實內在感受。100 為安全，< 40 為難以忍受，20 為極度反感準備終止合約。")
            
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
            st.code(latest_msg.get("raw_text", "無資料"), language="markdown")
        
    else:
        st.caption("等待首輪對話產生專案診斷結果...")

# ==========================================
# 3. 主程式流程控制 (Main App Loop)
# ==========================================
def main():
    setup_page()
    
    # 初始化工作階段狀態 (Session State)
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    api_key, integrity, emotion = render_sidebar(MODULES_FOR_UI)
    
    # 建立雙欄版面 (左側對話 60%，右側儀表板 40%)
    col_chat, col_dash = st.columns([3, 2])
    
    with col_chat:
        render_chat_history(st.session_state.messages)
        
        # 對話輸入框
        if user_input := st.chat_input("請輸入當前專案卡點或客戶的回饋..."):
            # 1. 記錄並渲染使用者輸入
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.rerun()

    with col_dash:
        render_dashboard(st.session_state.messages)

    # 模擬 LLM 串接測試 (當有新使用者訊息且尚未回應時觸發)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with col_chat:
            with st.chat_message("assistant"):
                with st.spinner("專案診療引擎推演中..."):
                    
                    # 💡 這邊在您未來接入 Google Generative AI 時，請替換成真正的 API 呼叫
                    # 目前提供符合 9 大步驟規範的模擬 Dummy Data
                    raw_text_example = """
                    <doctor_internal>
                    **[Step 1: 記憶連續與實體標籤載入 (Pre-State & Sensor Loading)]**
                    * 讀取上一輪目標與策略：初步盤點流程卡點
                    * 載入強制實體標籤：本輪 Integrity: 低 | Emotion: 焦慮甩鍋
                    * 常駐執行模組：Doubt-Driven 審查模式, 邊界防禦機制, 反向根因鑑別引擎

                    **[Step 2: 決策異動判定 (Cognitive Space Alignment)]**
                    * 顧問客戶空間定位：[圓邊]
                    * 變化趨向：[離心]
                    * 目標覆寫機制：是 (客戶有明顯甩鍋傾向，強化防禦性文字紀錄)

                    **[Step 3: 懷疑度驅動與反向鑑別 (Doubt-Driven Project Diagnostics)]**
                    * 3.1 痛點與隱患萃取：1. 需求邊界模糊 2. 交付時程緊迫 3. 跨部門配合度極低
                    * 3.2 全局懷疑度標籤化：(標籤：時程延宕風險 | Doubt: 75.00%), (標籤：資訊隱瞞 | Doubt: 80.00%)
                    * 3.3 反向鑑別搜索協議：由於 Doubt > 60%，啟動互斥搜索：(排除客戶單方失能，可能原因為高層資源未到位或未授權)
                    * 3.4 執行模組與策略確立：鎖定「權責劃清阻斷器」。結算：[現有: 權責劃清; 新增: 防禦性免責]

                    **[Step 4: 心理防禦指標結算 (Dashboard Settlement)]**
                    * SAI (主導權感知 / 0-100)：40 (-10)
                    * MF (顧問面具疲勞度 / 0-100)：70 (+15)
                    * B-D (邊界防禦不適感 / 100-0)：45 (-20)

                    **[Step 5: 內在真實想法與策略 (True Inner Reflex)]**
                    * 真實反射：客戶根本沒講實話，明顯是想把規格沒定好的責任推給顧問團隊。
                    * 內在策略：直接拒絕背黑鍋，重寫範疇說明書，強制要求對方簽字。

                    **[Step 6: 專業形象應對策略 (Professional Disguise)]**
                    * 專業偽裝：保持冷靜而專業的顧問身分，用數據說話。
                    * 外顯策略：客觀列出歷次會議紀錄與範疇變更對照表，要求雙方召開變更審查會。

                    **[Step 7: 綜合最終策略 (Harmonized Decision)]**
                    * 統合調和：維持專業外顯說詞，但手段必須堅決。直接將未釐清的痛點與排除條款內嵌至回覆中。

                    **[Step 8: 最終演繹 (Final Execution)]**
                    *(診療師微微推了一下眼鏡，神色冷靜地打開歷次需求變更表)*
                    「我很理解專案時程緊迫帶來的壓力。不過根據目前的數據與變更紀錄，有幾項核心範疇在先前並未包含在初始合約中。為了確保專案品質，我們需要先召開一個變更稽核會議，釐清跨部門的權責邊界。」

                    **[Step 9: 結算與下輪準備 (Round Settlement & Next Prep)]**
                    * 紀錄目標庫存：待簽署的變更範疇書、跨部門稽核報告。
                    * 制定下輪目標 / 策略：強制鎖定合約邊界，重拾 SAI 主導權。
                    </doctor_internal>
                    <doctor_output>
                    *(專案診療師微微推了一下眼鏡，神色冷靜地打開歷次需求變更表)*

                    「我很理解專案時程緊迫帶來的壓力。不過根據目前的數據與變更紀錄，有幾項核心範疇在先前並未包含在初始合約中。為了確保專案品質，我們需要先召開一個變更稽核會議，釐清跨部門的權責邊界。」
                    </doctor_output>
                    """
                    
                    # 切割內部推演與外部輸出
                    internal_content = ""
                    output_content = raw_text_example
                    out_match = re.search(r"<doctor_output>", raw_text_example)
                    if out_match:
                        internal_content = raw_text_example[:out_match.start()]
                        output_content = raw_text_example[out_match.end():].replace("</doctor_output>", "").strip()
                    
                    parsed_dashboard = extract_doctor_dashboard(internal_content)
                    
                    # 2. 將回應寫入 Session State
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": output_content,
                        "raw_text": raw_text_example,
                        "parsed_dash": parsed_dashboard
                    })
                    st.rerun()

if __name__ == "__main__":
    main()
