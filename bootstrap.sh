#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()     { echo -e "${GREEN}[OK]${NC} $1"; }
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
section() { echo -e "\n${BLUE}============================================================${NC}"; echo -e "${BLUE} $1${NC}"; echo -e "${BLUE}============================================================${NC}"; }

REPO_URL="https://github.com/FarwBr/financaspro.git"
PROJECT_DIR="/home/univates/financaspro"
RUNNER_DIR="/home/univates/actions-runner"
RUNNER_VERSION="2.322.0"

section "FinancasPro — Bootstrap"
info "Repositorio: $REPO_URL"

section "PASSO 1/5 — Atualizando sistema"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git
log "Sistema atualizado"

section "PASSO 2/5 — Instalando Docker"
if ! command -v docker &>/dev/null; then
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    log "Docker instalado"
else
    log "Docker ja instalado: $(docker --version)"
fi

section "PASSO 3/5 — Clonando repositorio"
if [ -d "$PROJECT_DIR" ]; then
    sudo rm -rf "$PROJECT_DIR"
fi
git clone "$REPO_URL" "$PROJECT_DIR"
cat > "$PROJECT_DIR/.env" << EOF
DB_PASSWORD=financas123
SECRET_KEY=financas_prod_secret_2024
EOF
log "Repositorio clonado"

section "PASSO 4/5 — Subindo containers"
cd "$PROJECT_DIR"
sudo docker compose build
sudo docker compose up -d
sleep 10
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
log "Containers iniciados"

section "PASSO 5/5 — Instalando GitHub Actions Runner"
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"
curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
log "Runner baixado"

echo ""
echo -e "${YELLOW}================================================================${NC}"
echo -e "${YELLOW} ACAO NECESSARIA:${NC}"
echo -e "${YELLOW} Acesse: https://github.com/FarwBr/financaspro/settings/actions/runners/new${NC}"
echo -e "${YELLOW} Selecione Linux / x64 e copie o token${NC}"
echo -e "${YELLOW}================================================================${NC}"
echo ""
read -p "Cole o token do GitHub Actions Runner: " RUNNER_TOKEN

./config.sh \
    --url https://github.com/FarwBr/financaspro \
    --token "$RUNNER_TOKEN" \
    --name "vm-univates" \
    --labels "self-hosted,Linux,X64" \
    --work "_work" \
    --unattended \
    --replace

sudo ./svc.sh install
sudo ./svc.sh start
log "Runner configurado e iniciado"

echo ""
echo -e "${GREEN}=== Bootstrap concluido! ===${NC}"
echo -e "Producao:    http://177.44.248.60:5000"
echo -e "Homologacao: http://177.44.248.60:5001"
echo -e "Login: admin / Senha: admin123"
