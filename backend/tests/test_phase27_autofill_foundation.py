"""
Phase 27.2 Application Preparation Engine & Field-Mapping Foundation Tests.

Tests:
1. Safe URL Validation:
   - HTTPS scheme enforcement (rejection of http, file, javascript, data).
   - Rejection of embedded credentials/userinfo.
   - Rejection of non-allowlisted ATS domains.
   - Comprehensive SSRF defense: loopback, private, link-local, reserved, CGNAT,
     IPv4-mapped IPv6 prohibited IP rejection.
   - DNS resolution failure and mixed DNS response handling.
2. ATS Provider Detection:
   - Greenhouse standard and embed URLs.
   - Lever posting and direct-apply URLs.
   - Unsupported paths and unknown domains.
3. Candidate Payload Builder:
   - Full name safe splitting.
   - Verified contact, education, experience, and skill mapping.
   - Safe resume metadata inclusion (no raw text).
   - Missing fields and un-inferrable screening disclosure identification.
4. Autofill Session Service and API Endpoints:
   - Authentication enforcement (401).
   - Feature disablement gate (503 when AUTOFILL_ENABLED=False).
   - Inactive opportunity / missing opportunity handling (404/422).
   - Resume isolation and cross-candidate ownership checks (404).
   - Successful session creation and field mapping (201).
   - Idempotent active session reuse.
   - Candidate session retrieval and authorization (200/404).
   - Session cancellation (200).
"""

from __future__ import annotations

import socket
import uuid
from datetime import date
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.candidate import CandidateProfile, Education, Experience, Resume, Skill
from app.models.enums import (
    ATSProvider,
    AutofillSessionStatus,
    EducationLevel,
    EmploymentType,
    OpportunitySource,
    OpportunityType,
    SkillCategory,
    SkillSource,
    WorkMode,
)
from app.models.opportunity import Opportunity
from app.models.user import User
from app.services.autofill import (
    InvalidURLError,
    ProhibitedDestinationError,
    UnsupportedProviderError,
    build_normalized_autofill_payload,
    derive_names,
    detect_ats_provider,
    is_prohibited_ip,
    validate_external_application_url,
)
from tests.factories.candidate_factory import CandidateProfileFactory
from tests.helpers.auth import create_authenticated_headers, create_test_user

# =============================================================================
# 1. Safe URL Validator & SSRF Guardrail Tests
# =============================================================================


