from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정. 값은 .env에서 읽는다(다른 곳에서 os.environ을 직접 읽지 않는다)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env에 모르는 키가 있어도 무시한다
    )

    # Whisper 모델 크기(tiny/base/small/medium/large 등)
    whisper_model_size: str = "small"
    # PyTorch device — Apple Silicon은 'mps', 그 외 'cpu'/'cuda'
    whisper_device: str = "mps"
    # 업로드 오디오 파일 크기 상한(MB). 초과하면 413으로 거절한다.
    max_upload_size_mb: int = 25


# 앱 전역에서 공유하는 설정 인스턴스
settings = Settings()
