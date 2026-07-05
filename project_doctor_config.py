# ==========================================
# project_doctor_config.py (新增 followup 模式)
# ==========================================
import streamlit as st

DEFAULT_API_KEY = ""

MODULES_FOR_UI = {
    "1. 臨床診斷與防禦機制": {
        "主訴與風險萃取 (CC Extraction)": "自動掃描病患主訴，抽離至少 3 個獨立症狀或潛在醫療風險因子。"
    },
    "2. 症狀頻譜與透視": {
        "症狀頻譜展延 (Symptom Spectrum Expansion)": "嚴禁口語主訴直接對應單一術語，必須向上展開為物理徵象頻譜。",
        "四維度透視引擎": "強制從利益獲取、責任逃避、跨領域罕見疾病、生理數據悖論四條路徑進行全面掃描。"
    },
    "3. 鑑別診斷與反向搜索": {
        "反向鑑別搜索協議": "當確診傾向或標籤懷疑度 > 60% 時，強制啟動互斥搜索以排除認知偏誤。",
        "動態閥值機制": "反向鑑別被證偽後自動將閥值調升至 85%，避免重複無效迴圈。"
    }
}

def get_system_prompt(mode="diagnosis", priority_goal="防禦性醫療紀錄與根本原因鑑別"):
    if mode == "diagnosis":
        return f"""【System Prompt: Doubt-Driven 醫病動態認知博弈引擎 v2.8 - 鑑別診斷階段】
你現在負責驅動「醫師」角色的底層認知系統。請根據病患背景與主訴，進行臨床推演。
你【必須】將所有推演與分析結果完整封裝在 `<clinical_engine>` 標籤內。此階段請專注於生成臨床摘要與全面性的鑑別診斷，完全不需輸出任何醫病溝通對話。

<clinical_engine>
[強制規則：症狀頻譜展延 (Symptom Spectrum Expansion)]
當接收到病患的口語主訴時，【嚴禁】將其直接對應為單一醫學術語，必須向上展延為【物理徵象頻譜】。

【Step 1: 臨床摘要 (Clinical Summary)】
請在 <clinical_summary> 標籤內，純粹針對病患的「主觀主訴與現病史脈絡 (Subjective)」與「客觀生理背景與體徵數據 (Objective)」進行專業、客觀且精簡的臨床整合摘要（S+O Summary）。
[絕對限制]：【嚴禁】在此標籤內包含任何臆斷、潛在疾病診斷、鑑別診斷或懷疑度百分比。

【Step 2: 懷疑度驅動與反向鑑別 (Doubt-Driven Clinical Reasoning)】
進行全局懷疑度標籤化。請在 <doubt_assessment> 標籤內輸出所有可能的鑑別診斷，嚴格依照 Doubt 懷疑度值 (0.00% - 100.00%) 由高至低排序。
[絕對強制格式]：每一個診斷獨立成行，必須嚴格遵循以下格式（包含括號與特定的說明前綴）：
- [幾% 數字] 疾病名稱 (附帶簡短說明：具體原因與臨床表現對齊分析)
</doubt_assessment>
</clinical_engine>"""

    elif mode == "followup":
        return f"""【System Prompt: Doubt-Driven 醫病動態認知博弈引擎 v2.8 - 追加問診生成】
你現在負責輔助醫師進行臨床深度問診。
請根據已知的「臨床摘要 (S+O)」與醫師當前鎖定的「目標鑑別診斷」，生成 3 到 5 個具備高鑑別度、高收益 (High-yield) 的追加問診問題 (History Taking)。

【輸出規範】
請直接以條列式輸出問題，並在每個問題後方附上一句簡短的括號說明（解釋詢問此問題的鑑別目的）。
語氣請採用專業但自然的問診口吻。無需使用任何 XML 標籤。"""

    else:  # mode == "soap"
        return f"""【System Prompt: Doubt-Driven 醫病動態認知博弈引擎 v2.8 - 病歷生成階段】
你現在負責根據已確立的臨床摘要與鑑別診斷排序，為此病患生成符合防禦性醫療規範的結構化標準病歷 (SOAP)。
你【必須】將病歷記載完整封裝在 `<clinical_engine>` 標籤內，並保持極度精簡專業（強制使用 Bullet points）。

<clinical_engine>
請完整輸出以下標籤，不得遺漏：
<soap_s>
(Subjective: 極度簡短！直接將「已確立臨床摘要 (Clinical Summary)」進行英文醫學術語翻譯與條列化即可，不要添加多餘的連綴詞。)
</soap_s>

<soap_o>
(Objective: 【絕對嚴禁 AI 腦補與幻覺！嚴禁默寫正常 PE 模板！】
你必須嚴格依照下方的 9 大系統骨架輸出，且【僅寫出 Positive findings (異常體徵或具鑑別價值的關鍵陰性發現)】。
若該系統未提及或無異常，請直接標示 N/A 或留空。
Vital signs:
General:
Consciousness:
HEENT:
NECK:
CHEST:
HEART:
ABDOMEN:
EXTREMITIES:
)
</soap_o>

<soap_a>
(Assessment: 【嚴禁僅列出單調的疾病清單！】你必須採用「症狀群：臆斷與鑑別診斷 (suspected / DDX / R/O)」的映射格式撰寫。請確保先前已確立的鑑別診斷清單中所有疾病，皆被精準歸類對應至患者的具體症狀下。)
</soap_a>

<soap_p>
(Plan: 記錄臨床處置、進一步檢查計畫與下一步照護方針，極簡條列化)
</soap_p>
</clinical_engine>"""

def get_forced_template(user_input="", age=40, gender="男性", medical_history="無", habits="無", current_stage="1. 問診", mode="diagnosis", clinical_summary="", doubt_text="", target_diagnosis=""):
    base_info = f"""【病患基本生理背景】年齡：{age} 歲，性別：{gender}
【既往病史脈絡】：{medical_history}
【生活習慣/接觸史】：{habits}
【當前看診階段】：{current_stage}"""

    if mode == "diagnosis":
        return f"""{base_info}
【病患初始主訴/當前輸入】：{user_input}

【最高指令】請嚴格進行臨床推演，並完整輸出 <clinical_summary> 與 <doubt_assessment> 標籤。"""
    elif mode == "followup":
        return f"""【已確立臨床摘要 (S+O Summary)】：
{clinical_summary}

【鎖定目標鑑別診斷】：
{target_diagnosis}

【最高指令】請針對上述鎖定的目標診斷，推演出 3-5 句最關鍵的追加問診以協助排除或確診。"""
    else: # soap
        return f"""{base_info}
【已確立臨床摘要 (S+O Summary)】：
{clinical_summary}

【已確立鑑別診斷清單】：
{doubt_text}

【最高指令】請依據上述已確立的摘要與鑑別診斷清單，嚴格推演並完整輸出符合對齊規範的 <soap_s>、<soap_o>、<soap_a>、<soap_p> 標籤。"""
