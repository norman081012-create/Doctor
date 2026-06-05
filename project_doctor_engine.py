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
    """精準提取臨床博弈引擎內部推演數據，轉譯為儀表板變數"""
    if not clinical_text: return {}
    plain = clinical_text.replace('**', '').replace('* ', '')

    def ext_line(pattern):
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    return {
        "location": ext_line(r"醫病空間定位[：:]\s*([^\n]*)"),
        "trend": ext_line(r"變化趨向[：:]\s*([^\n]*)"),
        "cc_extract": ext_line(r"3\.1 主訴與風險萃取.*?[：:]\s*(.*?)(?=\n.*?(?:3\.2|【Step 4】|\Z))"),
        "doubt_tagging": ext_line(r"3\.2 全局懷疑度標籤化.*?[：:]\s*(.*?)(?=\n.*?(?:3\.3|\Z))"),
        "differential": ext_line(r"3\.3 反向鑑別搜索協議.*?[：:]\s*(.*?)(?=\n.*?(?:3\.4|\Z))"),
        "modules": ext_line(r"3\.4 執行模組與策略確立.*?[：:]\s*(.*?)(?=\n.*?(?:【Step 4】|\[Step 4\]|\Z))"),
        "sai": ext_line(r"SAI \(主導權感知.*?[:：]\s*([^\n]*)"),
        "mf": ext_line(r"MF \(面具疲勞度.*?[:：]\s*([^\n]*)"),
        "bd": ext_line(r"B-D \(邊界防禦不適感.*?[:：]\s*([^\n]*)"),
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
    
    # 清理殘留的 Markdown 程式碼區塊標記
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE)
    
    clinical_text = ""
    output_text = clean_text

    # 尋找 <doctor_output> 作為外顯分水嶺
    out_match = re.search(r"<doctor_output>", clean_text, flags=re.IGNORECASE)
    
    if out_match:
        clinical_text = clean_text[:out_match.start()]
        output_text = clean_text[out_match.end():]
    else:
        # 防呆防漏標籤處理
        in_close_match = re.search(r"</clinical_engine>", clean_text, flags=re.IGNORECASE)
        if in_close_match:
            clinical_text = clean_text[:in_close_match.end()]
            output_text = clean_text[in_close_match.end():]

    # 清除前後殘留標籤
    output_text = re.sub(r"</?doctor_output>", "", output_text, flags=re.IGNORECASE).strip()
    clinical_text = re.sub(r"</?clinical_engine>", "", clinical_text, flags=re.IGNORECASE).strip()
    
    # 移除可能重複輸出的 Step 8 標題文字，只保留純結構化內文
    output_text = re.sub(r"【?Step 8[:：].*?】?\n?", "", output_text, flags=re.IGNORECASE).strip()

    return {
        "internal": clinical_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(clinical_text)
    }
