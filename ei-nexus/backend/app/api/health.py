from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "EI Nexus Backend",
        "version": "1.0.0"
    }