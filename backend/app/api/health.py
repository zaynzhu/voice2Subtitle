from fastapi import APIRouter

from app.config import settings
from app.models.schemas import HealthRead

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthRead)
def health() -> HealthRead:
    return HealthRead(
        status="ok",
        port=settings.port,
        database=str(settings.db_path),
    )
