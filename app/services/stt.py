import whisper
from whisper.model import Whisper

from app.config import settings

# 로딩된 Whisper 모델을 모듈 전역에 1개만 보관한다.
# 모델이 무거우므로 서버 시작 시(lifespan) load_model()로 딱 1회만 채운다.
_model: Whisper | None = None


def load_model() -> None:
    """서버 시작 시 1회 호출해 Whisper 모델을 메모리에 올린다. 이미 로딩됐으면 아무것도 하지 않는다."""
    global _model
    if _model is not None:
        return
    _model = whisper.load_model(settings.whisper_model_size, device=settings.whisper_device)


def get_model() -> Whisper:
    """로딩된 모델을 반환한다. 아직 로딩 전이면 에러를 낸다(요청 처리 중 로딩을 막기 위함)."""
    if _model is None:
        raise RuntimeError(
            "Whisper 모델이 로딩되지 않았다. 서버 시작 시 load_model()이 호출되어야 한다."
        )
    return _model


def transcribe(audio_path: str) -> str:
    """오디오 파일 경로를 받아 변환된 텍스트를 반환한다."""
    result = get_model().transcribe(audio_path)
    return str(result["text"]).strip()
