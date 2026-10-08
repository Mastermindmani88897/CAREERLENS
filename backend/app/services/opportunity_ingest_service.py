"""
Opportunity ingestion service orchestrating CSV/raw record parsing, validation,
deterministic normalization, skill normalization, deduplication, and transactional persistence.
"""

import csv
import io
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.enums import OpportunitySource
from app.models.opportunity import Opportunity, OpportunitySkill
from app.schemas.opportunity import OpportunityIngestResult, RawOpportunityRow
from app.services.opportunity_normalizer import (
    normalize_currency,
    normalize_education_level,
    normalize_employment_type,
    normalize_numeric_int,
    normalize_opportunity_type,
    normalize_source,
    normalize_url,
    normalize_work_mode,
    parse_flexible_date,
    parse_location_string,
    sanitize_text,
)
from app.services.opportunity_skill_normalizer import normalize_opportunity_skills

logger = get_logger("opportunity_ingest")


async def check_is_duplicate(
    db: AsyncSession,
    source: OpportunitySource,
    source_id: str | None,
    company: str,
    title: str,
    job_url: str | None,
    city: str | None,
    country: str | None,
) -> bool:
    """
    Evaluate deterministic deduplication:
    1. PRIMARY: Match on (source, source_id) where source_id is provided.
    2. FALLBACK: Match on normalized (company, title, job_url) or
       (company, title, city, country).
       Ensures different companies with same title or same company with
       different URLs are not skipped.
    """
    # 1. Primary Deduplication
    if source_id and source_id.strip():
        primary_stmt = select(Opportunity.id).where(
            Opportunity.source == source,
            Opportunity.source_id == source_id.strip(),
        )
        primary_res = await db.execute(primary_stmt)
        if primary_res.scalar_one_or_none() is not None:
            return True

    # 2. Fallback Deduplication
    company_lower = company.lower().strip()
    title_lower = title.lower().strip()

    base_query = select(Opportunity.id).where(
        func.lower(Opportunity.company) == company_lower,
        func.lower(Opportunity.title) == title_lower,
        Opportunity.is_active.is_(True),
    )

    if job_url and job_url.strip():
        # Match identical company, title, and application URL
        url_query = base_query.where(func.lower(Opportunity.job_url) == job_url.lower().strip())
        res = await db.execute(url_query)
        if res.scalar_one_or_none() is not None:
            return True
    elif city or country:
        # Match identical company, title, and location
        conditions = []
        if city:
            conditions.append(func.lower(Opportunity.location_city) == city.lower().strip())
        if country:
            conditions.append(func.lower(Opportunity.location_country) == country.lower().strip())
        if conditions:
            loc_query = base_query.where(*conditions)
            res = await db.execute(loc_query)
            if res.scalar_one_or_none() is not None:
                return True

    return False