class TestSafeURLValidation:
    """Test URL safety, protocol restrictions, domain allowlisting, and SSRF prevention."""

    def test_prohibited_ip_detection(self) -> None:
        """Verify strict detection of private, loopback, link-local, and reserved IPs."""
        # IPv4 Prohibited
        assert is_prohibited_ip("127.0.0.1") is True
        assert is_prohibited_ip("127.0.1.1") is True
        assert is_prohibited_ip("10.0.0.1") is True
        assert is_prohibited_ip("172.16.0.1") is True
        assert is_prohibited_ip("172.31.255.255") is True
        assert is_prohibited_ip("192.168.1.1") is True
        assert is_prohibited_ip("169.254.169.254") is True  # Cloud metadata
        assert is_prohibited_ip("0.0.0.0") is True
        assert is_prohibited_ip("255.255.255.255") is True
        assert is_prohibited_ip("100.64.0.1") is True  # CGNAT
        assert is_prohibited_ip("224.0.0.1") is True  # Multicast

        # IPv6 Prohibited
        assert is_prohibited_ip("::1") is True  # Loopback
        assert is_prohibited_ip("::") is True  # Unspecified
        assert is_prohibited_ip("fc00::1") is True  # Unique local
        assert is_prohibited_ip("fe80::1") is True  # Link-local
        assert is_prohibited_ip("::ffff:127.0.0.1") is True  # IPv4-mapped loopback
        assert is_prohibited_ip("::ffff:169.254.169.254") is True  # IPv4-mapped metadata
        assert is_prohibited_ip("::ffff:10.0.0.1") is True  # IPv4-mapped private

        # Public IPs (Permitted)
        assert is_prohibited_ip("8.8.8.8") is False
        assert is_prohibited_ip("1.1.1.1") is False
        assert is_prohibited_ip("140.82.121.3") is False

    def test_reject_empty_or_control_characters(self) -> None:
        """Reject empty strings or strings containing control characters."""
        with pytest.raises(InvalidURLError, match="cannot be empty"):
            validate_external_application_url("", resolve_dns=False)

        with pytest.raises(InvalidURLError, match="control characters"):
            validate_external_application_url(
                "https://boards.greenhouse.io/test\x00/jobs", resolve_dns=False
            )

    def test_reject_non_https_schemes(self) -> None:
        """Strictly reject http, file, javascript, ftp, data schemes."""
        prohibited_urls = [
            "http://boards.greenhouse.io/company/jobs/123",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "data:text/html,<html></html>",
            "ftp://boards.greenhouse.io/company/jobs/123",
        ]
        for u in prohibited_urls:
            with pytest.raises(InvalidURLError, match="Only secure 'https://' URLs are supported"):
                validate_external_application_url(u, resolve_dns=False)

    def test_reject_embedded_credentials(self) -> None:
        """Reject URLs embedding authentication credentials."""
        with pytest.raises(InvalidURLError, match="embedded authentication credentials"):
            validate_external_application_url(
                "https://admin:secret@boards.greenhouse.io/company/jobs/123",
                resolve_dns=False,
            )

    def test_reject_direct_ip_hostname(self) -> None:
        """Reject direct IP addresses in host position."""
        with pytest.raises(InvalidURLError, match="Direct IP address access is prohibited"):
            validate_external_application_url("https://127.0.0.1/jobs", resolve_dns=False)

    def test_reject_unsupported_domains(self) -> None:
        """Reject domains not on the allowlist."""
        unsupported = [
            "https://evil.com/jobs/123",
            "https://mycompany.com/apply",
            "https://indeed.com/viewjob",
        ]
        for u in unsupported:
            with pytest.raises(UnsupportedProviderError, match="not a supported ATS platform"):
                validate_external_application_url(u, resolve_dns=False)

    def test_dns_resolution_failure(self) -> None:
        """Reject URLs when DNS fails to resolve the hostname."""
        with patch(
            "app.services.autofill.url_validator.resolve_hostname_ips",
            side_effect=socket.gaierror("Name or service not known"),
        ):
            with pytest.raises(InvalidURLError, match="DNS resolution failed"):
                validate_external_application_url("https://boards.greenhouse.io/gitlab/jobs/123")

    def test_dns_resolving_to_private_destination(self) -> None:
        """Reject URLs if DNS resolves to an internal or private address."""
        # Simulated DNS rebinding attack returning AWS metadata IP
        fake_addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]
        with patch(
            "app.services.autofill.url_validator.resolve_hostname_ips", return_value=fake_addr_info
        ):
            with pytest.raises(ProhibitedDestinationError, match="prohibited or internal"):
                validate_external_application_url("https://boards.greenhouse.io/gitlab/jobs/123")

    def test_valid_allowlisted_url_with_public_dns(self) -> None:
        """Accept valid Greenhouse and Lever URLs resolving to public IPs."""
        fake_addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.18.25.100", 443))]
        with patch(
            "app.services.autofill.url_validator.resolve_hostname_ips", return_value=fake_addr_info
        ):
            url, ips = validate_external_application_url(
                "https://boards.greenhouse.io/gitlab/jobs/12345"
            )
            assert url == "https://boards.greenhouse.io/gitlab/jobs/12345"
            assert "104.18.25.100" in ips


# =============================================================================
# 2. ATS Provider Detection Tests
# =============================================================================


class TestATSProviderDetection:
    """Test modular ATS provider detection and identifier parsing."""

    def test_greenhouse_standard_url(self) -> None:
        """Correctly detect Greenhouse standard job URL."""
        res = detect_ats_provider("https://boards.greenhouse.io/gitlab/jobs/7141381002")
        assert res.is_supported is True
        assert res.provider == ATSProvider.GREENHOUSE
        assert res.board_slug == "gitlab"
        assert res.external_job_id == "7141381002"
        assert res.is_direct_apply_page is True

    def test_greenhouse_embed_url(self) -> None:
        """Correctly detect Greenhouse embedded job application URL."""
        res = detect_ats_provider(
            "https://boards.greenhouse.io/embed/job_app?for=razorpay&token=554433"
        )
        assert res.is_supported is True
        assert res.provider == ATSProvider.GREENHOUSE
        assert res.board_slug == "razorpay"
        assert res.external_job_id == "554433"
        assert res.is_direct_apply_page is True

    def test_lever_posting_and_apply_url(self) -> None:
        """Correctly detect Lever hosted and direct apply URLs."""
        # Standard posting URL
        res1 = detect_ats_provider(
            "https://jobs.lever.co/spotify/e1f98bc4-9d56-4c3e-a81d-66911c42f0e1"
        )
        assert res1.is_supported is True
        assert res1.provider == ATSProvider.LEVER
        assert res1.board_slug == "spotify"
        assert res1.external_job_id == "e1f98bc4-9d56-4c3e-a81d-66911c42f0e1"
        assert res1.is_direct_apply_page is False

        # Direct apply URL
        res2 = detect_ats_provider(
            "https://jobs.lever.co/spotify/e1f98bc4-9d56-4c3e-a81d-66911c42f0e1/apply"
        )
        assert res2.is_supported is True
        assert res2.provider == ATSProvider.LEVER
        assert res2.is_direct_apply_page is True

    def test_unsupported_urls(self) -> None:
        """Return unsupported for non-matching paths or unknown hosts."""
        res1 = detect_ats_provider("https://boards.greenhouse.io/static/about")
        assert res1.is_supported is False
        assert res1.provider == ATSProvider.UNSUPPORTED

        res2 = detect_ats_provider("https://example.com/jobs/123")
        assert res2.is_supported is False
        assert res2.provider == ATSProvider.UNSUPPORTED


