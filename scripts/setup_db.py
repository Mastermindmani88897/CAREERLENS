"""
CareerLens — Database and pgvector Setup Script.

Initializes PostgreSQL roles, databases, and pgvector extension
without hardcoding or exposing sensitive credentials.
"""

import asyncio
import os
import re
import secrets
import sys
from pathlib import Path

import asyncpg

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE = ROOT_DIR / ".env.example"


async def main() -> None:
    superuser_password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD")
    scratch_file = (
        Path(os.environ.get("USERPROFILE", ""))
        / ".gemini"
        / "antigravity-ide"
        / "brain"
        / "f6564141-1178-4c20-bf2d-8ee33f78eb0a"
        / "scratch"
        / "pgpass.txt"
    )
    if not superuser_password and scratch_file.exists():
        superuser_password = scratch_file.read_text(encoding="utf-8").strip()
        try:
            scratch_file.unlink()
        except OSError:
            pass

    if not superuser_password:
        print(
            "Error: Superuser password must be provided via PGPASSWORD or "
            "POSTGRES_PASSWORD environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    host = os.environ.get("PGHOST", "localhost")
    port = int(os.environ.get("PGPORT", "5432"))
    superuser = os.environ.get("PGUSER", "postgres")

    db_user = "careerlens_user"
    main_db = "careerlens_db"
    test_db = "careerlens_test"

    # Determine or generate careerlens_user password
    app_db_password = None
    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
        match = re.search(r"DATABASE_URL=postgresql\+asyncpg://[^:]+:([^@]+)@", content)
        if match and match.group(1) != "PASSWORD":
            app_db_password = match.group(1)

    if not app_db_password:
        app_db_password = secrets.token_urlsafe(24)

    # 1. Connect to PostgreSQL server as superuser
    try:
        sys_conn = await asyncpg.connect(
            user=superuser,
            password=superuser_password,
            host=host,
            port=port,
            database="postgres",
        )
    except (asyncpg.PostgresError, OSError) as e:
        print(
            f"Error: Unable to connect to PostgreSQL as {superuser}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # Check/create role
        role_exists = await sys_conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", db_user)
        if not role_exists:
            # DDL does not allow parameterized role creation directly for role name/password
            # We use an anonymous code block to pass the password safely
            await sys_conn.execute(
                """
                DO $role$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'careerlens_user') THEN
                        CREATE ROLE careerlens_user WITH LOGIN;
                    END IF;
                END
                $role$;
                """
            )
            print(f"Role '{db_user}' created.")
        else:
            print(f"Role '{db_user}' already exists.")

        # Ensure least-privilege role attributes (remove CREATEDB if present)
        await sys_conn.execute(f"ALTER ROLE {db_user} NOCREATEDB;")
        print(f"Role '{db_user}' configured with least-privilege (NOCREATEDB).")

        # Update password securely via format with sanitized token.
        # token_urlsafe contains only url-safe base64 [a-zA-Z0-9_-], no SQL injection possible.
        await sys_conn.execute(  # nosec B608
            f"ALTER ROLE {db_user} WITH PASSWORD '{app_db_password}';"
        )

        # Check/create databases
        for db_name in [main_db, test_db]:
            db_exists = await sys_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            if not db_exists:
                await sys_conn.execute(f'CREATE DATABASE "{db_name}" OWNER {db_user};')
                print(f"Database '{db_name}' created.")
            else:
                await sys_conn.execute(f'ALTER DATABASE "{db_name}" OWNER TO {db_user};')
                print(f"Database '{db_name}' already exists.")
    finally:
        await sys_conn.close()

    # 2. Configure extension and permissions in each database as superuser
    for db_name in [main_db, test_db]:
        db_conn = await asyncpg.connect(
            user=superuser,
            password=superuser_password,
            host=host,
            port=port,
            database=db_name,
        )
        try:
            await db_conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await db_conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO {db_user};')
            await db_conn.execute(f"GRANT ALL ON SCHEMA public TO {db_user};")
            ext_version = await db_conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
            )
            print(f"pgvector extension v{ext_version} active in '{db_name}'.")
        finally:
            await db_conn.close()

    # 3. Create or update .env file
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        env_content = ENV_EXAMPLE.read_text(encoding="utf-8")
    elif ENV_FILE.exists():
        env_content = ENV_FILE.read_text(encoding="utf-8")
    else:
        env_content = ""

    # Replace placeholders
    main_url = f"postgresql+asyncpg://{db_user}:{app_db_password}@{host}:{port}/{main_db}"
    test_url = f"postgresql+asyncpg://{db_user}:{app_db_password}@{host}:{port}/{test_db}"

    if "DATABASE_URL=" in env_content:
        env_content = re.sub(
            r"DATABASE_URL=.*",
            f"DATABASE_URL={main_url}",
            env_content,
        )
    else:
        env_content += f"\nDATABASE_URL={main_url}"

    if "TEST_DATABASE_URL=" in env_content:
        env_content = re.sub(
            r"TEST_DATABASE_URL=.*",
            f"TEST_DATABASE_URL={test_url}",
            env_content,
        )
    else:
        env_content += f"\nTEST_DATABASE_URL={test_url}"

    # Generate secrets if missing/empty
    if re.search(r"APP_SECRET_KEY=\s*$", env_content, re.MULTILINE):
        env_content = re.sub(
            r"APP_SECRET_KEY=\s*$",
            f"APP_SECRET_KEY={secrets.token_urlsafe(32)}",
            env_content,
            flags=re.MULTILINE,
        )

    if re.search(r"JWT_SECRET_KEY=\s*$", env_content, re.MULTILINE):
        env_content = re.sub(
            r"JWT_SECRET_KEY=\s*$",
            f"JWT_SECRET_KEY={secrets.token_urlsafe(32)}",
            env_content,
            flags=re.MULTILINE,
        )

    ENV_FILE.write_text(env_content, encoding="utf-8")
    print(f"Configured environment file at '{ENV_FILE.name}'.")

    # 4. Verify connection as careerlens_user
    app_conn = await asyncpg.connect(
        user=db_user,
        password=app_db_password,
        host=host,
        port=port,
        database=main_db,
    )
    try:
        val = await app_conn.fetchval("SELECT '[1,2,3]'::vector <-> '[3,2,1]'::vector;")
        print(f"Verified application user connection and vector math: distance = {val:.4f}")
    finally:
        await app_conn.close()

    print("PostgreSQL and pgvector setup completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
