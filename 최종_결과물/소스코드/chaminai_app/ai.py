import os
import time

"""Gemini API service."""
from .config import *

def ask_gemini(prompt: str) -> str:
    """제미나이 호출. 키가 없거나 오류가 나도 앱이 멈추지 않고 안내 문구를 돌려준다.
    503(서버 과부하)/429(요청 한도) 처럼 일시적인 오류는 잠깐 쉬었다가 자동 재시도한다."""
    # 1) .env 파일에서 API 키를 읽어온다. 키가 아예 없으면 AI 호출을 시도하지 않고 바로 안내 문구 반환
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return "AI 키가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY 를 넣어주세요."
    try:
        from google import genai  # 필요할 때만 불러온다 (패키지가 없어도 앱 전체가 죽지 않게)
    except ImportError:
        return "google-genai 패키지가 없습니다. `pip install google-genai` 후 다시 실행하세요."

    client = genai.Client(api_key=api_key)
    # .env 의 모델이 종료됐거나 없으면(404) 기본 최신 모델로 자동 재시도
    # → GEMINI_MODEL을 먼저 시도하고, 안 되면 FALLBACK_MODELS 순서대로 하나씩 더 시도
    models = [GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != GEMINI_MODEL]
    last_error = None
    for model in models:  # 모델을 하나씩 바꿔가며 시도
        error = None
        for delay in (0,) + RETRY_DELAYS:  # 같은 모델로 최대 4번(즉시+3번) 재시도
            if delay:
                time.sleep(delay)  # 재시도 전에 잠깐 대기 (서버 부담을 줄이기 위해)
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                return resp.text or "(AI가 빈 답변을 돌려줬습니다. 다시 시도해 주세요.)"
            except Exception as e:  # 모델명 오류, 무료 한도 초과, 네트워크 오류, 일시적 과부하 등
                error = e
                if any(marker in str(e) for marker in RETRYABLE_MARKERS):
                    continue  # 일시적 오류(과부하/한도) → 같은 모델로 잠깐 쉬었다가 재시도
                break  # 일시적 오류가 아니면 재시도해도 소용없음

        last_error = error
        is_bad_model = "404" in str(error) or "NOT_FOUND" in str(error)
        is_transient = any(marker in str(error) for marker in RETRYABLE_MARKERS)
        if not (is_bad_model or is_transient):
            break  # 모델 문제도 일시적 과부하도 아니면 다른 모델로 바꿔도 소용없다

    # 2) 여기까지 왔다는 건 모든 모델 시도가 다 실패했다는 뜻 → 사용자에게 보여줄 오류 문구 결정
    if last_error is not None and any(marker in str(last_error) for marker in RETRYABLE_MARKERS):
        return "지금 AI 서버가 많이 붐빕니다 (일시적 과부하). 잠시 후 다시 시도해 주세요."
    return f"[AI 답변 오류] {last_error}"
