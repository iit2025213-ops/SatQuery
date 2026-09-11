-- migrations/021_terrain_tables.sql
-- Phase 8: Terrain Experience

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- Terrain Assets
-- =========================================================================
CREATE TABLE IF NOT EXISTS terrain_assets (
  terrain_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,

  dem_id UUID NOT NULL REFERENCES dem_assets(dem_id) ON DELETE CASCADE,
  gee_asset_id UUID REFERENCES gee_assets(gee_asset_id),

  -- Mode
  mode VARCHAR(10) NOT NULL,  -- 2d, 3d

  -- 2D outputs
  hillshade_url TEXT,
  contour_url TEXT,

  -- 3D outputs
  mesh_url TEXT,       -- glTF/GLB
  mesh_lod0_url TEXT,
  mesh_lod1_url TEXT,
  mesh_lod2_url TEXT,

  texture_url TEXT,

  -- Metadata
  bounds JSONB,           -- {minx, miny, maxx, maxy}
  elevation_stats JSONB,
  mesh_metadata JSONB,

  -- Processing options
  processing_params JSONB,  -- hillshade azimuth, exaggeration, etc

  -- Status
  status VARCHAR(50) DEFAULT 'pending',
  progress_percent INT DEFAULT 0,
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_terrain_job_id ON terrain_assets(job_id);
CREATE INDEX IF NOT EXISTS idx_terrain_mode ON terrain_assets(mode);

-- =========================================================================
-- Row Level Security
-- =========================================================================
ALTER TABLE terrain_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access terrain_assets"
  ON terrain_assets FOR ALL USING (auth.role() = 'service_role');
