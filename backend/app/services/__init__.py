"""Services package."""

from app.services.auth_service import (
    authenticate_user,
    get_user_by_email,
    get_user_by_id,
    register_user,
)
from app.services.matching_service import (
    compute_and_persist_match,
    compute_hybrid_match,
    evaluate_eligibility,
    score_education,
    score_employment_type,
    score_experience,
    score_location,
    score_location_work_mode,
    score_skill_overlap,
    score_work_mode,
    upsert_match,
)
from app.services.opportunity_ingest_service import (
    ingest_csv_content,
    ingest_raw_records,
)
from app.services.opportunity_normalizer import (
    normalize_opportunity_type,
    normalize_url,
    sanitize_text,
)
from app.services.opportunity_skill_normalizer import (
    normalize_opportunity_skills,
    normalize_skill_name,
)

__all__ = [
    "authenticate_user",
    "compute_and_persist_match",
    "compute_hybrid_match",
    "evaluate_eligibility",
    "get_user_by_email",
    "get_user_by_id",
    "ingest_csv_content",
    "ingest_raw_records",
    "normalize_opportunity_skills",
    "normalize_opportunity_type",
    "normalize_skill_name",
    "normalize_url",
    "register_user",
    "sanitize_text",
    "score_education",
    "score_employment_type",
    "score_experience",
    "score_location",
    "score_location_work_mode",
    "score_skill_overlap",
    "score_work_mode",
    "upsert_match",
]
