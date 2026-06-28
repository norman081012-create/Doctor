# ==========================================
# project_doctor_engine.py
# ==========================================
import re
import google.generativeai as genai

def fetch_available_models(api_key):
    """向 Google API 請求當前帳號可用的模型清單[cite: 5]"""
    try:
        genai.configure(api_key=api_key)
        return [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        return []

def extract_doctor_dashboard(clinical_text):
    """精準提取臨床博弈引擎內部推演數據，針對 v2.1 引擎獨立抽出真實 SOAP 區塊[cite: 4, 5]"""
    if not clinical_text: return {}

    # 直接從原始文本中利用無損正則提取 Step 4 的 SOAP Note 全貌，確保 Markdown 格式標籤不被破壞
    soap_match = re.search(r"【Step 4:[^】]*?SOAP Note\)】\s*(.*?)(?=\n\s*【Step 5|\Z)", clinical_text, flags=re.IGNORECASE | re.DOTALL)
    soap_content = soap_match.group(1).strip() if soap_match else "未解析到完整 SOAP 病歷資料[cite: 4]"

    return {
        "soap": soap_content
    }

def process_doctor_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    """驅動核心醫療博弈運算，與大模型對話並切分臨床推演與外部演繹[cite: 5]"""
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
    
    # 調整為動態過濾 Step 5 標籤
    output_text = re.sub(r"【?Step 5[:：].*?】?\n?", "", output_text, flags=re.IGNORECASE).strip()

    if not output_text:
        output_text = "*(醫師暫默，低頭檢視病歷，持續觀察病患反應)*"

    return {
        "internal": clinical_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
