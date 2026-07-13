# ==========================================
# project_doctor_engine.py (v2.4 無病歷版)
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

def extract_engine_status(clinical_text):
    """
    v2.4 刪除 SOAP 病歷輸出。
    只擷取引擎的運作狀態，供除錯或後台邏輯追蹤。
    """
    if not clinical_text: 
        return {}
    return {
        "current_phase": extract_tag_content("current_phase", clinical_text),
        "opqrst_status": extract_tag_content("opqrst_status", clinical_text)
    }

def generate_raw_text(api_key, selected_model, system_prompt, prompt_text):
    """底層 API 呼叫，回傳純文字結果"""
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    response = model_inst.generate_content(prompt_text)
    return response.text

def parse_chat_response(full_text):
    """
    精準分離前端對話文字與後端 XML 推演狀態。
    """
    # 移除可能的 markdown 程式碼區塊標記
    clean_text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", full_text, flags=re.MULTILINE).strip()
    
    # 提取 <clinical_engine> 標籤內部所有內容
    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", clean_text, flags=re.IGNORECASE | re.DOTALL)
    
    if engine_match:
        engine_xml = engine_match.group(1).strip()
        # 把 <clinical_engine> 區塊拔掉，剩下的純文字就是對病患的回覆
        chat_text = re.sub(r"<clinical_engine>.*?</clinical_engine>", "", clean_text, flags=re.IGNORECASE | re.DOTALL).strip()
    else:
        engine_xml = ""
        chat_text = clean_text
    
    return {
        "chat_text": chat_text,
        "engine_status": extract_engine_status(engine_xml),
        # 若未來仍需追蹤整段思考脈絡，保留 raw_xml 
        "raw_xml": f"<clinical_engine>\n{engine_xml}\n</clinical_engine>" if engine_xml else ""
    }
