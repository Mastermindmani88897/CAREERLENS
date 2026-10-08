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
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.enums import EmploymentType, OpportunityType, WorkMode
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.user import User
from app.schemas.opportunity import (
    OpportunityDetailResponse,
    OpportunityIngestResult,
    OpportunityListResponse,
    OpportunityResponse,
    OpportunitySortBy,
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
    summary="List opportunities with filtering, keyword search, sorting, and pagination",
)
async def list_opportunities(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    opportunity_type: OpportunityType | None = Query(
        None, description="Filter by opportunity type (job, internship, hackathon)"
    ),
    work_mode: WorkMode | None = Query(None, description="Filter by work mode"),
    employment_type: EmploymentType | None = Query(None, description="Filter by employment type"),
    location: str | None = Query(
        None, max_length=100, description="Filter by city, state, or country substring"
    ),
    min_experience_years: int | None = Query(
        None, ge=0, description="Lower bound for candidate experience filter"
    ),
    max_experience_years: int | None = Query(
        None, ge=0, description="Upper bound for candidate experience filter"
    ),
    keyword: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Search substring across title, company, description, location, or required/preferred skill names",
    ),
    sort_by: OpportunitySortBy = Query(
        OpportunitySortBy.NEWEST, description="Sorting criteria"
    ),
) -> OpportunityListResponse:
    """
    Public opportunity discovery endpoint.
    Strictly discovers active opportunities (`is_active == True`).
    Supports keyword matching across core fields and relational skill names,
    mathematical experience interval overlap, category filters, and safe sorting.
    """
    # 1. Base filter: Public discovery is strictly limited to active opportunities
    base_filter = [Opportunity.is_active.is_(True)]

    # 2. Opportunity type filter
    if opportunity_type is not None:
        base_filter.append(Opportunity.opportunity_type == opportunity_type)

    # 3. Work mode filter
    if work_mode is not None:
        base_filter.append(Opportunity.work_mode == work_mode)

    # 4. Employment type filter
    if employment_type is not None:
        base_filter.append(Opportunity.employment_type == employment_type)

    # 5. Location filter (matches city, state, or country substring case-insensitively)
    if location and location.strip():
        loc_term = f"%{location.strip()}%"
        base_filter.append(
            or_(
                Opportunity.location_city.ilike(loc_term),
                Opportunity.location_state.ilike(loc_term),
                Opportunity.location_country.ilike(loc_term),
            )
        )

    # 6. Experience range overlap semantics:
    # Opportunity requirement interval: [Opportunity.min_experience_years, Opportunity.max_experience_years]
    # Filter interval: [min_experience_years, max_experience_years]
    # Overlap occurs when:
    # (Opportunity.max_experience_years is NULL or Opportunity.max_experience_years >= filter_min)
    # AND
    # (Opportunity.min_experience_years is NULL or Opportunity.min_experience_years <= filter_max)
    if min_experience_years is not None:
        base_filter.append(
            or_(
                Opportunity.max_experience_years.is_(None),
                Opportunity.max_experience_years >= min_experience_years,
            )
        )
    if max_experience_years is not None:
        base_filter.append(
            or_(
                Opportunity.min_experience_years.is_(None),
                Opportunity.min_experience_years <= max_experience_years,
            )
        )

    # 7. Keyword discovery: matches title, company, description, location, or relational skill names
    if keyword and keyword.strip():
        kw_term = f"%{keyword.strip()}%"
        skill_subquery = (
            select(OpportunitySkill.id)
            .where(
                OpportunitySkill.opportunity_id == Opportunity.id,
                OpportunitySkill.skill_name.ilike(kw_term),
            )
            .exists()
        )
        base_filter.append(
            or_(
                Opportunity.title.ilike(kw_term),
                Opportunity.company.ilike(kw_term),
                Opportunity.description.ilike(kw_term),
                Opportunity.location_city.ilike(kw_term),
                skill_subquery,
            )
        )

    # 8. Total count query
    count_stmt = select(func.count(Opportunity.id)).where(*base_filter)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # 9. Sorting translation
    order_clause = Opportunity.created_at.desc()
    if sort_by == OpportunitySortBy.OLDEST:
        order_clause = Opportunity.created_at.asc()
    elif sort_by == OpportunitySortBy.DEADLINE_SOONEST:
        order_clause = Opportunity.application_deadline.asc().nulls_last()
    elif sort_by == OpportunitySortBy.TITLE_ASC:
        order_clause = Opportunity.title.asc()

    # 10. Paginated items query
    offset = (page - 1) * page_size
    items_stmt = (
        select(Opportunity)
        .where(*base_filter)
        .order_by(order_clause)
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
