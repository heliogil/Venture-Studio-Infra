-- Migration 002: Full-text search (keyword search) sobre documents
-- Adiciona coluna tsvector + índice GIN para busca híbrida (semântica + keyword)

ALTER TABLE documents ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    to_tsvector('portuguese', coalesce(title, '') || ' ' || coalesce(content, ''))
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_documents_fts
  ON documents USING gin(fts);
