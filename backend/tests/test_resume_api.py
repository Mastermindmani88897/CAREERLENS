"""
Integration tests for Phase 11 Resume Processing API endpoints:
- POST /api/v1/resumes
- GET /api/v1/resumes/{resume_id}
- GET /api/v1/resumes
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.candidate import Resume
from app.models.user import User
from tests.helpers.auth import create_authenticated_headers, create_test_user
from tests.helpers.synthetic_resumes import (
    create_malformed_pdf,
    create_no_text_pdf,
    create_oversized_resume,
    create_synthetic_docx_resume,
    create_synthetic_pdf_resume,
    create_synthetic_txt_resume,
    create_unsupported_file,
)


@pytest.mark.asyncio
async def test_upload_resume_unauthenticated_rejected() -> None:
    """Unauthenticated requests are rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            files={"file": ("resume.txt", b"some text", "text/plain")},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_resume_txt_success(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """Authenticated user uploads valid TXT resume successfully."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    txt_bytes = create_synthetic_txt_resume()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("resume.txt", txt_bytes, "text/plain")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "resume.txt"
    assert data["file_type"] == "txt"
    assert data["status"] == "parsed"
    assert data["parsed_data"] is not None
    assert data["parsed_data"]["contact"]["full_name"] == "Alex Morgan"
    assert len(data["parsed_data"]["skills"]) > 0

    # Verify database persistence
    resume_id = uuid.UUID(data["id"])
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db_session.execute(stmt)
    saved_resume = res.scalar_one_or_none()
    assert saved_resume is not None
    assert saved_resume.raw_text is not None
    assert saved_resume.file_type == "txt"


@pytest.mark.asyncio
async def test_upload_resume_pdf_success(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """Authenticated user uploads valid PDF resume successfully."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    pdf_bytes = create_synthetic_pdf_resume()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("candidate_resume.pdf", pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "pdf"
    assert data["status"] == "parsed"
    assert data["parsed_data"]["contact"]["full_name"] == "Taylor Swiftness"


@pytest.mark.asyncio
async def test_upload_resume_docx_success(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """Authenticated user uploads valid DOCX resume successfully."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    docx_bytes = create_synthetic_docx_resume()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={
                "file": (
                    "jordan_resume.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "docx"
    assert data["status"] == "parsed"
    assert data["parsed_data"]["contact"]["full_name"] == "Jordan Lee"


@pytest.mark.asyncio
async def test_upload_no_text_pdf_returns_422(
    authenticated_user: tuple[User, str],
) -> None:
    """Scanned/blank PDF with no text returns 422 with explanation that OCR is not supported."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    blank_pdf = create_no_text_pdf()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("blank_scan.pdf", blank_pdf, "application/pdf")},
        )

    assert response.status_code == 422
    assert "OCR is not supported in Phase 11" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_malformed_document_rejected(
    authenticated_user: tuple[User, str],
) -> None:
    """Corrupted PDF document is rejected with 400 Bad Request."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    corrupted = create_malformed_pdf()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("corrupt.pdf", corrupted, "application/pdf")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_unsupported_extension_rejected(
    authenticated_user: tuple[User, str],
) -> None:
    """Executable content or unsupported extension is rejected with 400."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    exe_bytes = create_unsupported_file()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("malicious.exe", exe_bytes, "application/octet-stream")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected(
    authenticated_user: tuple[User, str],
) -> None:
    """Oversized file exceeding size limit is rejected with 400."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    oversized = create_oversized_resume(size_mb=11)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("huge.pdf", oversized, "application/pdf")},
        )

    assert response.status_code == 400
    assert "exceeds maximum" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_resume_detail_and_list(
    authenticated_user: tuple[User, str],
) -> None:
    """Authenticated user can retrieve their uploaded resume by ID and in list view."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)
    txt_bytes = create_synthetic_txt_resume()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        upload_res = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("my_resume.txt", txt_bytes, "text/plain")},
        )
        assert upload_res.status_code == 201
        resume_id = upload_res.json()["id"]

        # 1. Retrieve by ID
        detail_res = await ac.get(f"/api/v1/resumes/{resume_id}", headers=headers)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["id"] == resume_id
        assert detail_data["raw_text"] is not None

        # 2. List resumes
        list_res = await ac.get("/api/v1/resumes", headers=headers)
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 1
        assert any(item["id"] == resume_id for item in list_data["items"])


@pytest.mark.asyncio
async def test_unauthorized_resume_access_prevented(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """User B cannot access User A's uploaded resume (returns 403 Forbidden)."""
    user_a, _ = authenticated_user
    user_b, _ = await create_test_user(db_session)
    await db_session.commit()

    headers_a = create_authenticated_headers(user_a.id)
    headers_b = create_authenticated_headers(user_b.id)

    txt_bytes = create_synthetic_txt_resume()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        upload_res = await ac.post(
            "/api/v1/resumes",
            headers=headers_a,
            files={"file": ("user_a_resume.txt", txt_bytes, "text/plain")},
        )
        assert upload_res.status_code == 201
        resume_id = upload_res.json()["id"]

        # User B attempts to access User A's resume
        b_res = await ac.get(f"/api/v1/resumes/{resume_id}", headers=headers_b)
        assert b_res.status_code == 403
        assert "permission" in b_res.json()["detail"].lower()
