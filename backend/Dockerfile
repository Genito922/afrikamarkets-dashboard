FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le projet dans /app
COPY . .

# /app est le WORKDIR, backend/ est à /app/backend/
# Python path inclut /app donc "backend.app.main" fonctionne
CMD ["python", "backend/start.py"]