def parse_csv_to_raw_rows(csv_text: str) -> list[RawOpportunityRow]:
    """Parse CSV text into list of RawOpportunityRow models, accommodating header aliases."""
    # Handle UTF-8 with BOM if present
    cleaned_csv = csv_text.lstrip("\ufeff")
    stream = io.StringIO(cleaned_csv)
    reader = csv.DictReader(stream)

    raw_rows: list[RawOpportunityRow] = []
    if not reader.fieldnames:
        return raw_rows

    for row in reader:
        # Normalize header keys
        norm_row: dict[str, Any] = {}
        for k, v in row.items():
            if not k:
                continue
            key_clean = k.strip().lower().replace(" ", "_")
            norm_row[key_clean] = v

        # Map common header aliases
        title = norm_row.get("title") or norm_row.get("role_title") or norm_row.get("name")
        company = norm_row.get("company") or norm_row.get("organization") or norm_row.get("org")
        description = norm_row.get("description") or norm_row.get("job_description") or ""
        opp_type = norm_row.get("opportunity_type") or norm_row.get("type")
        emp_type = norm_row.get("employment_type")
        work_mode = norm_row.get("work_mode")
        edu_level = norm_row.get("required_education_level") or norm_row.get("education_level")
        loc_city = norm_row.get("location_city") or norm_row.get("city")
        loc_state = norm_row.get("location_state") or norm_row.get("state")
        loc_country = norm_row.get("location_country") or norm_row.get("country")
        loc_comp = norm_row.get("location")
        if loc_comp and not (loc_city and loc_country):
            c_city, c_state, c_country = parse_location_string(
                loc_comp, loc_city, loc_state, loc_country
            )
            loc_city, loc_state, loc_country = c_city, c_state, c_country

        url = norm_row.get("job_url") or norm_row.get("application_url") or norm_row.get("url")
        deadline = norm_row.get("application_deadline") or norm_row.get("deadline")
        posted = norm_row.get("posted_date") or norm_row.get("posted_at")
        req_skills = norm_row.get("required_skills") or norm_row.get("skills")
        pref_skills = norm_row.get("preferred_skills")

        raw_rows.append(
            RawOpportunityRow(
                title=title or "",
                company=company or "",
                description=description,
                opportunity_type=opp_type,
                employment_type=emp_type,
                work_mode=work_mode,
                required_education_level=edu_level,
                location_city=loc_city,
                location_state=loc_state,
                location_country=loc_country,
                salary_min=norm_row.get("salary_min"),
                salary_max=norm_row.get("salary_max"),
                salary_currency=norm_row.get("salary_currency") or norm_row.get("currency"),
                min_experience_years=norm_row.get("min_experience_years")
                or norm_row.get("experience_min"),
                max_experience_years=norm_row.get("max_experience_years")
                or norm_row.get("experience_max"),
                application_deadline=deadline,
                job_url=url,
                source=norm_row.get("source") or "manual",
                source_id=norm_row.get("source_id"),
                posted_date=posted,
                required_skills=req_skills,
                preferred_skills=pref_skills,
                is_active=norm_row.get("is_active", True),
            )
        )

    return raw_rows


