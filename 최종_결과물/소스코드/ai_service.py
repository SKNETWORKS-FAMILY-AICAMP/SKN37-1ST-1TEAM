import json
import os
import time
from config import GEMINI_MODEL, FALLBACK_MODELS, RETRYABLE_MARKERS, RETRY_DELAYS, FUEL_CHOICES

def ask_gemini(prompt: str) -> str:
    """Gemini API 호출 및 재시도 로직"""
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return "AI 키가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY 를 넣어주세요."
    try:
        from google import genai
    except ImportError:
        return "google-genai 패키지가 없습니다. `pip install google-genai` 후 다시 실행하세요."

    client = genai.Client(api_key=api_key)
    models = [GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != GEMINI_MODEL]
    last_error = None
    for model in models:
        error = None
        for delay in (0,) + RETRY_DELAYS:
            if delay:
                time.sleep(delay)
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                return resp.text or "(AI가 빈 답변을 돌려줬습니다. 다시 시도해 주세요.)"
            except Exception as e:
                error = e
                if any(marker in str(e) for marker in RETRYABLE_MARKERS):
                    continue
                break

        last_error = error
        is_bad_model = "404" in str(error) or "NOT_FOUND" in str(error)
        is_transient = any(marker in str(error) for marker in RETRYABLE_MARKERS)
        if not (is_bad_model or is_transient):
            break

    if last_error is not None and any(marker in str(last_error) for marker in RETRYABLE_MARKERS):
        return "지금 AI 서버가 많이 붐빕니다 (일시적 과부하). 잠시 후 다시 시도해 주세요."
    return f"[AI 답변 오류] {last_error}"

def classify_chat_intent(user_msg: str, history_text: str, regions: list) -> dict:
    """사용자 질문 의도 파악 (recommend / faq / general)"""
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return {"intent": "general"}
    try:
        from google import genai
    except ImportError:
        return {"intent": "general"}

    prompt = (
        "사용자 메시지를 분석해서 의도를 아래 중 하나로 분류하고, JSON 하나만 출력해라.\n\n"
        "- \"recommend\": 차량 구매/추천을 원하는 경우\n"
        "- \"faq\": 브랜드 이용 FAQ 관련 문의\n"
        "- \"general\": 일반 대화\n\n"
        '{"intent":"recommend","annual_km":<int|null>,"region":<지역명|null>,'
        '"budget_manwon":<int|null>,"fuel_pref":[<언급된 연료만>]}\n\n'
        f"사용 가능한 지역명: {regions}\n사용 가능한 연료: {FUEL_CHOICES}\n\n"
        f"최근 대화:\n{history_text}\n\n사용자 메시지: {user_msg}"
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        return {"intent": "general"}