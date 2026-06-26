import os, sys

# Le Dockerfile copie tout dans /app
# start.py est à /app/backend/start.py
# donc la racine projet = /app
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)

import uvicorn
port = int(os.environ.get("PORT", 8000))
print(f"ROOT={root} PORT={port}", flush=True)

# Depuis /app, le module s'appelle backend.app.main
uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
