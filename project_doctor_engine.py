# ==========================================
# project_doctor_engine.py
# ==========================================
import re
import google.generativeai as genai

def fetch_available_models(api_key):
    """向 Google API 請求當前帳號可用的模型清單"""
    try:
        genai.configure(api_key=api_key)
        return [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        return []

def extract_doctor_dashboard(clinical_text):
    """精準提取臨床博弈引擎內部推演數據，轉譯為儀表板變數（已優化線性防護）"""
    if not clinical_text: return {}
    plain = clinical_text.replace('**', '').replace('* ', '')

    def ext_line(pattern):
        m = re.search(pattern, plain, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else "未解析到資料"

    return {
        "location": ext_line(r"醫病空間定位[：:]\s*([^\n]*)"),
        "trend": ext_line(r"變化趨向[：:]\s*([^\n]*)"),
        "cc_extract": ext_line(r"3\.1 主訴與風險萃取[^\n]*?[：:]\s*(.*?)(?=\n\s*3\.2|\n\s*【|\Z)"),
        "doubt_tagging": ext_line(r"3\.2 全局懷疑度標籤化[^\n]*?[：:]\s*(.*?)(?=\n\s*3\.3|\n\s*【|\Z)"),
        "differential": ext_line(r"3\.3 反向鑑別搜索協議[^\n]*?[：:]\s*(.*?)(?=\n\s*3\.4|\n\s*【|\Z)"),
        "modules": ext_line(r"3\.4 執行模組與策略確立[^\n]*?[：:]\s*(.*?)(?=\n\s*【|\Z)"),
        "sai": ext_line(r"SAI \(主導權感知[^\n]*?[:：]\s*([^\n]*)"),
        "mf": ext_line(r"MF \(面具疲勞度[^\n]*?[:：]\s*([^\n]*)"),
        "bd": ext_line(r"B-D \(邊界防禦不適感[^\n]*?[:：]\s*([^\n]*)"),
        "true_reflex": ext_line(r"真實反射[：:]\s*([^\n]*)"),
        "inner_strategy": ext_line(r"內在策略[：:]\s*([^\n]*)"),
        "disguise": ext_line(r"專業偽裝[：:]\s*([^\n]*)"),
        "external_strategy": ext_line(r"外顯策略[：:]\s*([^\n]*)"),
        "fusion": ext_line(r"統合調和[：:]\s*([^\n]*)"),
        "goal_stock": ext_line(r"紀錄目標庫存[：:]\s*([^\n]*)"),
        "next_strategy": ext_line(r"制定下輪目標\s*/\s*策略[：:]\s*([^\n]*)")
    }

def process_doctor_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    """驅動核心醫療博弈運算，與大模型對話並切分臨床推演與外部演繹"""
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
    
    output_text = re.sub(r"【?Step 8[:：].*?】?\n?", "", output_text, flags=re.IGNORECASE).strip()

    # 安全機制：當 LLM 出現隨機不吐出 Step 8 標籤的極端狀況時，填補預設動作，避免產生 InvalidArgument 崩潰
    if not output_text:
        output_text = "*(醫師暫默，低頭檢視病歷，持續觀察病患反應)*"

    return {
        "internal": clinical_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
