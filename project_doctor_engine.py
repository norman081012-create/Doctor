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
        "consultation_complete": extract_tag_content("consultation_complete", clinical_text).strip().lower() == "true",
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

def run_diagnosis_guard(api_key, selected_model, chat_text):
    """
    守門員 Agent：獨立第二次呼叫，審查醫師回覆是否對病患下診斷。
    回傳 True = 偵測到診斷洩漏 (LEAK)。
    Prompt 內建於此函式，不依賴 config，避免跨檔案版本不同步。
    設計為 fail-open：守門員本身故障時不阻斷主流程。
    """
    guard_prompt = f"""你是「診斷洩漏守門員」，任務是審查一組醫師要問病患的問題。

判定標準：
* LEAK = 醫師以「結論性語氣」向病患宣告診斷，例如「你得的是X」「這就是X」「診斷是X」「你罹患了X」。
* SAFE = 未下診斷。注意：疾病名稱作為「排查脈絡」或「詢問症狀的背景」不算洩漏（如「我想確認心臟方面的問題」「比較不像是腸胃的狀況」皆為 SAFE）。以機率性措辭表達傾向（「比較不像」「可能性較低」）也是 SAFE。

【只輸出一個詞】：LEAK 或 SAFE。禁止輸出其他任何文字。

待審查的內容：
---
{chat_text}
---"""
    try:
        genai.configure(api_key=api_key)
        model_inst = genai.GenerativeModel(model_name=selected_model)
        response = model_inst.generate_content(guard_prompt)
        verdict = response.text.strip().upper()
        return "LEAK" in verdict
    except Exception:
        return False

def parse_patient_questions(clinical_text):
    """從 <patient_questions> 解析結構化問題清單。"""
    if not clinical_text:
        return []
    block = extract_tag_content("patient_questions", clinical_text)
    if not block:
        return []
    qs = []
    for m in re.finditer(r'<q\s+type\s*=\s*["\']?(yn|text)["\']?\s*>(.*?)</q>', block, flags=re.IGNORECASE | re.DOTALL):
        qtype = m.group(1).lower()
        qtext = re.sub(r"\s+", " ", m.group(2)).strip()
        if not qtext:
            continue
        # 【強制拆題】模型若把兩個問句塞進同一個 <q>，在此硬性拆開。
        for part in split_compound_question(qtext):
            qs.append({"type": qtype, "text": part})
    return qs


def split_compound_question(qtext):
    """一個 <q> 內若含多個問句（多個問號），強制拆成多題。"""
    parts = re.findall(r"[^？?]*[？?]", qtext)
    tail = re.sub(r"^.*[？?]", "", qtext, flags=re.DOTALL).strip()
    out = [p.strip() for p in parts if p.strip()]
    if tail:
        out.append(tail)
    return out if len(out) > 1 else [qtext]


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
        "raw_xml": full_xml_string,
        "questions": parse_patient_questions(engine_xml)
    }
