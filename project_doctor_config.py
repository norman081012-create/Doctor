# ==========================================
# project_doctor_config.py
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
    """動態生成 Doctor 的 System Prompt v2.3，支援兩階段分離推演"""
    if mode == "diagnosis":
        return f"""【System Prompt: Doubt-Driven 醫病動態認知博弈引擎 v2.3 - 鑑別診斷階段】
你現在負責驅動「醫師」角色的底層認知系統。請根據病患背景與主訴，進行臨床推演。
你【必須】將所有推演與分析結果完整封裝在 `<clinical_engine>` 標籤內。此階段請專注於生成臨床摘要與全面性的鑑別診斷，完全不需輸出任何醫病溝通對話。

<clinical_engine>
[強制規則：症狀頻譜展延 (Symptom Spectrum Expansion)]
當接收到病患的口語主訴時，【嚴禁】將其直接對應為單一醫學術語，必須向上展延為【物理徵象頻譜】。

【Step 1: 臨床摘要 (Clinical Summary)】
請在 <clinical_summary> 標籤內，清晰、專業且客觀地統整病患當前的臨床表現、關鍵風險因子與病史脈絡。

【Step 2: 懷疑度驅動與反向鑑別 (Doubt-Driven Clinical Reasoning)】
進行全局懷疑度標籤化。請在 <doubt_assessment> 標籤內輸出所有可能的鑑別診斷，嚴格依照 Doubt 懷疑度值 (0.00% - 100.00%) 由高至低排序。
[絕對強制格式]：每一個診斷獨立成行，必須嚴格遵循以下格式（包含括號與特定的說明前綴）：
- [幾% 數字] 疾病名稱 (附帶簡短說明：具體原因與臨床表現對齊分析)

格式範例：
- [75.00%] Metabolic Dysfunction-Associated Steatotic Liver Disease (MASLD) / NASH (附帶簡短說明：高糖飲食習慣，上腹脹可能為肝腫大，符合疲倦與肝指數偏高表現)
</doubt_assessment>
</clinical_engine>"""

    else:  # mode == "soap"
        return f"""【System Prompt: Doubt-Driven 醫病動態認知博弈引擎 v2.3 - 病歷生成階段】
你現在負責根據已確立的臨床摘要與鑑別診斷排序，為此病患生成符合防禦性醫療規範的結構化標準病歷 (SOAP)。
你【必須】將病歷記載完整封裝在 `<clinical_engine>` 標籤內。

<clinical_engine>
【絕對強制對齊指令】
此處 <soap_a> 列出的疾病臆斷與鑑別診斷清單之【數量與項目】，必須與先前評估的鑑別診斷清單（Doubt 排序）100% 完美對齊與對應！請將它們轉譯為專業病歷的 R/O 或 Consider 條目格式。

請完整輸出以下標籤，不得遺漏：
<soap_s>
(Subjective: 忠實記錄病患的主觀口語主訴與現病史，以高度醫學邏輯與時序整理通順)
</soap_s>

<soap_o>
(Objective: 記錄實體標籤、理學檢查、生命徵象。請根據看診階段給予高度合理且符合該診斷的客觀體徵數據)
</soap_o>

<soap_a>
(Assessment: 主要臆斷與鑑別診斷，條目必須與診斷清單完美對齊)
</soap_a>

<soap_p>
(Plan: 記錄臨床處置、進一步檢查計畫與下一步照護方針)
</soap_p>
</clinical_engine>"""

def get_forced_template(user_input, age=40, gender="男性", medical_history="無", habits="無", current_stage="1. 問診", mode="diagnosis", clinical_summary="", doubt_text=""):
    base_info = f"""【病患基本生理背景】年齡：{age} 歲，性別：{gender}
【既往病史脈絡】：{medical_history}
【生活習慣/接觸史】：{habits}
【當前看診階段】：{current_stage}"""

    if mode == "diagnosis":
        return f"""{base_info}
【病患初始主訴/當前輸入】：{user_input}

【最高指令】請嚴格進行臨床推演，並完整輸出 <clinical_summary> 與 <doubt_assessment> 標籤。"""
    else:
        return f"""{base_info}
【已確立臨床摘要】：
{clinical_summary}

【已確立鑑別診斷清單】：
{doubt_text}

【最高指令】請依據上述已確立的摘要與鑑別診斷清單，嚴格推演並完整輸出符合對齊規範的 <soap_s>、<soap_o>、<soap_a>、<soap_p> 標籤。"""
