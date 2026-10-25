import anyio
import httpx2
from uuid import UUID
from fastapi import Request, APIRouter, HTTPException
from pydantic import BaseModel, ValidationError
from src.settings import settings

router = APIRouter()
MAX_AUDIO_BYTES = 10 * 1024 * 1024
AUDIO_FORMATS = {"audio/webm": "webm", "audio/mp4": "mp4", "audio/ogg": "ogg", "audio/wav": "wav"}


class TranscriptionJob(BaseModel):
    """Validate the provider's transcription job identifier."""

    batch_id: UUID


@router.post("/dictation", response_model=str)
async def dictate(request: Request) -> str:
    """Transcribe a bounded recording without storing its audio locally."""
    # Bound the body while reading, including requests without Content-Length.
    content_type = request.headers.get("content-type", "").split(";")[0].lower()
    if content_type not in AUDIO_FORMATS:
        raise HTTPException(status_code=415, detail="Unsupported recording format.")
    audio = bytearray()
    async for chunk in request.stream():
        if len(audio) + len(chunk) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Recording must be smaller than 10 MB.")
        audio.extend(chunk)
    if not audio:
        raise HTTPException(status_code=400, detail="The recording is empty.")

    # Use the documented asynchronous Whisper API and a fixed result URL.
    client = request.app.state.client
    base_url = f"https://api.infomaniak.com/1/ai/{settings.INFOMANIAK_PRODUCT_ID}"
    try:
        with anyio.fail_after(90):
            response = await client.post(
                f"{base_url}/openai/audio/transcriptions",
                data={"model": "whisper", "response_format": "text"},
                files={"file": (f"dictation.{AUDIO_FORMATS[content_type]}", bytes(audio), content_type)},
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and payload.get("result") == "success":
                payload = payload.get("data")
            job = TranscriptionJob.model_validate(payload)
            while True:
                if await request.is_disconnected():
                    raise HTTPException(status_code=499, detail="Dictation cancelled.")
                response = await client.get(f"{base_url}/results/{job.batch_id}")
                response.raise_for_status()
                result = response.json()
                if isinstance(result, dict) and result.get("result") == "success":
                    result = result.get("data")
                if not isinstance(result, dict):
                    raise HTTPException(status_code=502, detail="Invalid transcription response.")
                if result.get("status") == "success":
                    response = await client.get(f"{base_url}/results/{job.batch_id}/download")
                    response.raise_for_status()
                    text = response.text.strip()
                    if len(text) > 100_000:
                        raise HTTPException(status_code=502, detail="The transcript is too long.")
                    return text
                if result.get("status") not in {"pending", "processing"}:
                    raise HTTPException(status_code=502, detail="Unable to transcribe this recording.")
                await anyio.sleep(1)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Transcription timed out. Try a shorter recording.") from None
    except (httpx2.HTTPError, ValidationError, ValueError):
        raise HTTPException(status_code=502, detail="Unable to transcribe this recording. Please try again.") from None
