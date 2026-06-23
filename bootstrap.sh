#!/bin/bash
# =============================================================================
# bootstrap.sh — FinancasPro
# Instala tudo do zero e sobe APENAS o ambiente de Homologação
# Uso: curl -fsSL https://raw.githubusercontent.com/FarwBr/financaspro/main/bootstrap.sh | bash
# =============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()     { echo -e "${GREEN}[OK]${NC} $1"; }
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error()   { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }
section() { echo -e "\n${BLUE}============================================================${NC}"; \
            echo -e "${BLUE} $1${NC}"; \
            echo -e "${BLUE}============================================================${NC}"; }

REPO_URL="https://github.com/FarwBr/financaspro.git"
REPO_OWNER="FarwBr"
REPO_NAME="financaspro"
PROJECT_DIR="/home/univates/financaspro"
RUNNER_DIR="/home/univates/actions-runner"
RUNNER_VERSION="2.322.0"
# PAT passado como variável de ambiente
# Uso: curl -fsSL .../bootstrap.sh | GITHUB_PAT=ghp_xxx bash
if [ -z "$GITHUB_PAT" ]; then
    echo -e "${RED}[ERRO]${NC} Variável GITHUB_PAT não definida!"
    echo "Use: curl -fsSL .../bootstrap.sh | GITHUB_PAT=seu_token bash"
    exit 1
fi

section "FinancasPro — Bootstrap (Homologação)"
info "Repositório: $REPO_URL"

# =============================================================================
# PASSO 1 — Atualizar sistema
# =============================================================================
section "PASSO 1/5 — Atualizando sistema"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git
log "Sistema atualizado"

# =============================================================================
# PASSO 2 — Instalar Docker
# =============================================================================
section "PASSO 2/5 — Instalando Docker"
if ! command -v docker &>/dev/null; then
    info "Instalando Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    log "Docker instalado: $(docker --version)"
else
    log "Docker já instalado: $(docker --version)"
fi

# =============================================================================
# PASSO 3 — Clonar repositório
# =============================================================================
section "PASSO 3/5 — Clonando repositório"
if [ -d "$PROJECT_DIR" ]; then
    warn "Pasta $PROJECT_DIR já existe. Removendo..."
    sudo rm -rf "$PROJECT_DIR"
fi
git clone "$REPO_URL" "$PROJECT_DIR"
cat > "$PROJECT_DIR/.env" << EOF
DB_PASSWORD=financas123
SECRET_KEY=financas_prod_secret_2024
EOF
log "Repositório clonado em $PROJECT_DIR"

# =============================================================================
# PASSO 4 — Subir APENAS Homologação
# =============================================================================
section "PASSO 4/5 — Subindo ambiente de HOMOLOGAÇÃO"
cd "$PROJECT_DIR"

info "Fazendo build da imagem..."
sudo docker compose build

info "Subindo containers de Homologação..."
sudo docker compose up -d postgres_homolog

info "Aguardando PostgreSQL Homolog ficar saudável..."
sleep 10

sudo docker compose up -d app_homolog

sleep 10

info "Status dos containers:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "homolog|NAMES"
log "Ambiente de Homologação no ar!"

# =============================================================================
# PASSO 5 — Instalar GitHub Actions Runner (token automático)
# =============================================================================
section "PASSO 5/5 — Instalando GitHub Actions Runner"

info "Obtendo token do Runner via API do GitHub..."
RUNNER_TOKEN=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_PAT" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/actions/runners/registration-token" \
    | grep '"token"' | cut -d'"' -f4)

if [ -z "$RUNNER_TOKEN" ]; then
    error "Não foi possível obter o token do Runner. Verifique o PAT."
fi
log "Token obtido automaticamente!"

if [ -d "$RUNNER_DIR" ]; then
    warn "Runner já existe. Removendo instalação anterior..."
    cd "$RUNNER_DIR"
    sudo ./svc.sh stop 2>/dev/null || true
    sudo ./svc.sh uninstall 2>/dev/null || true
    cd /home/univates
    sudo rm -rf "$RUNNER_DIR"
fi

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

info "Baixando GitHub Actions Runner v$RUNNER_VERSION..."
curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
log "Runner baixado"

info "Configurando Runner..."
./config.sh \
    --url "https://github.com/$REPO_OWNER/$REPO_NAME" \
    --token "$RUNNER_TOKEN" \
    --name "vm-univates" \
    --labels "self-hosted,Linux,X64" \
    --work "_work" \
    --unattended \
    --replace

sudo ./svc.sh uninstall 2>/dev/null || true
sudo ./svc.sh install
sudo ./svc.sh start
log "Runner configurado e iniciado como serviço!"

# =============================================================================
# RESUMO FINAL
# =============================================================================
section "Bootstrap concluído!"

echo ""
echo -e "${GREEN}Homologação:${NC} ${BLUE}http://177.44.248.60:5001${NC} ✅"
echo -e "${YELLOW}Produção:${NC}    http://177.44.248.60:5000 ❌ (ainda não subiu)"
echo ""
echo -e "${GREEN}Credenciais:${NC} admin / admin123"
echo ""
echo -e "${YELLOW}Para subir a Produção, execute:${NC}"
echo -e "  ${BLUE}curl -fsSL https://raw.githubusercontent.com/FarwBr/financaspro/main/setup-prod.sh | bash${NC}"
echo ""
