"""
WSGI entry point for production deployment (Gunicorn, Vercel, etc.)
"""
import os
import sys
import traceback

try:
    from app.main import app
    print("✓ Successfully imported app.main")
except Exception as e:
    print(f"❌ Failed to import app.main: {e}")
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    print(f"Starting FastAPI server on port {port}...")
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        traceback.print_exc()
        sys.exit(1)
