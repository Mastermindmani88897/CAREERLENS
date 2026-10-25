-- =============================================================================
-- CareerLens — PostgreSQL Initialization Script
-- Executed on container cluster initialization within /docker-entrypoint-initdb.d
-- =============================================================================

-- Enable pgvector extension for high-performance vector embeddings and HNSW indexing
CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure application role careerlens_user exists with least-privilege attributes
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'careerlens_user') THEN
        CREATE ROLE careerlens_user WITH LOGIN PASSWORD 'careerlens_secure_pass';
    END IF;
    IF (SELECT rolsuper FROM pg_roles WHERE rolname = 'careerlens_user') IS FALSE THEN
        ALTER ROLE careerlens_user WITH LOGIN NOCREATEDB NOSUPERUSER NOCREATEROLE;
    END IF;
END
$$;

