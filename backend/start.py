import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uvicorn
port = int(os.environ.get("PORT", 8000))
print(f"Starting on port {port}", flush=True)
uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
