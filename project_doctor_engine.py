# ==========================================
# project_doctor_engine.py (v2.1 完整支援版)
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

def parse_diagnoses(soap_a_text):
    """
    從 Assessment 中精準提取診斷，並轉換為 [診斷] -> [檢查項目] 的格式。
    """
    if not soap_a_text:
        return []
        
    lines = soap_a_text.split('\n')
    results = []
    
    for line in lines:
        # 清理行首的 markdown 與空白符號
        line = line.strip().replace('**', '')
        if not line:
            continue
            
        # 匹配 r/o [診斷] need further [處置] 或 suspected [診斷] need further [處置]
        m_need = re.search(r'(?:r/o|suspected)\s+(.+?)\s+need further\s+(.+)', line, re.IGNORECASE)
        if m_need:
            diag = m_need.group(1).strip()
            plan = m_need.group(2).strip()
            results.append(f"{diag} -> {plan}")
            continue
            
        # 匹配尚未問診的 DDX [診斷]
        m_ddx = re.search(r'(?:DDX|DDx)\s+(.+)', line, re.IGNORECASE)
        if m_ddx:
            results.append(m_ddx.group(1).strip())
            continue
            
    return results

def extract_doctor_dashboard(clinical_text):
    """從引擎的內部推演區塊提取三個 SAP 核心標籤與解析後的診斷"""
    if not clinical_text: 
        return {}
    
    soap_a = extract_tag_content("soap_a", clinical_text)
    
    return {
        "soap_s": extract_tag_content("soap_s", clinical_text),
        "soap_a": soap_a,
        "soap_p": extract_tag_content("soap_p", clinical_text),
        "diagnoses": parse_diagnoses(soap_a) # 新增解析診斷清單
    }

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

# 保留原本的單向推演相容性
def process_doctor_turn(api_key, selected_model, system_prompt, forced_template_text):
    full_text = generate_raw_text(api_key, selected_model, system_prompt, forced_template_text)
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE)
    clinical_text = re.sub(r"</?clinical_engine>", "", clean_text, flags=re.IGNORECASE).strip()
    
    return {
        "internal": clinical_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
