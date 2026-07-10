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
    match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_doctor_dashboard(clinical_text):
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
    items = []
    if not text: return items
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line: continue
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

def generate_raw_text(api_key, selected_model, system_prompt, prompt_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    response = model_inst.generate_content(prompt_text)
    return response.text

def parse_chat_response(full_text):
    """從包含 XML 的回覆中切分出前端對話文字與後端 XML 狀態"""
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE).strip()
    
    # 提取 XML 前面的對話文字
    chat_text = re.split(r"<clinical_engine>", clean_text, flags=re.IGNORECASE)[0].strip()
    
    # 提取標籤內容
    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", clean_text, flags=re.IGNORECASE | re.DOTALL)
    engine_xml = engine_match.group(1).strip() if engine_match else ""
    
    return {
        "chat_text": chat_text,
        "parsed_dash": extract_doctor_dashboard(engine_xml),
        "raw_xml": engine_xml
    }
