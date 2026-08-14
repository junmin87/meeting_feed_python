# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 지침이다.

## 프로젝트 개요

'회의록 코치'의 STT(음성→텍스트) 마이크로서비스. 로컬 Whisper 모델(openai-whisper, PyTorch)로 회의 음성을 텍스트로 변환하고, 그 텍스트를 NestJS 백엔드가 받아 채점한다. FastAPI 기반. 도커로 컨테이너화해 GCP VM에 배포한다.

## 환경

- Python 3.12, 가상환경은 `venv/` (활성화: `source venv/bin/activate`)
- 로컬 개발: Apple Silicon(M4), PyTorch `mps`(Metal GPU) 사용
- 배포(GCP VM): GPU 없음 → PyTorch `cpu` 사용. `WHISPER_DEVICE` 환경변수로 전환한다.
- `ffmpeg` 필요 (Whisper가 오디오 디코딩에 사용). 로컬은 Homebrew, 도커 이미지는 apt로 설치.

## 명령어

```bash
source venv/bin/activate                 # 먼저 가상환경 활성화
uvicorn app.main:app --reload            # 개발 서버(핫 리로드), http://localhost:8000
uvicorn app.main:app --reload --port 8000
```

실행하면 `/docs`에서 FastAPI 자동 문서(Swagger UI)를 볼 수 있다.

## 아키텍처 (레이어별 책임 분리)

```
app/
├── main.py                 # FastAPI 진입점; 서버 시작 시 Whisper 모델 로딩
├── config.py               # .env에서 설정값 로딩
├── routers/                # 요청/응답 계층 (Express route / Nest controller 역할)
├── services/               # 비즈니스 로직 계층; Whisper 처리를 여기 격리
└── schemas/                # 검증·응답 스키마 (Nest DTO 역할)
```

규칙:
- **routers** — 요청/응답만 담당한다. 입력 검증, HTTP 상태 코드 매핑, 스키마 변환까지. 비즈니스 로직이나 외부 도구(Whisper 등) 호출을 직접 하지 않고 services에 위임한다.
- **services** — 비즈니스 로직과 외부 처리(Whisper 변환, 파일 I/O 등)를 담당한다. HTTP나 요청 객체에 의존하지 않는다(순수 로직으로 유지해 테스트·재사용이 쉽도록).
- **schemas** — 요청/응답 데이터의 형태와 검증 규칙만 정의한다. 로직을 넣지 않는다.
- 각 레이어는 자기 책임 범위의 일만 하고, 다른 레이어의 역할을 침범하지 않는다.
- **Whisper 모델은 서버 시작 시(FastAPI lifespan) 딱 1회만 로딩한다.** 모델이 무거워 매 요청마다 로딩하면 매우 느려진다.
- 설정값은 config(pydantic-settings)를 통해 `.env`(또는 컨테이너 환경변수)에서 읽는다. 다른 곳에서 os.environ을 직접 읽지 않는다.

## 연동

- 이 서비스는 변환된 텍스트를 출력하고, 별도 저장소의 NestJS 백엔드가 그걸 받아 채점한다.
- 시크릿·설정값은 `.env`에만 둔다(gitignore). `.env`를 커밋하지 않고, 시크릿을 하드코딩하지 않으며, 도커 이미지에도 포함하지 않는다(배포 시 환경변수로 주입).

## 컨벤션

- 모든 곳에 파이썬 타입 힌트를 쓴다. 입출력 스키마는 Pydantic으로 정의한다.
- Whisper 모델 크기·device는 config에서 가져온다(기본: 모델 'small'). 하드코딩하지 않는다.

## 하지 말아야 할 것 (DO NOT)

- 레이어의 책임 경계를 넘지 마라 (routers에 비즈니스 로직, services에 HTTP 의존성 등을 섞지 마라).
- 요청 핸들러 안에서 Whisper 모델을 로딩하지 마라.
- 지시하지 않은 라이브러리를 임의로 추가하지 마라.
- venv/, .env, 모델 캐시 파일을 커밋하지 마라.
- 지시 범위 밖의 사이드 이펙트를 만들거나 기존 동작을 바꾸지 마라.
- 버그를 만들지 마라. 불확실하면 임의로 진행하지 말고 먼저 물어봐라.

## 작업 원칙

- 기존 아키텍처와 레이어 구조를 유지한다.
- 가독성, 기존 코드 재사용성, 유지보수성을 고려해 작성한다.
- 새로 작성하는 코드에는 무엇을 왜 하는지 간단한 한글 주석을 단다. 도움이 되면 Express/NestJS의 대응 개념에 빗대어 설명한다.