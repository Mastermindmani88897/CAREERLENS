"""
Opportunity API endpoints for Phase 14 Opportunity Ingestion and Normalization.
Provides batch ingestion (CSV or JSON), paginated listing with filtering, and detail retrieval.
"""

import math
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.enums import EmploymentType, OpportunityType, WorkMode
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.opportunity import (
    OpportunityDetailResponse,
    OpportunityIngestResult,
    OpportunityListResponse,
    OpportunityResponse,
    RawOpportunityRow,
)
from app.services.opportunity_ingest_service import (
    ingest_csv_content,
    ingest_raw_records,
)

logger = get_logger("opportunities_api")

router = APIRouter()


@router.post(
    "/ingest",
    response_model=OpportunityIngestResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest batch opportunities via CSV file or JSON payload",
)
async def ingest_opportunities(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityIngestResult:
    """
    Ingest opportunity listings from an uploaded CSV file or a JSON list of raw opportunity records.
    Normalizes text, URLs, dates, salaries, enums, and skills.
    Deduplicates against existing records deterministically.
    Requires active user authentication.
    """
    content_type = request.headers.get("content-type", "").lower()

    # 1. Handle multipart CSV upload
    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if file_obj is None or not hasattr(file_obj, "read"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Form field 'file' is required.",
            )
        filename = getattr(file_obj, "filename", "") or ""
        if filename and not filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must be a .csv format file.",
            )
        try:
            content = await file_obj.read()
            result = await ingest_csv_content(db, content)
            logger.info(
                "User %s ingested CSV '%s': created=%d, skipped=%d, errors=%d",
                current_user.id,
                filename,
                result.created,
                result.skipped_duplicates,
                len(result.errors),
            )
            return result
        except Exception as exc:
            logger.error("CSV ingestion failed unexpectedly: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while processing the CSV file.",
            ) from None

    # 2. Handle JSON batch
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload.",
            ) from None

        raw_list = (
            body
            if isinstance(body, list)
            else body.get("records", [])
            if isinstance(body, dict)
            else []
        )
        if not raw_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "JSON payload must be a non-empty list of records or contain a 'records' field."
                ),
            )
        try:
            records = [RawOpportunityRow.model_validate(r) for r in raw_list]
        except Exception as val_exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Record schema validation error: {val_exc}",
            ) from None

        result = await ingest_raw_records(db, records)
        logger.info(
            "User %s ingested JSON batch of %d records: created=%d, skipped=%d, errors=%d",
            current_user.id,
            len(records),
            result.created,
            result.skipped_duplicates,
            len(result.errors),
        )
        return result

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either a CSV file or a JSON list of opportunity records must be provided.",
    )


@router.get(
    "/",
    response_model=OpportunityListResponse,
    summary="List opportunities with filtering and pagination",
)
async def list_opportunities(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    opportunity_type: OpportunityType | None = Query(
        None, description="Filter by opportunity type"
    ),
    work_mode: WorkMode | None = Query(None, description="Filter by work mode"),
    employment_type: EmploymentType | None = Query(None, description="Filter by employment type"),
    is_active: bool = Query(True, description="Filter active opportunities"),
) -> OpportunityListResponse:
    """
    Retrieve paginated opportunities with optional filters for type, work mode, and employment type.
    """
    base_filter = [Opportunity.is_active == is_active]
    if opportunity_type is not None:
        base_filter.append(Opportunity.opportunity_type == opportunity_type)
    if work_mode is not None:
        base_filter.append(Opportunity.work_mode == work_mode)
    if employment_type is not None:
        base_filter.append(Opportunity.employment_type == employment_type)

    # 1. Total count query
    count_stmt = select(func.count(Opportunity.id)).where(*base_filter)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # 2. Paginated items query
    offset = (page - 1) * page_size
    items_stmt = (
        select(Opportunity)
        .where(*base_filter)
        .order_by(Opportunity.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items_res = await db.execute(items_stmt)
    items = items_res.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return OpportunityListResponse(
        items=[OpportunityResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{id}",
    response_model=OpportunityDetailResponse,
    summary="Retrieve single opportunity details with associated skills",
)
async def get_opportunity(
    id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityDetailResponse:
    """
    Retrieve single opportunity details including relational skills by UUID.
    """
    stmt = select(Opportunity).options(selectinload(Opportunity.skills)).where(Opportunity.id == id)
    res = await db.execute(stmt)
    opp = res.scalar_one_or_none()

    if opp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found.",
        )

    return OpportunityDetailResponse.model_validate(opp)
