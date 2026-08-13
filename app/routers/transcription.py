from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.transcription import TranscriptionResponse

router = APIRouter(tags=["transcription"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)) -> TranscriptionResponse:
    """업로드된 회의 음성 파일을 텍스트로 변환한다."""
    # TODO: 다음 단계에서 구현 —
    #   1) 업로드 파일을 임시 파일로 저장
    #   2) stt.transcribe(임시 파일 경로) 호출 (모델 로딩은 서버 시작 시 이미 완료됨)
    #   3) 임시 파일 정리 후 TranscriptionResponse로 반환
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="변환 로직은 아직 구현되지 않았다.",
    )
