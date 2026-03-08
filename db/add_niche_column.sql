-- Add niche column to leads table
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/poybvsigfcxivoiygysk/sql
ALTER TABLE leads ADD COLUMN IF NOT EXISTS niche text DEFAULT '';
