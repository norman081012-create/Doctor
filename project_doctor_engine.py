# ==========================================
# project_doctor_engine.py (v2.1 摰霁敍?舀鹁??
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
    """?栀??孵? XML 璅⒢惜?抒??批捆"""
    match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_doctor_dashboard(clinical_text):
    """敺霶??怿??折们?冽??憛簧??綤???SAP ?詨?璅⒢惜"""
    if not clinical_text: 
        return {}
    return {
        "soap_s": extract_tag_content("soap_s", clinical_text),
        "soap_a": extract_tag_content("soap_a", clinical_text),
        "soap_p": extract_tag_content("soap_p", clinical_text)
    }

def generate_raw_text(api_key, selected_model, system_prompt, prompt_text):
    """摨刧惜 API ?澆韪嚗鉴??喟??枞?蝯栁?"""
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    response = model_inst.generate_content(prompt_text)
    return response.text

def parse_chat_response(full_text):
    """
    蝎暹??尽漄?讵垢撠诎店?枞??枞?蝡?XML ??骗?    撠?<clinical_engine> ?折们?栋铫瞍鯒?憭緥们??Step 5 (撠诎店) ?浆???    """
    # 蝘駁妚?航泾??markdown 蝔鲳?蝣澆?憛簧?閮?    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE).strip()
    
    # ?栀? <clinical_engine> 璅⒢惜?折们??桧须摰?    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", clean_text, flags=re.IGNORECASE | re.DOTALL)
    
    if engine_match:
        engine_xml = engine_match.group(1).strip()
        # ?簧敍??<clinical_engine> ?憛簧??涩??拐??枣停?舐策?盏倶?枣?閰望?摮?        chat_text = re.sub(r"<clinical_engine>.*?</clinical_engine>", "", clean_text, flags=re.IGNORECASE | re.DOTALL).strip()
    else:
        # ?交芋?鲭??樯须?澆?頛詨婵 XML 璅⒢惜 (?脣?)
        engine_xml = ""
        chat_text = clean_text
    
    return {
        "chat_text": chat_text,
        "parsed_dash": extract_doctor_dashboard(engine_xml),
        # 靽㎡??⒣憚摰霁敍??XML ?批捆嚗霁??⒢珏雿?銝頛芰? previous_soap ?癴? Prompt
        "raw_xml": f"<clinical_engine>\n{engine_xml}\n</clinical_engine>" if engine_xml else ""
    }

# 靽㎥??蓤珻?枣腙?凵铫瞍鯑灜摰寞改?憒弴?敺鞑??栋??桃??蓤??残?瘙恠?
def process_doctor_turn(api_key, selected_model, system_prompt, forced_template_text):
    full_text = generate_raw_text(api_key, selected_model, system_prompt, forced_template_text)
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE)
    clinical_text = re.sub(r"</?clinical_engine>", "", clean_text, flags=re.IGNORECASE).strip()
    
    return {
        "internal": clinical_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
