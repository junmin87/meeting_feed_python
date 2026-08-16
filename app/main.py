from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.rate_limit import limiter
from app.routers import transcription
from app.services import stt


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 Whisper 모델을 1회만 로딩한다(요청마다 로딩하지 않는다)."""
    stt.load_model()
    yield


app = FastAPI(title="회의록 코치 STT 서비스", lifespan=lifespan)

# rate limit 등록 (slowapi 표준 방식)
# - Limiter를 app.state.limiter에 넣어야 @limiter.limit 데코레이터가 동작한다.
# - 제한 초과 시 발생하는 RateLimitExceeded를 429 응답으로 바꿔 주는 기본 핸들러를 연결한다.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 기능별 라우터 등록
app.include_router(transcription.router)


@app.get("/")
async def health_check() -> dict[str, str]:
    """상태 확인용 엔드포인트."""
    return {"status": "ok"}
