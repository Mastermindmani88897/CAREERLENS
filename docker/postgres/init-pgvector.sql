-- =============================================================================
-- CareerLens — PostgreSQL Initialization Script
-- Executed on container cluster initialization within /docker-entrypoint-initdb.d
-- =============================================================================

-- Enable pgvector extension for high-performance vector embeddings and HNSW indexing
CREATE EXTENSION IF NOT EXISTS vector;
