"""Run migration to add extra_phones and social_media columns to leads table."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.database import get_supabase_admin


def migrate():
    db = get_supabase_admin()

    # Test if columns already exist by querying one lead
    try:
        result = db.table("leads").select("extra_phones,social_media").limit(1).execute()
        print("Columns already exist, migration not needed.")
        return
    except Exception:
        pass

    # Run migration via RPC or direct SQL
    # Supabase Python client doesn't support raw SQL, so we'll add columns
    # by inserting a test row and catching errors
    print("Columns don't exist yet. Please run this SQL in Supabase SQL Editor:")
    print()
    print("ALTER TABLE leads ADD COLUMN IF NOT EXISTS extra_phones text DEFAULT '';")
    print("ALTER TABLE leads ADD COLUMN IF NOT EXISTS social_media jsonb DEFAULT '{}';")
    print()
    print("Or run: supabase db push (if using Supabase CLI)")


if __name__ == "__main__":
    migrate()
