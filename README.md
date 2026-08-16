# 회의록 코치 — STT 서비스 (Python)

회의 음성 파일을 받아 **텍스트로 변환**하는 마이크로서비스입니다.
회의록 코치 시스템에서 음성 입력을 담당하며, 변환된 텍스트는 NestJS 게이트웨이가 받아 채점합니다.

## 역할

전체 시스템에서 이 서비스의 위치입니다.

```
Frontend ──▶ NestJS Gateway ──▶ [이 서비스] Python STT
                   │                  (음성 → 텍스트)
                   ▼
              Claude API (채점)
```

- 프론트엔드에 직접 노출되지 않고, **NestJS 게이트웨이 뒤에서만 호출**됩니다.
- 음성을 텍스트로만 바꾸고, 채점·저장 등은 하지 않습니다 (단일 책임).
- 로컬 Whisper로 변환하므로 외부 STT API 비용이 없습니다.

## 무엇을 하나요

`POST /transcribe`로 오디오 파일을 받아, OpenAI Whisper로 변환한 텍스트를 반환합니다.

```
음성 파일 → 확장자·크기 검증 → Whisper 변환 → { "text": "..." }
```

## 구조 (레이어별 책임 분리)

```
app/
├── main.py                  # FastAPI 진입점 + 모델 로딩(lifespan)
├── config.py                # 설정(.env에서 로드)
├── routers/
│   └── transcription.py     # POST /transcribe — 요청/응답·입력 검증
├── services/
│   └── stt.py               # Whisper 호출 격리 (변환 로직)
└── schemas/
    └── transcription.py     # 응답 스키마 (Pydantic)
```

router는 요청/응답과 검증만, 실제 변환은 service에 위임합니다. Whisper 호출은 `stt.py`에 격리되어, 모델 교체 시 고칠 파일이 하나로 끝납니다.

## 주요 설계 포인트

**모델 1회 로딩** — Whisper 모델은 무거우므로 서버 시작 시(lifespan) 딱 한 번 메모리에 올리고, 요청마다 재로딩하지 않습니다.

**이벤트 루프 보호** — Whisper 변환은 CPU를 오래 점유하는 동기 작업이라 `run_in_threadpool`로 실행합니다. 안 그러면 변환 중 다른 요청까지 멈춥니다.

**방어적 입력 검증**
- 확장자 화이트리스트로 오디오가 아닌 파일은 400으로 미리 차단
- 크기 상한은 Content-Length(위조 가능) 대신 **실제로 읽은 바이트**로 판단하며, 청크로 읽다가 상한 초과 시 즉시 중단
- 빈 파일은 400, 변환 실패는 상세 원인을 서버 로그에만 남기고 클라이언트엔 일반 메시지만 반환

**임시 파일 정리** — Whisper(ffmpeg)는 파일 경로를 입력으로 받으므로 업로드 바이트를 임시 파일에 쓰는데, 성공·실패와 무관하게 `try/finally`로 삭제합니다.

## 기술 선택 이유

**왜 Docker인가** — 로컬(개발자 맥북)에서만 돌아가는 서버로는 시연이 안 됩니다. Whisper는 PyTorch·ffmpeg 등 의존성이 무겁고 환경을 타기 때문에, 실행 환경째 이미지로 묶어 어디서든 동일하게 뜨도록 했습니다. "내 컴퓨터에선 되는데" 문제를 없애고, 서버엔 이미지만 받아 실행하면 됩니다.

**왜 Compute Engine(VM)인가** — NestJS 게이트웨이는 App Engine에 올렸지만, STT는 VM으로 분리했습니다. Whisper 변환은 무거운 연산이라 GPU가 있으면 빠르지만 GPU 인스턴스는 비쌉니다. 이 프로젝트는 시연·포트폴리오 목적이라 **변환이 다소 느려도 비용을 아끼는 쪽**을 택해, GPU 없이 CPU만 있는 Compute Engine VM에 배포했습니다. VM은 사양을 자유롭게 정하고 무거운 모델을 메모리에 상주시켜 쓰기에 적합합니다.

## 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/` | 상태 확인 → `{ "status": "ok" }` |
| POST | `/transcribe` | 오디오 파일(`file`) → `{ "text": "..." }` |

허용 오디오 형식: mp3, wav, m4a, mp4, webm, ogg, flac, aac, mpga, mpeg (최대 25MB)

## 환경 변수 (.env)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `WHISPER_MODEL_SIZE` | `small` | Whisper 모델 크기 (tiny/base/small/medium/large) |
| `WHISPER_DEVICE` | `mps` | 연산 장치 (Apple Silicon `mps`, 서버 `cpu`, GPU `cuda`) |
| `MAX_UPLOAD_SIZE_MB` | `25` | 업로드 오디오 크기 상한 |

## 기술 스택

- **Python / FastAPI** — 웹 프레임워크
- **OpenAI Whisper** (로컬) — 음성 인식
- **ffmpeg** — 오디오 디코딩
- **Pydantic Settings** — 설정 관리
- 배포: **Docker** on **GCP Compute Engine**

## 실행

### 로컬
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# .env에 WHISPER_DEVICE 등 설정 (Apple Silicon이면 mps)
uvicorn app.main:app --reload
```

### Docker
```bash
docker build --platform linux/amd64 -t meeting-feed-stt .
docker run -d -p 80:8000 \
  -e WHISPER_MODEL_SIZE=small \
  -e WHISPER_DEVICE=cpu \
  --name stt \
  meeting-feed-stt
```

서버 기동 시 Whisper 모델을 내려받으므로, 첫 요청 준비까지 잠깐 걸립니다.