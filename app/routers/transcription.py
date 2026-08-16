import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.rate_limit import TRANSCRIBE_RATE_LIMIT, limiter
from app.schemas.transcription import TranscriptionResponse
from app.services import stt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["transcription"])

# ffmpeg로 디코딩 가능한 흔한 오디오/영상 확장자만 받는다.
# (엉뚱한 파일이 Whisper까지 내려가 500이 나는 걸 400에서 미리 막는다)
ALLOWED_SUFFIXES: frozenset[str] = frozenset(
    {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".aac", ".mpga", ".mpeg"}
)

# 한 번에 읽어 들이는 청크 크기(1MB). 파일 전체를 읽기 전에 크기 초과를 감지하려고 나눠 읽는다.
_CHUNK_SIZE = 1024 * 1024


@router.post("/transcribe", response_model=TranscriptionResponse)
# IP당 호출 제한. 초과하면 slowapi가 RateLimitExceeded를 던지고 main.py에 등록한 핸들러가 429로 변환한다.
# (slowapi 데코레이터는 요청자 IP를 알아내야 하므로 핸들러에 Request 파라미터가 반드시 필요하다)
@limiter.limit(TRANSCRIBE_RATE_LIMIT)
async def transcribe_audio(
    request: Request, file: UploadFile = File(...)
) -> TranscriptionResponse:
    """업로드된 회의 음성 파일을 텍스트로 변환한다."""
    # 1) 확장자 검증 — 오디오가 아니면 400 (Nest의 ParseFilePipe/FileTypeValidator 역할)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 파일 형식이다: '{suffix or file.filename}'. "
            f"허용 확장자: {', '.join(sorted(ALLOWED_SUFFIXES))}",
        )

    # 2) 크기 상한 검사 — 청크로 읽으면서 상한을 넘는 순간 즉시 중단한다.
    #    (Content-Length 헤더는 위조될 수 있으므로 실제로 읽은 바이트로 판단한다)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = bytearray()
    while chunk := await file.read(_CHUNK_SIZE):
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"파일이 너무 크다. 최대 {settings.max_upload_size_mb}MB까지 허용된다.",
            )

    # 3) 빈 파일이면 400
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="업로드된 파일이 비어 있다.",
        )

    # 4) 변환은 서비스에 위임한다(라우터는 요청/응답만 담당).
    #    Whisper 변환은 CPU/GPU를 오래 점유하는 동기 작업이라 스레드풀에서 돌린다.
    #    안 그러면 변환 중 이벤트 루프가 막혀 다른 요청까지 멈춘다(Node에서 동기 작업으로
    #    이벤트 루프를 블로킹하는 것과 같은 문제).
    try:
        text = await run_in_threadpool(stt.transcribe_bytes, bytes(content), suffix)
    except Exception:
        # 상세 원인은 서버 콘솔에만 남기고, 클라이언트에는 일반적인 메시지만 준다.
        logger.exception("STT 변환 실패 (filename=%s)", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="음성 변환 중 오류가 발생했다.",
        ) from None

    return TranscriptionResponse(text=text)