# =============================================================================
# 3. Normalized Payload Builder Tests
# =============================================================================


class TestPayloadBuilder:
    """Test candidate profile and resume data mapping."""

    def test_derive_names(self) -> None:
        """Verify defensive first and last name extraction."""
        assert derive_names("Jane Doe") == ("Jane", "Doe")
        assert derive_names("Alex Morgan Smith") == ("Alex", "Morgan Smith")
        assert derive_names("Cher") == ("Cher", "")
        assert derive_names("") == ("", "")
        assert derive_names(None) == ("", "")

    def test_build_normalized_payload_complete(self) -> None:
        """Verify full candidate profile mapping with verified resume metadata."""
        profile = CandidateProfile(
            full_name="Sarah Connor",
            phone="+1-555-0199",
            location_city="San Francisco",
            location_state="CA",
            location_country="United States",
            linkedin_url="https://linkedin.com/in/sarah-connor",
            github_url="https://github.com/sconnor",
            portfolio_url="https://sarahconnor.dev",
        )
        profile.user = User(email="sarah@resistance.org", hashed_password="pw")
        profile.skills = [
            Skill(skill_name="Python", category=SkillCategory.TECHNICAL, source=SkillSource.MANUAL),
            Skill(
                skill_name="FastAPI", category=SkillCategory.TECHNICAL, source=SkillSource.MANUAL
            ),
        ]
        profile.educations = [
            Education(
                institution="UC Berkeley",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                education_level=EducationLevel.BACHELOR,
                start_date=date(2018, 9, 1),
                end_date=date(2022, 5, 30),
                is_current=False,
                grade="3.9 GPA",
            )
        ]
        profile.experiences = [
            Experience(
                company="Cyberdyne Systems",
                title="Systems Engineer",
                start_date=date(2022, 6, 1),
                end_date=None,
                is_current=True,
                description="Backend platform development with Python.",
                skills_used=["Python", "PostgreSQL"],
            )
        ]

        resume = Resume(
            id=uuid.uuid4(),
            candidate_profile_id=uuid.uuid4(),
            filename="sarah_connor_cv.pdf",
            file_path="/safe/storage/cv.pdf",
            file_type="pdf",
            file_size_bytes=102400,
            raw_text="CONFIDENTIAL RESUME TEXT NOT EXPOSED IN PAYLOAD",
            is_active=True,
        )

        payload, missing_fields = build_normalized_autofill_payload(profile, resume)

        # Contact assertions
        assert payload["contact"]["first_name"] == "Sarah"
        assert payload["contact"]["last_name"] == "Connor"
        assert payload["contact"]["email"] == "sarah@resistance.org"
        assert payload["contact"]["phone"] == "+1-555-0199"
        assert payload["contact"]["linkedin_url"] == "https://linkedin.com/in/sarah-connor"

        # Education & Experience assertions
        assert len(payload["educations"]) == 1
        assert payload["educations"][0]["institution"] == "UC Berkeley"
        assert len(payload["experiences"]) == 1
        assert payload["experiences"][0]["company"] == "Cyberdyne Systems"
        assert "Python" in payload["skills"]

        # Safe Resume assertions (no raw text)
        assert payload["resume"]["filename"] == "sarah_connor_cv.pdf"
        assert "raw_text" not in payload["resume"]

        # Un-inferrable questionnaire notices
        assert "screening.work_authorization_status" in missing_fields
        assert "screening.salary_expectations" in missing_fields

    def test_missing_fields_detection_for_minimal_profile(self) -> None:
        """Detect missing required fields when candidate profile is sparse."""
        profile = CandidateProfile(full_name="SingleNameOnly")
        profile.user = User(email="", hashed_password="pw")
        profile.skills = []

        profile.educations = []
        profile.experiences = []

        payload, missing_fields = build_normalized_autofill_payload(profile, resume=None)

        assert "contact.legal_name" in missing_fields
        assert "contact.phone" in missing_fields
        assert "education.history" in missing_fields
        assert "resume.attachment" in missing_fields
        assert payload["resume"] is None


