-- migrations/022_timeline_tables.sql
-- Phase 9: Temporal Timeline

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- Timeline Collections (multi-year query + alignment tracking)
-- =========================================================================
CREATE TABLE IF NOT EXISTS timeline_collections (
  timeline_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  aoi_id UUID NOT NULL REFERENCES aois(aoi_id) ON DELETE CASCADE,

  -- Query parameters
  date_start DATE NOT NULL,
  date_end DATE NOT NULL,
  year_count INT,

  collection_name VARCHAR(50),  -- Sentinel-2, Landsat
  cloud_cover_max INT,

  -- Alignment
  reference_year INT,
  alignment_status VARCHAR(50) DEFAULT 'pending',
  -- pending | aligned | completed | failed
  alignment_rmse FLOAT8,

  -- Status
  status VARCHAR(50) DEFAULT 'queued',
  progress_percent INT DEFAULT 0,
  error_log TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_job_id ON timeline_collections(job_id);
CREATE INDEX IF NOT EXISTS idx_timeline_aoi_id ON timeline_collections(aoi_id);

-- =========================================================================
-- Timeline Imagery (one row per year)
-- =========================================================================
CREATE TABLE IF NOT EXISTS timeline_imagery (
  timeline_imagery_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  timeline_id UUID NOT NULL REFERENCES timeline_collections(timeline_id) ON DELETE CASCADE,

  year INT NOT NULL,
  acquisition_date DATE,

  scene_id VARCHAR(500),
  cloud_cover_percent FLOAT8,

  cloudinary_public_id VARCHAR(255),
  cloudinary_url TEXT,

  -- Quality metrics
  valid_pixels_percent FLOAT8,

  -- Spectral indices
  ndvi_min FLOAT8,
  ndvi_max FLOAT8,
  ndvi_mean FLOAT8,

  status VARCHAR(50) DEFAULT 'processing',

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_imagery_timeline_id ON timeline_imagery(timeline_id);
CREATE INDEX IF NOT EXISTS idx_timeline_imagery_year ON timeline_imagery(year);

-- =========================================================================
-- Timeline Animations (GIF / MP4)
-- =========================================================================
CREATE TABLE IF NOT EXISTS timeline_animations (
  animation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  timeline_id UUID NOT NULL REFERENCES timeline_collections(timeline_id) ON DELETE CASCADE,

  format VARCHAR(10),  -- gif, mp4
  duration_seconds INT,
  frame_count INT,

  cloudinary_public_id VARCHAR(255),
  cloudinary_url TEXT,

  status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_animations_timeline_id ON timeline_animations(timeline_id);

-- =========================================================================
-- Row Level Security
-- =========================================================================
ALTER TABLE timeline_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_imagery ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_animations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access timeline_collections"
  ON timeline_collections FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access timeline_imagery"
  ON timeline_imagery FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access timeline_animations"
  ON timeline_animations FOR ALL USING (auth.role() = 'service_role');
