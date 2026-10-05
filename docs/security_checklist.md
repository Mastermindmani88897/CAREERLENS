# CareerLens — Security Hardening & Hygiene Checklist

This checklist defines mandatory security controls and verification procedures for the CareerLens project (Phase 8 Baseline).

---

## 1. Secret Management Policy

- **No Secrets in Source Control**: Never commit `.env`, private keys (`*.pem`, `*.key`), certificate bundles, or real API keys to git.
- **Environment Isolation**:
  - Root `.env` and `frontend/.env` must remain strictly gitignored.
  - Only template files (`.env.example` and `frontend/.env.example`) containing non-sensitive placeholders may be tracked.
- **Client/Frontend Separation**:
  - NEVER expose server-only variables (`JWT_SECRET`, `PGPASSWORD`, `DATABASE_URL`) to frontend client code or `VITE_` prefixed environment variables.
- **Pre-Push Secret Audit**:
  Run `python scripts/check_quality.py` or inspect staged files with:
  ```powershell
  git diff --cached
  ```

---

## 2. CORS Baseline Policy

- Development permits local origins (`http://localhost:5173` and `http://127.0.0.1:5173`).
- Allowed origins are configurable via `ALLOWED_ORIGINS` in `.env` (comma-delimited).
- Explicit HTTP methods allowed: `GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD`.
- Explicit HTTP headers allowed: `Content-Type, Authorization, Accept, Origin, X-Requested-With`.
- **Production Guard**: Wildcard origin `*` is strictly rejected by `Settings` validation in production.

---

## 3. Protective Security Headers

All HTTP responses automatically include standard defensive headers:
- `X-Content-Type-Options: nosniff` (mitigates MIME-type confusion attacks)
- `X-Frame-Options: DENY` (prevents clickjacking via iframes)
- `X-XSS-Protection: 1; mode=block` (enforces browser XSS reflection filter)
- `Referrer-Policy: strict-origin-when-cross-origin` (prevents path leakage in external referrers)
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()` (restricts unnecessary browser capabilities)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (enforced in production)

---

## 4. Logging & Redaction Policy

- All application logging passes through `SensitiveDataFilter` (`app.core.logging`).
- Automatically redacts:
  - User passwords and raw credential arguments (`password='***'`)
  - Authorization headers and bearer tokens (`[REDACTED_TOKEN]`)
  - Database connection strings with embedded passwords (passwords masked in connection URLs)
  - API keys and JWT secret values

---

## 5. Error Masking & Exception Exposure

- Unhandled exceptions return generic `{"detail": "Internal server error"}` with HTTP 500.
- Stack traces, database hostnames, internal filesystem paths, and query parameters are never rendered in client HTTP responses.
- Errors are logged server-side through the sanitized logging pipeline.
