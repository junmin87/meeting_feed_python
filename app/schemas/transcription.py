from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """STT 변환 결과 응답. NestJS 백엔드가 이 텍스트를 받아 채점한다."""

    text: str = Field(..., description="음성에서 변환된 텍스트")
