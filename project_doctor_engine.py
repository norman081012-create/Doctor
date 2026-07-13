# ==========================================
# project_doctor_engine.py (v2.5)
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
    """提取特定 XML 標籤內的內容"""
    match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_doctor_dashboard(clinical_text):
    """從引擎的內部推演區塊提取 Phase 狀態與完整紀錄"""
    if not clinical_text: 
        return {}
    return {
        "current_phase": extract_tag_content("current_phase", clinical_text),
        "full_internal": clinical_text
    }

def generate_raw_text(api_key, selected_model, system_prompt, prompt_text):
    """底層 API 呼叫，回傳純文字結果（包含 ResourceExhausted 自動重試機制）"""
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    
    max_retries = 3
    base_wait_time = 5  # 基礎等待秒數
    
    for attempt in range(max_retries):
        try:
            response = model_inst.generate_content(prompt_text)
            return response.text
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                sleep_time = base_wait_time * (2 ** attempt)
                print(f"達到 API 速率限制 (ResourceExhausted)，將於 {sleep_time} 秒後重試... (第 {attempt + 1}/{max_retries} 次)")
                time.sleep(sleep_time)
            else:
                # 若重試三次仍失敗，則將錯誤拋出給 Streamlit
                raise e

def parse_chat_response(full_text):
    """
    精準分離前端對話文字與後端 XML 狀態。
    將 <clinical_engine> 內部的推演與外部的 Step 3 (對話) 切開。
    """
    # 移除可能的 markdown 程式碼區塊標記
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE).strip()
    
    # 提取 <clinical_engine> 標籤內部所有內容
    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", clean_text, flags=re.IGNORECASE | re.DOTALL)
    
    if engine_match:
        engine_xml = engine_match.group(1).strip()
        # 把整個 <clinical_engine> 區塊拔掉，剩下的就是給病患的對話文字
        chat_text = re.sub(r"<clinical_engine>.*?</clinical_engine>", "", clean_text, flags=re.IGNORECASE | re.DOTALL).strip()
    else:
        # 若模型沒有照格式輸出 XML 標籤 (防呆)
        engine_xml = ""
        chat_text = clean_text
    
    return {
        "chat_text": chat_text,
        "parsed_dash": extract_doctor_dashboard(engine_xml),
        # 保存這輪完整的 XML 內容，準備當作下一輪的 previous_soap 送回 Prompt
        "raw_xml": f"<clinical_engine>\n{engine_xml}\n</clinical_engine>" if engine_xml else ""
    }
