import os
import sys

# Ajouter la racine du projet au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

port = int(os.environ.get("PORT", 8000))
print(f"[START] Démarrage sur port {port}")
print(f"[START] Python path: {sys.path[:3]}")

uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, log_level="info")
