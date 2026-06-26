# -*- coding: utf-8 -*-
import os
import sys

# Le Dockerfile copie tout dans /app
# start.py est à /app/backend/start.py
# donc la racine projet = /app
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)

import uvicorn

# Railway attribue dynamiquement un port via la variable PORT
port = int(os.environ.get("PORT", 8080))
print(f"ROOT={root} PORT={port}", flush=True)

# Lancement d'Uvicorn avec le rechargement désactivé en production (plus stable)
uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")