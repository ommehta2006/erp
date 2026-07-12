from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_supabase
import logging

app = FastAPI(title="FactoryPulse Global ERP API", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

@app.get("/")
def read_root():
    return {"message": "Welcome to FactoryPulse Global ERP API. Powered by FastAPI and Supabase."}

@app.get("/health")
def health_check():
    try:
        supabase = get_supabase()
        # Basic check to see if we can connect/initialize client
        if supabase:
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# --- Department API Modules ---

# HR Module
@app.get("/api/hr/employees")
def get_employees():
    try:
        supabase = get_supabase()
        response = supabase.table("employees").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Finance Module
@app.get("/api/finance/invoices")
def get_invoices():
    try:
        supabase = get_supabase()
        response = supabase.table("invoices").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Operations Module
@app.get("/api/operations/incidents")
def get_incidents():
    try:
        supabase = get_supabase()
        response = supabase.table("incidents").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
