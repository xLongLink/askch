from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Report application availability without contacting the provider."""
    return {"status": "ok"}
