# ==========================================
# project_doctor_engine.py (部分更新：解析強化)
# ==========================================
import re
import time
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

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
        "full_internal": clinical_text
    }

def generate_raw_text(api_key, selected_model, system_prompt, prompt_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    
    max_retries = 3
    base_wait_time = 5 
    
    for attempt in range(max_retries):
        try:
            response = model_inst.generate_content(prompt_text)
            return response.text
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                sleep_time = base_wait_time * (2 ** attempt)
                print(f"達到 API 速率限制，將於 {sleep_time} 秒後重試... (第 {attempt + 1}/{max_retries} 次)")
                time.sleep(sleep_time)
            else:
                raise e

def parse_chat_response(full_text):
    """
    【修復點】：精準分離前端對話文字與後端 XML 狀態，不被模型隨機輸出的 Markdown 干擾。
    """
    # 直接在完整文本中尋找 <clinical_engine> 標籤
    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", full_text, flags=re.IGNORECASE | re.DOTALL)
    
    if engine_match:
        engine_xml = engine_match.group(1).strip()
        # 把整個 <clinical_engine> 區塊 (包含標籤) 拔掉
        chat_text = re.sub(r"<clinical_engine>.*?</clinical_engine>", "", full_text, flags=re.IGNORECASE | re.DOTALL).strip()
        # 清理可能殘留的 ```xml 或 ``` 標記
        chat_text = re.sub(r"```[a-z]*\n|\n```|```", "", chat_text, flags=re.IGNORECASE).strip()
    else:
        # 防呆：若模型沒照格式輸出，就全部當成對話
        engine_xml = ""
        chat_text = re.sub(r"```[a-z]*\n|\n```|```", "", full_text, flags=re.IGNORECASE).strip()
    
    # 強制組裝完整 XML
    full_xml_string = f"<clinical_engine>\n{engine_xml}\n</clinical_engine>" if engine_xml else ""

    return {
        "chat_text": chat_text,
        "parsed_dash": extract_doctor_dashboard(engine_xml),
        "raw_xml": full_xml_string
    }
