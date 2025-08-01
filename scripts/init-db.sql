-- Database initialization script for Faculty Research Opportunity Notifier
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions that might be useful for the research application
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For similarity searches
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- For accent-insensitive searches

-- Create application user (if not already created by environment variables)
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'research_app') THEN
--         CREATE ROLE research_app WITH LOGIN PASSWORD 'app_password';
--     END IF;
-- END
-- $$;

-- Grant necessary permissions
-- GRANT CONNECT ON DATABASE research_db TO research_app;
-- GRANT USAGE ON SCHEMA public TO research_app;
-- GRANT CREATE ON SCHEMA public TO research_app;

-- Create initial tables (uncomment when ready to use PostgreSQL)
/*
-- Faculty profiles table
CREATE TABLE IF NOT EXISTS faculty_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    institution VARCHAR(255),
    department VARCHAR(255),
    research_interests TEXT[],
    publications JSONB DEFAULT '[]',
    career_stage VARCHAR(50),
    contact_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Funding opportunities table
CREATE TABLE IF NOT EXISTS funding_opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    agency VARCHAR(255) NOT NULL,
    program VARCHAR(255),
    description TEXT,
    research_areas TEXT[],
    eligibility_criteria TEXT[],
    funding_amount_min DECIMAL(12,2),
    funding_amount_max DECIMAL(12,2),
    deadline TIMESTAMP WITH TIME ZONE,
    application_url VARCHAR(1000),
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Research matches table
CREATE TABLE IF NOT EXISTS research_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    faculty_id UUID REFERENCES faculty_profiles(id) ON DELETE CASCADE,
    opportunity_id UUID REFERENCES funding_opportunities(id) ON DELETE CASCADE,
    match_score DECIMAL(5,4) NOT NULL CHECK (match_score >= 0 AND match_score <= 1),
    score_breakdown JSONB DEFAULT '{}',
    research_ideas JSONB DEFAULT '[]',
    collaborator_suggestions JSONB DEFAULT '[]',
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(faculty_id, opportunity_id)
);

-- System metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4),
    metric_metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_faculty_research_interests ON faculty_profiles USING GIN (research_interests);
CREATE INDEX IF NOT EXISTS idx_funding_research_areas ON funding_opportunities USING GIN (research_areas);
CREATE INDEX IF NOT EXISTS idx_funding_deadline ON funding_opportunities (deadline);
CREATE INDEX IF NOT EXISTS idx_matches_score ON research_matches (match_score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_faculty ON research_matches (faculty_id);
CREATE INDEX IF NOT EXISTS idx_matches_opportunity ON research_matches (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time ON system_metrics (metric_name, recorded_at DESC);

-- Create full-text search indexes
CREATE INDEX IF NOT EXISTS idx_faculty_name_search ON faculty_profiles USING GIN (to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_funding_title_search ON funding_opportunities USING GIN (to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_funding_description_search ON funding_opportunities USING GIN (to_tsvector('english', description));

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_faculty_profiles_updated_at BEFORE UPDATE ON faculty_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_funding_opportunities_updated_at BEFORE UPDATE ON funding_opportunities FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_research_matches_updated_at BEFORE UPDATE ON research_matches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
*/

-- Insert some initial data for testing (uncomment when ready)
/*
INSERT INTO faculty_profiles (name, email, institution, department, research_interests, career_stage) VALUES
('Dr. Sarah Johnson', 'sarah.johnson@university.edu', 'State University', 'Computer Science', 
 ARRAY['machine learning', 'artificial intelligence', 'healthcare AI'], 'Assistant Professor'),
('Dr. Michael Chen', 'michael.chen@university.edu', 'State University', 'Biology', 
 ARRAY['computational biology', 'genomics', 'bioinformatics'], 'Associate Professor'),
('Dr. Emily Rodriguez', 'emily.rodriguez@university.edu', 'State University', 'Engineering', 
 ARRAY['robotics', 'automation', 'human-robot interaction'], 'Full Professor')
ON CONFLICT (email) DO NOTHING;
*/

-- Create a simple health check function
CREATE OR REPLACE FUNCTION database_health_check()
RETURNS TEXT AS $$
BEGIN
    RETURN 'Database is healthy at ' || NOW();
END;
$$ LANGUAGE plpgsql;