"""
database/models.py — Afrika Markets Intelligence
SQLAlchemy models partagés (Streamlit + FastAPI)
Les migrations Alembic restent dans backend/alembic/
"""
# Les modèles ORM sont dans backend/app/models/ (FastAPI async)
# Ce fichier sert de référence pour la structure de la base
#
# Tables principales :
#   - users            (auth)
#   - subscriptions    (plans Lemon Squeezy)
#   - brvm_actions     (cours actions)
#   - brvm_indices     (indices marché + sectoriels)
#   - brvm_market_summary (récap journalier)
#   - price_history    (OHLCV historique par titre)
#   - alerts           (alertes utilisateur)
