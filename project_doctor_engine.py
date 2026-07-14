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

def run_question_scanner(api_key, selected_model, chat_text):
    """
    Scanner Agent：獨立呼叫，把醫師的口語回覆掃描成結構化題目清單。
    職責單一——只做「抽出問句 + 拆解併題 + 分類 yn/text」，不做任何臨床推理。
    設計為 fail-soft：掃描失敗時回傳空清單，前端退回自由文字作答。
    """
    if not chat_text or not chat_text.strip():
        return []

    scanner_prompt = f"""你是「問句掃描器」。任務：把下面這段醫師的口語問診回覆，拆解成一份結構化題目清單。

【規則】
1. 只抽出【問句】。過渡語、安撫語、說明語一律丟棄。
2. 【一題一問】：一個問句若問到兩件以上可獨立回答的事，必須拆成多題。
   例：「有沒有發燒，或身上出現紅疹？」→ 拆成「這幾天有沒有發燒？」和「身上有沒有出現紅疹？」
   例：「能自己站穩走路嗎？會不會像喝醉酒一樣偏一邊？」→ 拆成兩題。
3. 拆題時【必須】補回原句的情境詞（時間、部位、發作當下等），讓每一題單獨看也完整。
4. 分類：
   yn   = 可用「是/否」直接回答
   text = 需要描述、無法用是否回答（如：請描述感覺、幾分、多久）
5. 保持醫師的口語用詞，【不得】改寫成醫學名詞、【不得】自行新增醫師沒問的題目。

【輸出格式】每行一題，格式固定為：
yn|問題文字
text|問題文字

只輸出這些行。禁止輸出編號、標題、解釋、Markdown、程式碼區塊。

【待掃描的醫師回覆】
---
{chat_text}
---"""

    try:
        genai.configure(api_key=api_key)
        model_inst = genai.GenerativeModel(model_name=selected_model)
        response = model_inst.generate_content(scanner_prompt)
        raw = response.text or ""
    except Exception:
        return []

    return _parse_scanner_output(raw)


def _parse_scanner_output(raw):
    """解析 scanner 的 'yn|問題' 逐行輸出，並做最後一道機械拆題保險。"""
    qs = []
    raw = re.sub(r"```[a-z]*\n|\n```|```", "", raw, flags=re.IGNORECASE)
    for line in raw.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        qtype, _, qtext = line.partition("|")
        qtype = qtype.strip().lower()
        if qtype not in ("yn", "text"):
            continue
        qtext = re.sub(r"^\s*[\d]+[\.、)]\s*", "", qtext).strip()
        if not qtext:
            continue
        # 保險：scanner 沒拆乾淨的併題，在此硬拆
        for part in split_compound_question(qtext):
            qs.append({"type": qtype, "text": part})
    return qs


def split_compound_question(qtext):
    """一個問句內若含多個問號，強制拆成多題。"""
    parts = re.findall(r"[^？?]*[？?]", qtext)
    tail = re.sub(r"^.*[？?]", "", qtext, flags=re.DOTALL).strip()
    out = [p.strip() for p in parts if p.strip()]
    if tail:
        out.append(tail)
    return out if len(out) > 1 else [qtext]


def parse_chat_response(full_text):
    """分離內部 XML 與對病患的口語回覆。題目由 run_question_scanner 另行掃描。"""
    engine_match = re.search(r"<clinical_engine>(.*?)</clinical_engine>", full_text, flags=re.IGNORECASE | re.DOTALL)
    engine_xml = engine_match.group(1).strip() if engine_match else ""

    chat_text = re.sub(r"<clinical_engine>.*?</clinical_engine>", "", full_text, flags=re.IGNORECASE | re.DOTALL)
    chat_text = re.sub(r"</?clinical_engine>", "", chat_text, flags=re.IGNORECASE)
    chat_text = re.sub(r"```[a-z]*\n|\n```|```", "", chat_text, flags=re.IGNORECASE).strip()

    full_xml_string = f"<clinical_engine>\n{engine_xml}\n</clinical_engine>" if engine_xml else ""

    return {
        "chat_text": chat_text,
        "parsed_dash": extract_doctor_dashboard(engine_xml),
        "raw_xml": full_xml_string
    }
