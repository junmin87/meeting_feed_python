import os
import tempfile

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


def transcribe_bytes(content: bytes, suffix: str) -> str:
    """업로드된 오디오 바이트를 임시 파일에 쓴 뒤 변환하고, 끝나면 임시 파일을 정리한다.

    Whisper(정확히는 ffmpeg)는 메모리 버퍼가 아니라 '파일 경로'를 입력으로 받기 때문에
    임시 파일이 필요하다. 성공·실패 상관없이 파일이 남지 않도록 try/finally로 지운다.
    """
    # delete=False로 만들어 파일을 닫은 뒤에도 경로로 접근할 수 있게 한다.
    # (열린 핸들을 Whisper에 넘기지 않고 경로만 넘기기 위함)
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(content)
        tmp.close()  # ffmpeg가 읽기 전에 버퍼를 디스크로 flush 한다
        return transcribe(tmp.name)
    finally:
        tmp.close()  # 이미 닫혀 있으면 무시된다(예외로 close 전에 빠져나온 경우 대비)
        os.unlink(tmp.name)  # 변환 성공/실패와 무관하게 임시 파일 삭제
