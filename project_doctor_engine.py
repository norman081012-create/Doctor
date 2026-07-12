# ==========================================
# project_doctor_engine.py (v2.3)
# 變更摘要：
#   [NEW] extract_doctor_dashboard 增加 qa_ledger / cc_profile / ros_ledger / soap_o
#   [NEW] audit_gaps()      —— 計算未特徵化欄位與未問 ROS 數量，供 UI 亮紅燈
#   [NEW] audit_fabrication() —— 客觀端交叉比對：SOAP 是否出現帳本中不存在的陽性
# ==========================================
import re
import google.generativeai as genai


def fetch_available_models(api_key):
    try:
        genai.configure(api_key=api_key)
        return [
            m.name.replace("models/", "")
            for m in genai.list_models()
            if 'generateContent' in m.supported_generation_methods
        ]
    except Exception:
        return []


def extract_tag_content(tag_name, text):
    """提取特定 XML 標籤內的內容"""
    match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_doctor_dashboard(clinical_text):
    """從引擎的內部推演區塊提取所有監控標籤"""
    if not clinical_text:
        return {}
    tags = [
        "qa_ledger", "positive_findings", "negative_findings",
        "cc_profile", "ros_ledger",
        "soap_s", "soap_o", "soap_a", "soap_p",
    ]
    return {t: extract_tag_content(t, clinical_text) for t in tags}


# ------------------------------------------
# 稽核層：不信任 LLM 自律，由 code 端硬檢查
# ------------------------------------------
def audit_gaps(dash):
    """回傳問診缺口計數。兩者歸零前，禁止結案。"""
    cc = dash.get("cc_profile", "") or ""
    ledger = dash.get("ros_ledger", "") or ""
    return {
        "cc_unknown": cc.count("[UNKNOWN]"),
        "ros_unasked": ledger.count("[未問]"),
    }


def audit_fabrication(dash):
    """
    交叉比對：檢查 SOAP 的 S/P 是否出現「帳本中標記為 [-] 的症狀」。
    以 negative_findings 的關鍵詞去掃 soap_s / soap_p，命中即為疑似造假。
    這是最後一道防線 —— prompt 可能失守，但 code 不會。
    """
    neg_block = dash.get("negative_findings", "") or ""
    s_text = (dash.get("soap_s", "") or "")
    p_text = (dash.get("soap_p", "") or "")

    # 從 negative_findings 抽出條列項目的核心名詞（去除 bullet 與括號註解）
    neg_items = []
    for line in neg_block.splitlines():
        item = re.sub(r"^[\s\-\*\u2022\d\.\)]+", "", line).strip()
        item = re.sub(r"[\(（].*?[\)）]", "", item).strip()
        if len(item) >= 2:
            neg_items.append(item)

    # 只比對 Pertinent Negatives 段落「以外」的 S 內容，避免自我誤判
    s_positive_zone = re.split(r"\[?Pertinent Negatives\]?", s_text, flags=re.IGNORECASE)[0]

    hits = []
    for item in neg_items:
        # 取項目前 6 字元作為指紋，降低格式差異造成的漏抓
        fp = item[:6]
        if fp and (fp in s_positive_zone or fp in p_text):
            hits.append(item)

    return {"suspected_fabrication": hits}


def generate_raw_text(api_key, selected_model, system_prompt, prompt_text):
    """底層 API 呼叫，回傳純文字結果"""
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    response = model_inst.generate_content(prompt_text)
    return response.text


def parse_chat_response(full_text):
    """
    精準分離前端對話文字與後端 XML 狀態。
    將 <clinical_engine> 內部的推演與外部的 Step 5 (對話) 切開。
    """
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE).strip()

    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", clean_text,
                             flags=re.IGNORECASE | re.DOTALL)

    if engine_match:
        engine_xml = engine_match.group(1).strip()
        chat_text = re.sub(r"<clinical_engine>.*?</clinical_engine>", "", clean_text,
                           flags=re.IGNORECASE | re.DOTALL).strip()
    else:
        engine_xml = ""
        chat_text = clean_text

    dash = extract_doctor_dashboard(engine_xml)

    return {
        "chat_text": chat_text,
        "parsed_dash": dash,
        "gaps": audit_gaps(dash),
        "fabrication": audit_fabrication(dash),
        # 完整 XML 回傳，作為下一輪 previous_soap 送回 Prompt（帳本因此得以跨輪累積）
        "raw_xml": f"<clinical_engine>\n{engine_xml}\n</clinical_engine>" if engine_xml else "",
    }
