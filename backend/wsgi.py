"""
WSGI entry point for production deployment (Gunicorn, Vercel, etc.)
"""
import os
from app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
