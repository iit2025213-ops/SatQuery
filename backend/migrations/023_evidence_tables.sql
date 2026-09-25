-- migrations/023_evidence_tables.sql
-- Phase 11: Evidence Graph + Provenance

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- Analysis (Top-level logical grouping for a single chat turn/execution)
-- =========================================================================
CREATE TABLE IF NOT EXISTS analysis (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(job_id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    query_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_job_id ON analysis(job_id);
CREATE INDEX IF NOT EXISTS idx_analysis_user_id ON analysis(user_id);

-- =========================================================================
-- Evidence (Immutable record of a scientific result/tool execution)
-- =========================================================================
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES analysis(analysis_id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(job_id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

    source VARCHAR(50) NOT NULL,       -- e.g. 'GEE', 'OpenAI'
    tool_name VARCHAR(100),            -- e.g. 'gee_calculate_change_area'
    methodology TEXT,                  -- explanation of the scientific approach
    parameters JSONB,                  -- AOI, dates, thresholds, etc.
    
    metric VARCHAR(100),               -- e.g. 'NDVI_change_area'
    value FLOAT8,                      -- numeric result if applicable
    unit VARCHAR(50),                  -- e.g. 'km2', 'index'
    scene_ids JSONB,                   -- The exact scenes used in computation
    quality_metadata JSONB,            -- observation counts, valid pixel %
    
    fingerprint_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of the core result data to prevent tampering

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evidence is IMMUTABLE. Prevent UPDATE operations.
CREATE OR REPLACE FUNCTION prevent_evidence_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Evidence records are immutable and cannot be updated.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_prevent_evidence_update
    BEFORE UPDATE ON evidence
    FOR EACH ROW
    EXECUTE FUNCTION prevent_evidence_update();

CREATE INDEX IF NOT EXISTS idx_evidence_analysis_id ON evidence(analysis_id);
CREATE INDEX IF NOT EXISTS idx_evidence_job_id ON evidence(job_id);
CREATE INDEX IF NOT EXISTS idx_evidence_user_id ON evidence(user_id);

-- =========================================================================
-- Evidence Relationships (e.g. finding supports evidence, etc)
-- =========================================================================
CREATE TABLE IF NOT EXISTS evidence_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_evidence_id UUID NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    target_evidence_id UUID NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- 'computed_by', 'supports', 'derived_from'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_er_source ON evidence_relationships(source_evidence_id);
CREATE INDEX IF NOT EXISTS idx_er_target ON evidence_relationships(target_evidence_id);

-- =========================================================================
-- Artifacts (Persistent outputs like Rasters, DOCX, Timelines)
-- =========================================================================
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES analysis(analysis_id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(job_id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

    artifact_type VARCHAR(50) NOT NULL, -- 'docx', 'raster', 'timeline', 'timelapse'
    url TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_analysis_id ON artifacts(analysis_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_job_id ON artifacts(job_id);

-- =========================================================================
-- Artifact <-> Evidence (Many-to-Many Bridge)
-- =========================================================================
CREATE TABLE IF NOT EXISTS artifact_evidence (
    artifact_id UUID NOT NULL REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (artifact_id, evidence_id)
);

-- =========================================================================
-- Row Level Security (RLS)
-- =========================================================================
ALTER TABLE analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_evidence ENABLE ROW LEVEL SECURITY;

-- Analysis
CREATE POLICY "Users can view own analysis" ON analysis FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own analysis" ON analysis FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access analysis" ON analysis FOR ALL USING (auth.role() = 'service_role');

-- Evidence
CREATE POLICY "Users can view own evidence" ON evidence FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own evidence" ON evidence FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access evidence" ON evidence FOR ALL USING (auth.role() = 'service_role');

-- Evidence Relationships (Check via Source Evidence Owner)
CREATE POLICY "Users can view own evidence_relationships" ON evidence_relationships 
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM evidence WHERE evidence_id = source_evidence_id AND user_id = auth.uid())
    );
CREATE POLICY "Users can insert own evidence_relationships" ON evidence_relationships 
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM evidence WHERE evidence_id = source_evidence_id AND user_id = auth.uid())
    );
CREATE POLICY "Service role full access evidence_relationships" ON evidence_relationships FOR ALL USING (auth.role() = 'service_role');

-- Artifacts
CREATE POLICY "Users can view own artifacts" ON artifacts FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own artifacts" ON artifacts FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access artifacts" ON artifacts FOR ALL USING (auth.role() = 'service_role');

-- Artifact Evidence (Check via Artifact Owner)
CREATE POLICY "Users can view own artifact_evidence" ON artifact_evidence 
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM artifacts WHERE artifact_id = artifact_evidence.artifact_id AND user_id = auth.uid())
    );
CREATE POLICY "Users can insert own artifact_evidence" ON artifact_evidence 
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM artifacts WHERE artifact_id = artifact_evidence.artifact_id AND user_id = auth.uid())
    );
CREATE POLICY "Service role full access artifact_evidence" ON artifact_evidence FOR ALL USING (auth.role() = 'service_role');
