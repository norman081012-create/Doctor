# ==========================================
# project_doctor_engine.py
# ==========================================
import re
import google.generativeai as genai

def fetch_available_models(api_key):
    try:
        genai.configure(api_key=api_key)
        return [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception:
        return []

def extract_tag_content(tag_name, text):
    """精準提取特定 XML 標籤內的內容"""
    match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_doctor_dashboard(clinical_text):
    """精準提取臨床博弈引擎的模組化結構"""
    if not clinical_text: return {}
    return {
        "clinical_summary": extract_tag_content("clinical_summary", clinical_text),
        "doubt_assessment": extract_tag_content("doubt_assessment", clinical_text),
        "soap_s": extract_tag_content("soap_s", clinical_text),
        "soap_o": extract_tag_content("soap_o", clinical_text),
        "soap_a": extract_tag_content("soap_a", clinical_text),
        "soap_p": extract_tag_content("soap_p", clinical_text)
    }

def parse_doubt_assessment(text):
    """正則解析鑑別診斷行，完美支援帶有內部括號的診斷（如 MASLD/NASH）"""
    items = []
    if not text: return items
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line: continue
        # 利用 (附帶簡短說明：) 作為分割錨點，排除疾病名稱內部的其他括號干擾
        match = re.search(r"-\s*\[(.*?)\]\s*(.*?)(?:\((附帶簡短說明：.*?)\))?$", line)
        if match:
            prob = match.group(1).strip()
            title = match.group(2).strip()
            desc = match.group(3).strip() if match.group(3) else "無詳細說明"
            items.append({"prob": prob, "title": title, "desc": desc})
        else:
            items.append({"prob": "評估", "title": line, "desc": "未解析到說明"})
    return items

def process_doctor_turn(api_key, selected_model, system_prompt, forced_template_text):
    """改採單次結構化運算核心，確保輸出不受對話歷史污染"""
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    
    response = model_inst.generate_content(forced_template_text)
    full_text = response.text
    
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE)
    clinical_text = re.sub(r"</?clinical_engine>", "", clean_text, flags=re.IGNORECASE).strip()
    
    return {
        "internal": clinical_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