async def ingest_raw_records(
    db: AsyncSession,
    raw_records: list[RawOpportunityRow],
) -> OpportunityIngestResult:
    """
    Validate, normalize, deduplicate, and persist raw opportunity records.
    Transaction isolation per record ensures individual failures do not abort the entire batch.
    """
    total = len(raw_records)
    created = 0
    skipped_duplicates = 0
    errors: list[dict[str, Any]] = []
    created_opp_ids: list[uuid.UUID] = []

    for idx, raw in enumerate(raw_records):
        row_num = idx + 1
        try:
            # 1. Mandatory field validation
            clean_title = sanitize_text(raw.title)
            if not clean_title:
                errors.append({"row": row_num, "error": "Title is required and cannot be empty."})
                continue

            company_val = raw.company or raw.organization
            clean_company = sanitize_text(company_val)
            if not clean_company:
                errors.append(
                    {
                        "row": row_num,
                        "error": "Company/organization is required and cannot be empty.",
                    }
                )
                continue

            clean_desc = sanitize_text(raw.description, allow_multiline=True)
            if not clean_desc:
                errors.append(
                    {"row": row_num, "error": "Description is required and cannot be empty."}
                )
                continue

            # 2. Normalization
            opp_type = normalize_opportunity_type(raw.opportunity_type)
            emp_type = normalize_employment_type(raw.employment_type, opp_type)
            work_mode = normalize_work_mode(raw.work_mode)
            edu_level = normalize_education_level(raw.required_education_level)
            source = normalize_source(raw.source)
            source_id = sanitize_text(raw.source_id) or None

            city, state, country = parse_location_string(
                None, raw.location_city, raw.location_state, raw.location_country
            )

            # Salary normalization
            sal_min = normalize_numeric_int(raw.salary_min)
            sal_max = normalize_numeric_int(raw.salary_max)
            if sal_min is not None and sal_max is not None and sal_min > sal_max:
                sal_min, sal_max = sal_max, sal_min
            currency = normalize_currency(raw.salary_currency)

            # Experience normalization
            exp_min = normalize_numeric_int(raw.min_experience_years)
            exp_max = normalize_numeric_int(raw.max_experience_years)
            if exp_min is not None and exp_max is not None and exp_min > exp_max:
                exp_min, exp_max = exp_max, exp_min

            # Date normalization
            deadline = parse_flexible_date(raw.application_deadline)
            posted_date = parse_flexible_date(raw.posted_date)

            # URL normalization
            raw_url = raw.job_url or raw.application_url
            job_url = normalize_url(raw_url)
            if raw_url and not job_url:
                # If a URL was given but failed scheme validation (e.g. javascript:), reject row
                errors.append({"row": row_num, "error": f"Invalid URL scheme: '{raw_url}'."})
                continue

            # Skills normalization
            req_skills_list, pref_skills_list, skill_tuples = normalize_opportunity_skills(
                raw.required_skills, raw.preferred_skills
            )

            # Active status
            is_active = True
            if raw.is_active is not None:
                if isinstance(raw.is_active, bool):
                    is_active = raw.is_active
                elif str(raw.is_active).strip().lower() in ("false", "0", "no"):
                    is_active = False

            # 3. Deduplication Check
            is_dup = await check_is_duplicate(
                db=db,
                source=source,
                source_id=source_id,
                company=clean_company,
                title=clean_title,
                job_url=job_url,
                city=city,
                country=country,
            )
            if is_dup:
                skipped_duplicates += 1
                continue

            # 4. Transactional Persistence via Savepoint
            async with db.begin_nested():
                opp = Opportunity(
                    id=uuid.uuid4(),
                    opportunity_type=opp_type,
                    title=clean_title,
                    company=clean_company,
                    description=clean_desc,
                    required_skills=req_skills_list,
                    preferred_skills=pref_skills_list,
                    min_experience_years=exp_min,
                    max_experience_years=exp_max,
                    required_education_level=edu_level,
                    location_city=city,
                    location_state=state,
                    location_country=country,
                    work_mode=work_mode,
                    employment_type=emp_type,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=currency,
                    application_deadline=deadline,
                    job_url=job_url,
                    source=source,
                    source_id=source_id,
                    posted_date=posted_date,
                    is_active=is_active,
                )
                db.add(opp)
                await db.flush()

                # Add OpportunitySkill entities
                for skill_name, is_req in skill_tuples:
                    opp_skill = OpportunitySkill(
                        id=uuid.uuid4(),
                        opportunity_id=opp.id,
                        skill_name=skill_name,
                        is_required=is_req,
                    )
                    db.add(opp_skill)

                await db.flush()

            created += 1
            created_opp_ids.append(opp.id)

        except Exception as exc:
            logger.error(
                "Failed to process opportunity record row %d: %s",
                row_num,
                exc,
                exc_info=True,
            )
            errors.append(
                {"row": row_num, "error": f"Failed to ingest record: {type(exc).__name__}"}
            )

    await db.commit()

    # Attempt embedding generation for newly created opportunities
    if created_opp_ids:
        try:
            from app.services.embeddings import generate_opportunity_embeddings_batch

            await generate_opportunity_embeddings_batch(db, created_opp_ids, commit=True)
        except Exception as emb_exc:
            logger.warning(
                "Non-fatal error generating opportunity embeddings during ingestion: %s",
                type(emb_exc).__name__,
            )

    logger.info(
        "Opportunity batch ingestion complete: total=%d, created=%d, skipped=%d, errors=%d",
        total,
        created,
        skipped_duplicates,
        len(errors),
    )
    return OpportunityIngestResult(
        total=total,
        created=created,
        skipped_duplicates=skipped_duplicates,
        errors=errors,
    )


async def ingest_csv_content(
    db: AsyncSession,
    csv_content: str | bytes,
) -> OpportunityIngestResult:
    """Convenience helper to ingest raw CSV string or byte stream."""
    if isinstance(csv_content, bytes):
        text_content = csv_content.decode("utf-8", errors="replace")
    else:
        text_content = str(csv_content)

    if not text_content.strip():
        return OpportunityIngestResult(
            total=0,
            created=0,
            skipped_duplicates=0,
            errors=[{"row": 0, "error": "CSV content is empty."}],
        )

    raw_rows = parse_csv_to_raw_rows(text_content)
    if not raw_rows:
        return OpportunityIngestResult(
            total=0,
            created=0,
            skipped_duplicates=0,
            errors=[{"row": 0, "error": "No valid data rows found in CSV."}],
        )

    return await ingest_raw_records(db, raw_rows)
