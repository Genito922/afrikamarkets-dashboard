import os
import sys
import uvicorn

# WORKDIR=/app dans le Dockerfile, le code est copié dans /app
# donc backend/ est accessible comme /app/backend/
# mais Python voit app.main depuis /app/backend/
port = int(os.environ.get("PORT", 8000))

# Ajouter /app au PYTHONPATH
sys.path.insert(0, "/app")

uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
