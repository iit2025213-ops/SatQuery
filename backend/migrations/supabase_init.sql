-- migrations/supabase_init.sql
-- Phase 6: AOI System

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- AOI Table
CREATE TABLE IF NOT EXISTS aois (
  aoi_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- GeoJSON
  geojson JSONB NOT NULL,  -- Full Polygon geometry

  -- Bounding box (precomputed)
  bbox FLOAT8[] NOT NULL,  -- [minx, miny, maxx, maxy]

  -- Calculated properties
  area_m2 FLOAT8,
  area_km2 FLOAT8,
  centroid FLOAT8[],  -- [lon, lat]

  -- CRS
  crs VARCHAR(20) DEFAULT 'EPSG:4326',  -- WGS84

  -- Validation
  validation_status VARCHAR(50) DEFAULT 'pending',  -- pending, valid, invalid
  validation_errors JSONB,  -- Error messages if invalid

  -- Metadata
  source VARCHAR(50),  -- drawn, uploaded, auto-generated
  description TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_aois_job_id ON aois(job_id);
CREATE INDEX IF NOT EXISTS idx_aois_user_id ON aois(user_id);
CREATE INDEX IF NOT EXISTS idx_aois_validation_status ON aois(validation_status);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_aois_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_aois_updated_at
  BEFORE UPDATE ON aois
  FOR EACH ROW
  EXECUTE FUNCTION update_aois_updated_at();

-- Enable Row Level Security
ALTER TABLE aois ENABLE ROW LEVEL SECURITY;

-- RLS Policies: users can only access their own AOIs
CREATE POLICY "Users can view own AOIs"
  ON aois FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own AOIs"
  ON aois FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own AOIs"
  ON aois FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own AOIs"
  ON aois FOR DELETE
  USING (auth.uid() = user_id);

-- Service role bypass (for backend operations)
CREATE POLICY "Service role full access"
  ON aois FOR ALL
  USING (auth.role() = 'service_role');
