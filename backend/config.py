import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://frontend-chi-azure-98.vercel.app",
        "https://frontend-6viv3g1uu-criptomtp-5211s-projects.vercel.app",
        "https://mtp-lead-agent.vercel.app",
        "https://mtp-lead-agent.vercel.app",
    ] + ([os.getenv("FRONTEND_URL")] if os.getenv("FRONTEND_URL") else [])


settings = Settings()
