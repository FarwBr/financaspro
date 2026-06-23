#!/bin/bash
# =============================================================================
# setup-prod.sh — FinancasPro
# Sobe APENAS o ambiente de Produção (após Homolog já estar no ar)
# Uso: curl -fsSL https://raw.githubusercontent.com/FarwBr/financaspro/main/setup-prod.sh | bash
# =============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()     { echo -e "${GREEN}[OK]${NC} $1"; }
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
section() { echo -e "\n${BLUE}============================================================${NC}"; \
            echo -e "${BLUE} $1${NC}"; \
            echo -e "${BLUE}============================================================${NC}"; }

PROJECT_DIR="/home/univates/financaspro"

section "FinancasPro — Subindo Produção"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[ERRO]${NC} Projeto não encontrado em $PROJECT_DIR"
    echo "Execute primeiro o bootstrap.sh!"
    exit 1
fi

cd "$PROJECT_DIR"

info "Subindo containers de Produção..."
sudo docker compose up -d postgres_prod
sleep 10
sudo docker compose up -d app_prod
sleep 10

info "Status de todos os containers:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

section "Produção no ar!"
echo ""
echo -e "${GREEN}Homologação:${NC} ${BLUE}http://177.44.248.60:5001${NC} ✅"
echo -e "${GREEN}Produção:${NC}    ${BLUE}http://177.44.248.60:5000${NC} ✅"
echo ""
echo -e "${GREEN}Credenciais:${NC} admin / admin123"
echo ""