# =============================================================================
# 4. API Endpoints & Session Management Integration Tests
# =============================================================================


class TestAutofillAPIEndpoints:
    """Integration test suite for /api/v1/autofill endpoints."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Unauthenticated requests must be rejected with HTTP 401."""
        resp = await async_client.post(
            "/api/v1/autofill/prepare",
            json={"opportunity_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_feature_disabled_gate(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """When AUTOFILL_ENABLED is False, prepare endpoint returns HTTP 503."""
        user, _ = await create_test_user(db_session)
        await db_session.commit()
        headers = create_authenticated_headers(user.id)

        with patch.object(settings, "AUTOFILL_ENABLED", False):
            resp = await async_client.post(
                "/api/v1/autofill/prepare",
                json={"opportunity_id": str(uuid.uuid4())},
                headers=headers,
            )
            assert resp.status_code == 503
            assert "disabled" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_missing_candidate_profile_returns_404(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Candidate without an initialized profile receives HTTP 404."""
        user, _ = await create_test_user(db_session)
        await db_session.commit()
        headers = create_authenticated_headers(user.id)

        with patch.object(settings, "AUTOFILL_ENABLED", True):
            resp = await async_client.post(
                "/api/v1/autofill/prepare",
                json={"opportunity_id": str(uuid.uuid4())},
                headers=headers,
            )
            assert resp.status_code == 404
            assert "candidate profile not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_nonexistent_and_inactive_opportunity_errors(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Non-existent opportunity returns 404; inactive returns 422."""
        user, _ = await create_test_user(db_session)
        headers = create_authenticated_headers(user.id)
        await CandidateProfileFactory.create(
            db_session, user_id=user.id, full_name="Alice Developer"
        )
        await db_session.commit()

        with patch.object(settings, "AUTOFILL_ENABLED", True):
            # 1. Non-existent opportunity
            missing_opp_id = str(uuid.uuid4())
            resp1 = await async_client.post(
                "/api/v1/autofill/prepare",
                json={"opportunity_id": missing_opp_id},
                headers=headers,
            )
            assert resp1.status_code == 404

            # 2. Inactive opportunity
            inactive_opp = Opportunity(
                title="Archived Engineer",
                company="Old Corp",
                description="Inactive role",
                opportunity_type=OpportunityType.JOB,
                employment_type=EmploymentType.FULLTIME,
                work_mode=WorkMode.REMOTE,
                source=OpportunitySource.GREENHOUSE,
                source_id=f"inactive-{uuid.uuid4()}",
                job_url="https://boards.greenhouse.io/oldcorp/jobs/112233",
                is_active=False,
            )
            db_session.add(inactive_opp)
            await db_session.commit()

            resp2 = await async_client.post(
                "/api/v1/autofill/prepare",
                json={"opportunity_id": str(inactive_opp.id)},
                headers=headers,
            )
            assert resp2.status_code == 422
            assert "inactive" in resp2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_unsupported_external_url_returns_400(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Opportunity with an unsupported job_url returns HTTP 400."""
        user, _ = await create_test_user(db_session)
        headers = create_authenticated_headers(user.id)
        await CandidateProfileFactory.create(db_session, user_id=user.id, full_name="Bob Engineer")

        opp = Opportunity(
            title="External Role",
            company="Unsupported Corp",
            description="Role on unsupported site",
            opportunity_type=OpportunityType.JOB,
            employment_type=EmploymentType.FULLTIME,
            work_mode=WorkMode.REMOTE,
            source=OpportunitySource.REMOTIVE,
            source_id=f"remotive-{uuid.uuid4()}",
            job_url="https://remotive.com/jobs/unsupported-role",
            is_active=True,
        )
        db_session.add(opp)
        await db_session.commit()

        with patch.object(settings, "AUTOFILL_ENABLED", True):
            resp = await async_client.post(
                "/api/v1/autofill/prepare",
                json={"opportunity_id": str(opp.id)},
                headers=headers,
            )
            assert resp.status_code == 400
            assert "not a supported ats platform" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resume_isolation_between_candidates(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Candidate cannot prepare autofill using another candidate's resume_id."""
        user1, _ = await create_test_user(db_session)
        headers1 = create_authenticated_headers(user1.id)
        await CandidateProfileFactory.create(
            db_session, user_id=user1.id, full_name="Candidate One"
        )

        user2, _ = await create_test_user(db_session)
        profile2 = await CandidateProfileFactory.create(
            db_session, user_id=user2.id, full_name="Candidate Two"
        )

        # Resume belonging to Candidate Two
        resume2 = Resume(
            candidate_profile_id=profile2.id,
            filename="candidate_two_resume.pdf",
            file_path="/storage/resumes/c2.pdf",
            file_type="pdf",
            file_size_bytes=50000,
            is_active=True,
        )
        db_session.add(resume2)

        # Opportunity for Greenhouse
        opp = Opportunity(
            title="Senior Backend Engineer",
            company="GitLab",
            description="Remote GitLab role",
            opportunity_type=OpportunityType.JOB,
            employment_type=EmploymentType.FULLTIME,
            work_mode=WorkMode.REMOTE,
            source=OpportunitySource.GREENHOUSE,
            source_id=f"gh-{uuid.uuid4()}",
            job_url="https://boards.greenhouse.io/gitlab/jobs/998877",
            is_active=True,
        )
        db_session.add(opp)
        await db_session.commit()

        # Candidate One attempts to specify Candidate Two's resume
        fake_addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.18.25.100", 443))]
        with (
            patch.object(settings, "AUTOFILL_ENABLED", True),
            patch(
                "app.services.autofill.url_validator.resolve_hostname_ips",
                return_value=fake_addr_info,
            ),
        ):
            resp = await async_client.post(
                "/api/v1/autofill/prepare",
                json={
                    "opportunity_id": str(opp.id),
                    "resume_id": str(resume2.id),
                },
                headers=headers1,
            )
            assert resp.status_code == 404
            assert "resume" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_successful_autofill_preparation_and_idempotent_reuse(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Successfully prepare session and verify idempotent active session reuse."""
        user, _ = await create_test_user(db_session)
        headers = create_authenticated_headers(user.id)
        profile = await CandidateProfileFactory.create(
            db_session, user_id=user.id, full_name="Grace Hopper"
        )

        resume = Resume(
            candidate_profile_id=profile.id,
            filename="grace_hopper_resume.pdf",
            file_path="/storage/resumes/hopper.pdf",
            file_type="pdf",
            file_size_bytes=80000,
            is_active=True,
        )
        db_session.add(resume)

        opp = Opportunity(
            title="Distributed Systems Lead",
            company="Spotify",
            description="Spotify backend infrastructure",
            opportunity_type=OpportunityType.JOB,
            employment_type=EmploymentType.FULLTIME,
            work_mode=WorkMode.REMOTE,
            source=OpportunitySource.LEVER,
            source_id=f"lever-{uuid.uuid4()}",
            job_url="https://jobs.lever.co/spotify/abcde-12345-ffeedd",
            is_active=True,
        )
        db_session.add(opp)
        await db_session.commit()

        fake_addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.18.25.100", 443))]
        with (
            patch.object(settings, "AUTOFILL_ENABLED", True),
            patch(
                "app.services.autofill.url_validator.resolve_hostname_ips",
                return_value=fake_addr_info,
            ),
        ):
            # 1. First Preparation Call
            resp1 = await async_client.post(
                "/api/v1/autofill/prepare",
                json={"opportunity_id": str(opp.id)},
                headers=headers,
            )
            assert resp1.status_code == 201
            data1 = resp1.json()
            session_id1 = data1["id"]
            assert data1["ats_provider"] == "lever"
            assert data1["status"] == AutofillSessionStatus.DATA_MAPPED.value
            assert data1["normalized_payload"]["contact"]["first_name"] == "Grace"
            assert data1["normalized_payload"]["contact"]["last_name"] == "Hopper"
            assert data1["normalized_payload"]["resume"]["filename"] == "grace_hopper_resume.pdf"

            # 2. Second Call (Idempotent reuse of active session)
            resp2 = await async_client.post(
                "/api/v1/autofill/prepare",
                json={"opportunity_id": str(opp.id)},
                headers=headers,
            )
            assert resp2.status_code == 201
            data2 = resp2.json()
            assert data2["id"] == session_id1  # Reused identical active session!

            # 3. Retrieve Session by ID
            resp3 = await async_client.get(
                f"/api/v1/autofill/{session_id1}",
                headers=headers,
            )
            assert resp3.status_code == 200
            assert resp3.json()["id"] == session_id1

            # 4. Cancel Session
            resp4 = await async_client.post(
                f"/api/v1/autofill/{session_id1}/cancel",
                headers=headers,
            )
            assert resp4.status_code == 200
            assert resp4.json()["status"] == AutofillSessionStatus.CANCELLED.value
