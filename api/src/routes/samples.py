from fastapi import APIRouter

router = APIRouter()


@router.get("/samples", response_model=list[str])
async def samples() -> list[str]:
    """Suggest questions backed by the available Swiss data tools."""
    return [
        "What is the weather forecast for Bern?",
        "What are the latest Swiss government announcements?",
        "Which languages are spoken in each Swiss canton?",
        "Find the postcodes for Lausanne.",
    ]
