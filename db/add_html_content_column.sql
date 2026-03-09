-- Add html_content column to proposals table for storing Gemini-generated HTML directly
-- This avoids Supabase Storage encoding issues with Cyrillic text
ALTER TABLE proposals ADD COLUMN IF NOT EXISTS html_content text DEFAULT '';
