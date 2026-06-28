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
    return match.group(1).strip() if match else f"未解析到 {tag_name} 內容"

def extract_doctor_dashboard(clinical_text):
    """精準提取臨床博弈引擎的時相、Doubt 排序與拆分的 SOAP 紀錄"""
    if not clinical_text: return {}
    return {
        "phase": extract_tag_content("phase", clinical_text),
        "doubt_assessment": extract_tag_content("doubt_assessment", clinical_text),
        "soap_s": extract_tag_content("soap_s", clinical_text),
        "soap_o": extract_tag_content("soap_o", clinical_text),
        "soap_a": extract_tag_content("soap_a", clinical_text),
        "soap_p": extract_tag_content("soap_p", clinical_text)
    }

def process_doctor_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    chat = model_inst.start_chat(history=history_for_api)

    response = chat.send_message(forced_template_text)
    full_text = response.text

    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE)

    clinical_text = ""
    output_text = clean_text
    out_match = re.search(r"<doctor_output>", clean_text, flags=re.IGNORECASE)

    if out_match:
        clinical_text = clean_text[:out_match.start()]
        output_text = clean_text[out_match.end():]
    else:
        in_close_match = re.search(r"</clinical_engine>", clean_text, flags=re.IGNORECASE)
        if in_close_match:
            clinical_text = clean_text[:in_close_match.end()]
            output_text = clean_text[in_close_match.end():]

    output_text = re.sub(r"</?doctor_output>", "", output_text, flags=re.IGNORECASE).strip()
    clinical_text = re.sub(r"</?clinical_engine>", "", clinical_text, flags=re.IGNORECASE).strip()

    output_text = re.sub(r"【?Step 5[:：].*?】?\n?", "", output_text, flags=re.IGNORECASE).strip()
    if not output_text:
        output_text = "*(醫師暫默，低頭檢視病歷，持續觀察病患反應)*"

    return {
        "internal": clinical_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
