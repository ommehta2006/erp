import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")

def get_supabase() -> Client:
    if not url or not key:
        raise ValueError("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY in .env")
    return create_client(url, key)
