-- Add html_url column to proposals table for Gemini-generated HTML
ALTER TABLE proposals ADD COLUMN IF NOT EXISTS html_url text DEFAULT '';
