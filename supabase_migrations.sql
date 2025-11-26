-- Supabase migration script for bot_service
-- This script creates the necessary tables and RPC functions for:
--  - usuarios (user credits management)
--  - knowledge_base (RAG knowledge storage with vector column)
--  - search and credit management RPCs

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- Table: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
  user_id BIGINT PRIMARY KEY,
  credit_balance INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Optional metadata to store purchases or other user-specific info
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
-- Optional columns to store telegram user name info
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS last_name TEXT;
-- Track updates to usuarios
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Table: knowledge_base
CREATE TABLE IF NOT EXISTS knowledge_base (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  content_embedding VECTOR(384) NOT NULL,
  tags TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Update updated_at timestamp on update
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_knowledge_base_updated_at
BEFORE UPDATE ON knowledge_base
FOR EACH ROW
EXECUTE PROCEDURE update_timestamp_column();

-- Index for vector similarity search; lists tuned for indexing speed vs memory
-- 384 is the embedding dimension (all-MiniLM-L6-v2)
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON knowledge_base
  USING ivfflat (content_embedding vector_l2_ops) WITH (lists = 100);

-- Function: deduct_credit
-- Atomically decrements 1 credit if balance > 0, returns boolean success
CREATE OR REPLACE FUNCTION deduct_credit(uid BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
  current_balance INTEGER;
BEGIN
  SELECT credit_balance INTO current_balance FROM usuarios WHERE user_id = uid FOR UPDATE;
  IF NOT FOUND OR current_balance <= 0 THEN
    RETURN FALSE;
  END IF;
  UPDATE usuarios SET credit_balance = credit_balance - 1 WHERE user_id = uid;
  PERFORM log_audit_event(uid, 'deduct_credit', jsonb_build_object('old_balance', current_balance, 'new_balance', current_balance - 1));
  RETURN TRUE;
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

-- Function: add_credits
-- Adds credits to an existing user or creates a new one with initial balance
CREATE OR REPLACE FUNCTION add_credits(uid BIGINT, amount INTEGER)
RETURNS VOID AS $$
BEGIN
  INSERT INTO usuarios(user_id, credit_balance, created_at)
    VALUES(uid, amount, now())
  ON CONFLICT (user_id) DO UPDATE
    SET credit_balance = usuarios.credit_balance + amount;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- Function: add_or_update_user
-- Usage: rpc('add_or_update_user', { uid: bigint, first_name: text, last_name: text, username: text, initial_balance: int })
CREATE OR REPLACE FUNCTION add_or_update_user(uid BIGINT, first_name TEXT DEFAULT NULL, last_name TEXT DEFAULT NULL, username TEXT DEFAULT NULL, initial_balance INTEGER DEFAULT 0)
RETURNS BOOLEAN AS $$
DECLARE
  _exists BOOLEAN;
BEGIN
  SELECT EXISTS(SELECT 1 FROM usuarios WHERE user_id = uid) INTO _exists;
  IF NOT _exists THEN
    INSERT INTO usuarios (user_id, first_name, last_name, username, credit_balance, created_at, updated_at)
      VALUES (uid, first_name, last_name, username, initial_balance, now(), now());
    RETURN TRUE; -- created
  ELSE
    UPDATE usuarios
    SET first_name = COALESCE(first_name, usuarios.first_name),
        last_name = COALESCE(last_name, usuarios.last_name),
        username = COALESCE(username, usuarios.username),
        updated_at = now()
    WHERE user_id = uid;
    RETURN FALSE; -- existed
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; -- executed with function owner privileges (avoid RLS/permission issues)

-- Function: search_knowledge_base
-- Accepts a float8[] vector as query_embedding and returns top_k results
CREATE OR REPLACE FUNCTION search_knowledge_base(query_embedding float8[], top_k INTEGER DEFAULT 5)
RETURNS TABLE(id UUID, title TEXT, content TEXT, similarity FLOAT) AS $$
BEGIN
  RETURN QUERY
  SELECT id, title, content,
         1 - (content_embedding <#> query_embedding::vector) AS similarity
  FROM knowledge_base
  ORDER BY content_embedding <#> query_embedding::vector
  LIMIT top_k;
END;
$$ LANGUAGE plpgsql STABLE;

-- Notes:
--  - The vector operator '<#>' stands for cosine distance in pgvector. Using 1 - distance to get similarity in [0..1].
--  - If you prefer Euclidean distance, change to '<->' operator and adjust similarity calculation accordingly.
--  - Ensure your Supabase project has 'pgvector' enabled (the "vector" extension) and enough memory for ivfflat index.

-- End of migration

-- =============================
-- Production safety and auditing
-- =============================

-- Add updated_at if missing (idempotent already above)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Audit log for recording important user events (credits, registration, updates)
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id BIGINT,
  event_type TEXT NOT NULL,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Function to write to audit_log with SECURITY DEFINER
CREATE OR REPLACE FUNCTION log_audit_event(p_user_id BIGINT, p_event_type TEXT, p_details JSONB DEFAULT '{}'::jsonb)
RETURNS VOID AS $$
BEGIN
  INSERT INTO audit_log (user_id, event_type, details, created_at)
    VALUES (p_user_id, p_event_type, p_details, now());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Ensure trigger for updated_at column on usuarios
CREATE OR REPLACE FUNCTION update_usuarios_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_update_usuarios_updated_at'
  ) THEN
    CREATE TRIGGER trg_update_usuarios_updated_at
      BEFORE UPDATE ON usuarios
      FOR EACH ROW
      EXECUTE PROCEDURE update_usuarios_timestamp_column();
  END IF;
END;
$$;

-- Update add_credits RPC to audit the operation (replace existing function)
CREATE OR REPLACE FUNCTION add_credits(uid BIGINT, amount INTEGER)
RETURNS VOID AS $$
DECLARE
  _exists BOOLEAN;
BEGIN
  SELECT EXISTS(SELECT 1 FROM usuarios WHERE user_id = uid) INTO _exists;
  IF NOT _exists THEN
    INSERT INTO usuarios(user_id, credit_balance, created_at, updated_at)
      VALUES(uid, amount, now(), now());
  ELSE
    UPDATE usuarios SET credit_balance = usuarios.credit_balance + amount, updated_at = now() WHERE user_id = uid;
  END IF;
  PERFORM log_audit_event(uid, 'add_credits', jsonb_build_object('amount', amount));
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

-- Replace add_or_update_user RPC to call audit logging
CREATE OR REPLACE FUNCTION add_or_update_user(uid BIGINT, first_name TEXT DEFAULT NULL, last_name TEXT DEFAULT NULL, username TEXT DEFAULT NULL, initial_balance INTEGER DEFAULT 0)
RETURNS BOOLEAN AS $$
DECLARE
  _exists BOOLEAN;
BEGIN
  SELECT EXISTS(SELECT 1 FROM usuarios WHERE user_id = uid) INTO _exists;
  IF NOT _exists THEN
    INSERT INTO usuarios (user_id, first_name, last_name, username, credit_balance, created_at, updated_at)
      VALUES (uid, first_name, last_name, username, initial_balance, now(), now());
    PERFORM log_audit_event(uid, 'user_created', jsonb_build_object('first_name', first_name, 'last_name', last_name, 'username', username, 'initial_balance', initial_balance));
    RETURN TRUE; -- created
  ELSE
    UPDATE usuarios
    SET first_name = COALESCE(first_name, usuarios.first_name),
        last_name = COALESCE(last_name, usuarios.last_name),
        username = COALESCE(username, usuarios.username),
        updated_at = now()
    WHERE user_id = uid;
    PERFORM log_audit_event(uid, 'user_updated', jsonb_build_object('first_name', first_name, 'last_name', last_name, 'username', username));
    RETURN FALSE; -- existed
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Row Level Security: enable RLS and create restricted policies
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

-- Allow public (anon) to SELECT users (readonly)
DROP POLICY IF EXISTS allow_anon_select_usuarios ON usuarios;
CREATE POLICY allow_anon_select_usuarios ON usuarios
  FOR SELECT
  USING (true);

-- Deny INSERT/UPDATE/DELETE from anon by not creating permissive policies for them.
-- The backend should use the service_role key and RPCs to insert/update entries.
DROP POLICY IF EXISTS allow_anon_insert_usuarios ON usuarios;
DROP POLICY IF EXISTS allow_anon_update_usuarios ON usuarios;
-- No policy = default deny; keep explicit deny policies for clarity
CREATE POLICY deny_anon_insert_usuarios ON usuarios
  FOR INSERT
  WITH CHECK (false);

CREATE POLICY deny_anon_update_usuarios ON usuarios
  FOR UPDATE
  USING (false)
  WITH CHECK (false);

CREATE POLICY deny_anon_delete_usuarios ON usuarios
  FOR DELETE
  USING (false);

