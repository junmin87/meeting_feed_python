from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import transcription
from app.services import stt


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 Whisper 모델을 1회만 로딩한다(요청마다 로딩하지 않는다)."""
    stt.load_model()
    yield


app = FastAPI(title="회의록 코치 STT 서비스", lifespan=lifespan)

# 기능별 라우터 등록
app.include_router(transcription.router)


@app.get("/")
async def health_check() -> dict[str, str]:
    """상태 확인용 엔드포인트."""
    return {"status": "ok"}
