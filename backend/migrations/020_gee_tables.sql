-- migrations/020_gee_tables.sql
-- Phase 7: GEE/STAC Data Layer

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- GEE Collections (a query + its results)
-- =========================================================================
CREATE TABLE IF NOT EXISTS gee_collections (
  collection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Query parameters used
  query_params JSONB NOT NULL,
  -- {
  --   "aoi": {...},
  --   "date_start": "2024-01-01",
  --   "date_end": "2024-12-31",
  --   "collections": ["Sentinel-2", "Landsat-8"],
  --   "cloud_cover_max": 20
  -- }

  -- Results
  results_count INT DEFAULT 0,
  scenes_retrieved INT DEFAULT 0,

  -- Status
  status VARCHAR(50) DEFAULT 'queued',
  -- queued | authenticating | querying | downloading | processing | completed | failed
  progress_percent INT DEFAULT 0,
  error_message TEXT,

  -- Which satellite collection
  collection_name VARCHAR(100),  -- "Sentinel-2", "Landsat-8/9", "MODIS"

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gee_collections_job_id ON gee_collections(job_id);
CREATE INDEX IF NOT EXISTS idx_gee_collections_user_id ON gee_collections(user_id);
CREATE INDEX IF NOT EXISTS idx_gee_collections_status ON gee_collections(status);

-- =========================================================================
-- GEE Assets (individual scenes/images)
-- =========================================================================
CREATE TABLE IF NOT EXISTS gee_assets (
  gee_asset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  collection_id UUID NOT NULL REFERENCES gee_collections(collection_id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,

  -- Scene identification
  scene_id VARCHAR(500) NOT NULL,  -- GEE full asset path
  source VARCHAR(50) NOT NULL,     -- Sentinel-2, Landsat-8, Landsat-9, MODIS

  -- Temporal
  acquisition_date DATE NOT NULL,
  year_month VARCHAR(7),  -- YYYY-MM for indexing

  -- Quality
  cloud_cover_percent FLOAT8,
  valid_pixels_percent FLOAT8,

  -- Spatial
  crs VARCHAR(20),    -- EPSG code
  resolution_m INT,   -- 10, 30, 250, etc

  -- Bands
  bands JSONB,           -- ["B02", "B03", "B04", "B08", "B11", "B12"]
  band_wavelengths JSONB, -- {"B02": 490, "B03": 560, ...}

  -- Storage
  cloudinary_public_id VARCHAR(255),
  cloudinary_url TEXT,
  temp_file_path TEXT,

  -- Status
  status VARCHAR(50) DEFAULT 'pending',
  -- pending | downloading | processing | uploaded | failed
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gee_assets_collection_id ON gee_assets(collection_id);
CREATE INDEX IF NOT EXISTS idx_gee_assets_job_id ON gee_assets(job_id);
CREATE INDEX IF NOT EXISTS idx_gee_assets_source ON gee_assets(source);
CREATE INDEX IF NOT EXISTS idx_gee_assets_date ON gee_assets(acquisition_date);
CREATE INDEX IF NOT EXISTS idx_gee_assets_status ON gee_assets(status);

-- =========================================================================
-- DEM Assets
-- =========================================================================
CREATE TABLE IF NOT EXISTS dem_assets (
  dem_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  collection_id UUID NOT NULL REFERENCES gee_collections(collection_id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,

  -- DEM source
  source VARCHAR(50),   -- USGS-3DEP, SRTM, NASADEM
  resolution_m INT,

  -- Storage
  cloudinary_public_id VARCHAR(255),
  cloudinary_url TEXT,

  -- Elevation statistics
  elevation_stats JSONB,
  -- { "min_m": 100, "max_m": 2500, "mean_m": 800, "std_m": 450 }

  -- Spatial
  crs VARCHAR(20),
  bbox FLOAT8[],

  -- Status
  status VARCHAR(50) DEFAULT 'pending',
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dem_assets_collection_id ON dem_assets(collection_id);
CREATE INDEX IF NOT EXISTS idx_dem_assets_job_id ON dem_assets(job_id);

-- =========================================================================
-- Auto-update triggers
-- =========================================================================
CREATE OR REPLACE FUNCTION update_gee_collections_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_gee_collections_updated_at
  BEFORE UPDATE ON gee_collections
  FOR EACH ROW
  EXECUTE FUNCTION update_gee_collections_updated_at();

-- =========================================================================
-- Row Level Security
-- =========================================================================
ALTER TABLE gee_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE gee_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dem_assets ENABLE ROW LEVEL SECURITY;

-- gee_collections RLS
CREATE POLICY "Users can view own gee_collections"
  ON gee_collections FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own gee_collections"
  ON gee_collections FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access gee_collections"
  ON gee_collections FOR ALL USING (auth.role() = 'service_role');

-- gee_assets RLS (via join to gee_collections)
CREATE POLICY "Service role full access gee_assets"
  ON gee_assets FOR ALL USING (auth.role() = 'service_role');

-- dem_assets RLS
CREATE POLICY "Service role full access dem_assets"
  ON dem_assets FOR ALL USING (auth.role() = 'service_role');
