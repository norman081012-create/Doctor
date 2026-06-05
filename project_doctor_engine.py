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

def extract_doctor_dashboard(internal_text):
    """精準提取專案診療師內部推演數據，轉譯為儀表板變數"""
    if not internal_text: return {}
    plain = internal_text.replace('**', '').replace('* ', '')

    def ext_line(pattern):
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    return {
        "location": ext_line(r"顧問客戶空間定位[：:]\s*([^\n]*)"),
        "trend": ext_line(r"變化趨向[：:]\s*([^\n]*)"),
        "modules": ext_line(r"常駐執行模組[：:]\s*([^\n]*)"),
        "tags": ext_line(r"結算當前標籤庫存.*?[:：]\s*(.*?)(?=\n.*?[Step 4]|\Z)"),
        "sai": ext_line(r"SAI \(主導權感知.*?[:：]\s*([^\n]*)"),
        "mf": ext_line(r"MF \(顧問面具疲勞度.*?[:：]\s*([^\n]*)"),
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
    """驅動核心運算，與大模型進行對話並進行內部與外部回覆的暴力切割"""
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    chat = model_inst.start_chat(history=history_for_api)
    
    response = chat.send_message(forced_template_text)
    full_text = response.text
    
    # 清理殘留的 Markdown 程式碼區塊標記
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE)
    
    internal_text = ""
    output_text = clean_text

    # 尋找 <doctor_output> 作為內外分水嶺
    out_match = re.search(r"<doctor_output>", clean_text, flags=re.IGNORECASE)
    
    if out_match:
        internal_text = clean_text[:out_match.start()]
        output_text = clean_text[out_match.end():]
    else:
        # 防呆防漏標籤處理
        in_close_match = re.search(r"</doctor_internal>", clean_text, flags=re.IGNORECASE)
        if in_close_match:
            internal_text = clean_text[:in_close_match.end()]
            output_text = clean_text[in_close_match.end():]

    # 清除前後殘留標籤
    output_text = re.sub(r"</?doctor_output>", "", output_text, flags=re.IGNORECASE).strip()
    internal_text = re.sub(r"</?doctor_internal>", "", internal_text, flags=re.IGNORECASE).strip()

    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_doctor_dashboard(internal_text)
    }
