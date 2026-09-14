#!/bin/bash
# ── Afrika Markets Intelligence — Deploy script (Alibaba Cloud ECS Ubuntu 22.04)
# Usage : bash deploy.sh [--init | --update | --ssl | --logs]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="api.sentinel-lccafrika.space"         # <- remplacer par votre sous-domaine
EMAIL="ndoubajeanclaude@outlook.com"
APP_DIR="/opt/afrikamarkets"
REPO="https://github.com/Genito922/afrikamarkets-dashboard.git"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[AMI]${NC} $*"; }
warn() { echo -e "${YELLOW}[AMI]${NC} $*"; }
err()  { echo -e "${RED}[AMI]${NC} $*" >&2; exit 1; }

# ── Fonctions ─────────────────────────────────────────────────────────────────

init_server() {
    log "Installation des dépendances système..."
    apt-get update -qq
    apt-get install -y -qq \
        docker.io docker-compose-v2 \
        nginx certbot python3-certbot-nginx \
        git curl ufw

    log "Configuration du pare-feu..."
    ufw allow OpenSSH
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable

    log "Activation de Docker..."
    systemctl enable --now docker

    log "Clonage du dépôt..."
    git clone "$REPO" "$APP_DIR" || (cd "$APP_DIR" && git pull origin main)

    log "Création des répertoires SSL..."
    mkdir -p "$APP_DIR/nginx/ssl" "$APP_DIR/nginx/certbot"

    if [ ! -f "$APP_DIR/.env.prod" ]; then
        cp "$APP_DIR/.env.prod.example" "$APP_DIR/.env.prod"
        warn "IMPORTANT : éditez $APP_DIR/.env.prod avant de continuer !"
        warn "  nano $APP_DIR/.env.prod"
        warn "Puis relancez : bash deploy.sh --ssl"
        exit 0
    fi

    log "Init terminée. Lancez : bash deploy.sh --ssl"
}

provision_ssl() {
    log "Obtention du certificat Let's Encrypt pour $DOMAIN..."
    certbot certonly --standalone \
        --non-interactive --agree-tos \
        --email "$EMAIL" \
        -d "$DOMAIN"

    log "Copie des certificats dans nginx/ssl/..."
    cp /etc/letsencrypt/live/"$DOMAIN"/fullchain.pem "$APP_DIR/nginx/ssl/"
    cp /etc/letsencrypt/live/"$DOMAIN"/privkey.pem   "$APP_DIR/nginx/ssl/"
    chmod 600 "$APP_DIR/nginx/ssl/"*.pem

    # Remplacer YOURDOMAIN dans nginx.conf
    sed -i "s/api\.YOURDOMAIN\.com/$DOMAIN/g" "$APP_DIR/nginx/nginx.conf"

    log "Démarrage des containers..."
    start_app

    # Cron renouvellement auto
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN/*.pem $APP_DIR/nginx/ssl/ && docker exec ami_nginx nginx -s reload") | crontab -
    log "Renouvellement SSL auto configuré (cron 3h00)."
}

start_app() {
    cd "$APP_DIR"
    docker compose -f docker-compose.prod.yml pull db nginx 2>/dev/null || true
    docker compose -f docker-compose.prod.yml up -d --build
    log "Containers démarrés."
    docker compose -f docker-compose.prod.yml ps
}

update_app() {
    log "Mise à jour de l'application..."
    cd "$APP_DIR"
    git pull origin main
    docker compose -f docker-compose.prod.yml up -d --build fastapi
    log "Mise à jour terminée."
}

show_logs() {
    cd "$APP_DIR"
    docker compose -f docker-compose.prod.yml logs -f --tail=100 fastapi
}

generate_secrets() {
    log "Génération des secrets pour .env.prod :"
    echo ""
    echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
    echo "POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────

case "${1:-}" in
    --init)     init_server ;;
    --ssl)      provision_ssl ;;
    --update)   update_app ;;
    --logs)     show_logs ;;
    --secrets)  generate_secrets ;;
    --start)    start_app ;;
    *)
        echo "Usage: bash deploy.sh [option]"
        echo ""
        echo "  --init      Première installation (Docker, dépôt, pare-feu)"
        echo "  --secrets   Générer SECRET_KEY + ENCRYPTION_KEY + POSTGRES_PASSWORD"
        echo "  --ssl       Obtenir certificat SSL + démarrer l'app"
        echo "  --update    Puller le dépôt + rebuilder le container FastAPI"
        echo "  --start     Démarrer sans rebuild"
        echo "  --logs      Suivre les logs FastAPI en temps réel"
        ;;
esac
