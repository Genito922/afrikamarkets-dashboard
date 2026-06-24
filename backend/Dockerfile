FROM python:3.11-slim

WORKDIR /app

# Copier et installer les dépendances
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le projet
COPY . .

# PORT est injecté par Railway
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
