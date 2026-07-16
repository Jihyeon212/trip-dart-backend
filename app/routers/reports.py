from fastapi import APIRouter

from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse
from app.services.report_service import report_service


router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
)


@router.post(
    "/generate",
    response_model=ReportGenerateResponse,
    response_model_by_alias=True,
)
def generate_report(request: ReportGenerateRequest) -> ReportGenerateResponse:
    return report_service.generate_report(request)
