-- Create videos table
CREATE TABLE IF NOT EXISTS videos (
    id UUID DEFAULT gen_random_uuid () PRIMARY KEY,
    digest_id UUID NOT NULL, -- References digests(id)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    s3_url TEXT NOT NULL,
    voice TEXT NOT NULL,
    status TEXT DEFAULT 'processing', -- 'processing', 'completed', 'failed'
    background_video TEXT, -- Which background video was used
    metadata JSONB, -- Additional metadata (model used, processing times, etc.)
    word_count INTEGER,
    subtitles_json JSONB -- Store the subtitle timing data
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_videos_digest_id ON videos (digest_id);

CREATE INDEX IF NOT EXISTS idx_videos_status ON videos (status);

CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos (created_at);

-- Add comment
COMMENT ON TABLE videos IS 'Stores generated TikTok-style brain rot videos with metadata';

-- Add RLS policies if needed
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

-- Allow read access to authenticated users
CREATE POLICY "Allow read access for authenticated users" ON videos FOR
SELECT TO authenticated USING (true);

-- Allow service role to perform all operations
CREATE POLICY "Allow service role to perform all operations" ON videos FOR ALL TO service_role USING (true);