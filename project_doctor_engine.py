# ==========================================
# project_doctor_engine.py (v2.4)
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
    match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_doctor_dashboard(clinical_text):
    if not clinical_text: 
        return {}
    return {
        "current_phase": extract_tag_content("current_phase", clinical_text),
        "opqrst_status": extract_tag_content("opqrst_status", clinical_text)
    }

def generate_raw_text(api_key, selected_model, system_prompt, prompt_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    response = model_inst.generate_content(prompt_text)
    return response.text

def parse_chat_response(full_text):
    clean_text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", full_text, flags=re.MULTILINE).strip()
    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", clean_text, flags=re.IGNORECASE | re.DOTALL)
    
    if engine_match:
        engine_xml = engine_match.group(1).strip()
        chat_text = re.sub(r"<clinical_engine>.*?</clinical_engine>", "", clean_text, flags=re.IGNORECASE | re.DOTALL).strip()
    else:
        engine_xml = ""
        chat_text = clean_text
    
    return {
        "chat_text": chat_text,
        "parsed_dash": extract_doctor_dashboard(engine_xml),
        "raw_xml": f"<clinical_engine>\n{engine_xml}\n</clinical_engine>" if engine_xml else ""
    }

def process_doctor_turn(api_key, selected_model, system_prompt, forced_template_text):
    full_text = generate_raw_text(api_key, selected_model, system_prompt, forced_template_text)
    clean_text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", full_text, flags=re.MULTILINE)
    clinical_text = re.sub(r"</?clinical_engine>", "", clean_text, flags=re.IGNORECASE).strip()
    
    return {
        "internal": clinical_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
