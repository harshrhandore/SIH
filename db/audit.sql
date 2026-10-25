CREATE TABLE audit_chains (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid UNIQUE REFERENCES institutions,
 name text NOT NULL,
 head_seq bigint NOT NULL DEFAULT 0 CHECK (head_seq >= 0),
 head_hash text NOT NULL DEFAULT repeat('0',64) CHECK (head_hash ~ '^[0-9a-f]{64}$')
);
CREATE UNIQUE INDEX ux_system_audit_chain ON audit_chains((1)) WHERE institution_id IS NULL;
CREATE TABLE audit_events (
 chain_id uuid NOT NULL REFERENCES audit_chains,
 sequence_no bigint NOT NULL CHECK (sequence_no > 0),
 id uuid NOT NULL UNIQUE,
 institution_id uuid REFERENCES institutions,
 student_id uuid REFERENCES students,
 actor_id uuid NOT NULL REFERENCES users,
 action text NOT NULL,
 entity_type text NOT NULL,
 entity_id text NOT NULL,
 reason text NOT NULL,
 occurred_at timestamptz NOT NULL,
 payload jsonb NOT NULL,
 canonical_text text NOT NULL CHECK (jsonb_typeof(canonical_text::jsonb)='object'),
 prev_hash text NOT NULL CHECK (prev_hash ~ '^[0-9a-f]{64}$'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 PRIMARY KEY (chain_id,sequence_no)
);
CREATE INDEX ix_audit_student_time ON audit_events(student_id,occurred_at,sequence_no);
CREATE INDEX ix_audit_scope_time ON audit_events(institution_id,occurred_at DESC);
CREATE TRIGGER audit_event_immutable BEFORE UPDATE OR DELETE ON audit_events
 FOR EACH ROW EXECUTE FUNCTION protect_history();
CREATE TRIGGER audit_event_no_truncate BEFORE TRUNCATE ON audit_events
 FOR EACH STATEMENT EXECUTE FUNCTION protect_history();

CREATE FUNCTION append_audit(p_chain uuid,p_canonical text)
RETURNS TABLE(sequence_no bigint,row_hash text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE c audit_chains%ROWTYPE; e jsonb; next_seq bigint; next_hash text;
BEGIN
 SELECT * INTO c FROM audit_chains WHERE id=p_chain FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'AUDIT_CHAIN_NOT_FOUND'; END IF;
 e := p_canonical::jsonb;
 next_seq := c.head_seq+1;
 IF e->>'chain_id' IS DISTINCT FROM p_chain::text
   OR (e->>'sequence_no')::bigint IS DISTINCT FROM next_seq
   OR (e->>'institution_id')::uuid IS DISTINCT FROM c.institution_id THEN
   RAISE EXCEPTION 'AUDIT_ENVELOPE_MISMATCH';
 END IF;
 IF NOT (e ?& ARRAY['event_id','chain_id','sequence_no','institution_id','student_id',
    'actor_id','action','entity_type','entity_id','reason','occurred_at','payload']) THEN
   RAISE EXCEPTION 'AUDIT_FIELDS_MISSING';
 END IF;
 IF (SELECT count(*) FROM jsonb_object_keys(e)) <> 12 THEN
   RAISE EXCEPTION 'AUDIT_EXTRA_FIELDS';
 END IF;
 IF jsonb_typeof(e->'payload')<>'object' THEN RAISE EXCEPTION 'AUDIT_PAYLOAD_INVALID'; END IF;
 IF (e->>'student_id') IS NOT NULL AND NOT EXISTS (
   SELECT 1 FROM students s WHERE s.id=(e->>'student_id')::uuid AND s.institution_id=c.institution_id
 ) THEN RAISE EXCEPTION 'AUDIT_STUDENT_SCOPE'; END IF;
 next_hash := encode(digest(convert_to(c.head_hash||p_canonical,'UTF8'),'sha256'),'hex');
 INSERT INTO audit_events(chain_id,sequence_no,id,institution_id,student_id,actor_id,
   action,entity_type,entity_id,reason,occurred_at,payload,canonical_text,prev_hash,row_hash)
 VALUES(p_chain,next_seq,(e->>'event_id')::uuid,c.institution_id,(e->>'student_id')::uuid,
   (e->>'actor_id')::uuid,e->>'action',e->>'entity_type',e->>'entity_id',e->>'reason',
   (e->>'occurred_at')::timestamptz,e->'payload',p_canonical,c.head_hash,next_hash);
 UPDATE audit_chains SET head_seq=next_seq,head_hash=next_hash WHERE id=p_chain;
 RETURN QUERY SELECT next_seq,next_hash;
END $$;
REVOKE ALL ON FUNCTION append_audit(uuid,text) FROM PUBLIC;

CREATE FUNCTION lock_audit_chain(p_institution uuid) RETURNS SETOF audit_chains
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 RETURN QUERY SELECT * FROM audit_chains WHERE institution_id IS NOT DISTINCT FROM p_institution FOR UPDATE;
END $$;
REVOKE ALL ON FUNCTION lock_audit_chain(uuid) FROM PUBLIC;

CREATE FUNCTION demo_sandbox_snapshot(p_institution uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE result jsonb;
BEGIN
 IF to_regclass('demo_sandbox.audit_chains') IS NULL OR to_regclass('demo_sandbox.audit_events') IS NULL THEN
   RETURN NULL;
 END IF;
 SELECT jsonb_build_object(
  'chain',(SELECT to_jsonb(c) FROM demo_sandbox.audit_chains c WHERE c.institution_id=p_institution),
  'events',(SELECT jsonb_agg(to_jsonb(e) ORDER BY e.sequence_no) FROM demo_sandbox.audit_events e WHERE e.institution_id=p_institution)
 ) INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION demo_sandbox_snapshot(uuid) FROM PUBLIC;
