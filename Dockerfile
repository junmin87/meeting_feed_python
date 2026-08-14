# 회의록 코치 STT 서비스 - 배포용 이미지
# 베이스: Python 3.12 slim (용량을 줄이기 위해 slim 계열 사용)
FROM python:3.12-slim

# 파이썬 로그를 버퍼링 없이 바로 출력한다(도커 로그에서 실시간 확인용)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 배포 환경(GCP VM)에는 GPU가 없으므로 device 기본값을 cpu로 둔다.
# config.py는 pydantic-settings를 쓰므로 .env가 없어도 이 컨테이너 환경변수를 그대로 읽는다.
# 실행 시 `-e WHISPER_DEVICE=...`로 덮어쓸 수 있다.
ENV WHISPER_DEVICE=cpu

# ffmpeg: Whisper가 오디오 디코딩에 사용한다(필수).
# 설치 후 apt 캐시를 지워 이미지 용량을 줄인다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# PyTorch는 CPU 전용 빌드를 PyTorch 공식 CPU 인덱스에서 먼저 설치한다.
# (기본 PyPI의 torch는 CUDA 의존성이 포함돼 이미지가 수 GB로 커진다)
# requirements.txt와 같은 버전을 지정해 둘이 어긋나지 않게 한다.
RUN pip install --no-cache-dir torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu

# 나머지 파이썬 패키지 설치. torch는 위에서 이미 설치돼 있어 그대로 재사용된다.
# 소스 코드보다 먼저 복사해야 코드만 바뀔 때 이 레이어 캐시가 유지된다.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app ./app

# 컨테이너가 사용하는 포트(문서화 목적)
EXPOSE 8000

# 상태 확인: main.py의 GET / 엔드포인트를 호출한다.
# Whisper 모델 로딩(최초 실행 시 가중치 다운로드 포함)에 시간이 걸리므로 start-period를 넉넉히 둔다.
HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)"

# 컨테이너 외부에서 접속 가능하도록 0.0.0.0:8000으로 서비스한다(--reload는 개발 전용이라 쓰지 않는다)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
