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
    # POST /transcribe 의 IP당 호출 제한(slowapi 문법: "<횟수>/<기간>").
    # 정상 트래픽(게이트웨이 경유)은 막지 않고, 초당 수십 번짜리 폭주만 차단하는 수준으로 넉넉히 잡는다.
    transcribe_rate_limit: str = "20/minute"
    # 이 서비스 앞단에 있는 '신뢰할 수 있는 프록시'의 개수(게이트웨이 등 홉 수).
    # X-Forwarded-For에서 오른쪽으로부터 이 번째 값을 실제 클라이언트 IP로 본다.
    # 0이면 XFF를 무시하고 소켓 주소만 쓴다(프록시 뒤가 아닌 로컬 개발 등).
    # 실제 배포 구성과 반드시 일치시켜야 한다 — 값이 크면 위조 구간을 신뢰하게 되고,
    # 값이 작으면 프록시 IP로 집계돼 정상 트래픽이 한 키에 몰린다.
    trusted_proxy_count: int = 1


# 앱 전역에서 공유하는 설정 인스턴스
settings = Settings()
