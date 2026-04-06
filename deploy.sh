#!/bin/bash

# WifiPwn Deploy Script

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✔${NC}  $*"; }
info() { echo -e "  ${BLUE}◆${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
fail() { echo -e "  ${RED}✖${NC}  $*"; }
step() { printf "  ${BLUE}◆${NC}  %-38s" "$* ..."; }
done_ok()   { echo -e " ${GREEN}OK${NC}"; }
done_fail() { echo -e " ${RED}FAIL${NC}"; }

banner() {
    echo ""
    echo -e "${CYAN}${BOLD}"
    echo ' _       __ ____ ______ ____ ____  _       __ _   __ '
    echo '| |     / //  _// ____//  _// __ \| |     / // | / / '
    echo '| | /| / / / / / /_    / / / /_/ /| | /| / //  |/ /  '
    echo '| |/ |/ /_/ / / __/  _/ / / ____/ | |/ |/ // /|  /   '
    echo '|__/|__//___//_/    /___//_/      |__/|__//_/ |_/    '
    echo -e "${NC}${DIM}                       by: afsh4ck${NC}"
    echo ""
}

panel() {
    local title="$1"; shift
    local width=46
    local top="${BOLD}┌$(printf '─%.0s' $(seq 1 $width))┐${NC}"
    local bot="${BOLD}└$(printf '─%.0s' $(seq 1 $width))┘${NC}"
    echo -e "$top"
    printf "${BOLD}│${NC}  ${CYAN}${BOLD}%-${width}s${NC}${BOLD}│${NC}\n" "$title"
    echo -e "${BOLD}│$(printf ' %.0s' $(seq 1 $width))│${NC}"
    for line in "$@"; do
        printf "${BOLD}│${NC}  %-${width}s${BOLD}│${NC}\n" "$line"
    done
    echo -e "$bot"
    echo ""
}

banner

# Función para generar IP aleatoria en rango privado
generate_random_ip() {
    # Generar IP en rango 172.16.0.0/12 o 10.0.0.0/8
    local network_type=$((RANDOM % 2))
    
    if [ $network_type -eq 0 ]; then
        # Rango 10.x.x.x
        local octet2=$((RANDOM % 256))
        local octet3=$((RANDOM % 256))
        local octet4=$((RANDOM % 254 + 1))  # Evitar .0 y .255
        echo "10.${octet2}.${octet3}.${octet4}"
    else
        # Rango 172.16-31.x.x
        local octet2=$((RANDOM % 16 + 16))  # 16-31
        local octet3=$((RANDOM % 256))
        local octet4=$((RANDOM % 254 + 1))
        echo "172.${octet2}.${octet3}.${octet4}"
    fi
}

# Función para generar máscara de red aleatoria
generate_random_netmask() {
    local masks=("255.255.255.0" "255.255.0.0" "255.0.0.0")
    local idx=$((RANDOM % 3))
    echo "${masks[$idx]}"
}

# ── Modo Docker ───────────────────────────────────────────────────────
# Uso: deploy.sh docker [build|stop|logs|status|shell|clean]
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="wifipwn"
IMAGE_NAME="wifipwn:latest"

if [ "${1:-}" = "docker" ] || [ "${1:-}" = "--docker" ]; then
    shift
    CMD="${1:-run}"
    case "$CMD" in
        build)
            step "Construyendo imagen Docker"
            docker build -t "$IMAGE_NAME" "$_SCRIPT_DIR" >/dev/null 2>&1 && done_ok || { done_fail; exit 1; }
            ;;
        stop)
            step "Deteniendo WifiPwn"
            docker stop "$CONTAINER_NAME" >/dev/null 2>&1 && done_ok || { echo -e " ${YELLOW}(no estaba corriendo)${NC}"; }
            ;;
        logs)
            docker logs -f "$CONTAINER_NAME"
            ;;
        status)
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                ok "WifiPwn está ${GREEN}${BOLD}ACTIVO${NC}"
                docker ps --filter "name=$CONTAINER_NAME" --format "    {{.Status}}  {{.Ports}}"
                echo ""
                echo -e "    ${BLUE}▸${NC} Web: http://localhost:1234"
                echo -e "    ${BLUE}▸${NC} API: http://localhost:8000/docs"
            else
                fail "WifiPwn está ${RED}DETENIDO${NC}"
            fi
            ;;
        shell)
            docker exec -it "$CONTAINER_NAME" /bin/bash
            ;;
        clean)
            step "Eliminando contenedor e imagen"
            docker stop "$CONTAINER_NAME" 2>/dev/null || true
            docker rm "$CONTAINER_NAME" 2>/dev/null || true
            docker rmi "$IMAGE_NAME" 2>/dev/null || true
            done_ok
            ;;
        run|*)
            if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
                step "Construyendo imagen Docker"
                docker build -t "$IMAGE_NAME" "$_SCRIPT_DIR" >/dev/null 2>&1 && done_ok || { done_fail; exit 1; }
            fi
            docker rm "$CONTAINER_NAME" 2>/dev/null || true
            mkdir -p "$_SCRIPT_DIR/data" "$_SCRIPT_DIR/captures" "$_SCRIPT_DIR/reports" "$_SCRIPT_DIR/logs"
            step "Iniciando contenedor"
            docker run -d \
                --name "$CONTAINER_NAME" \
                --privileged \
                --cap-add=NET_ADMIN \
                --cap-add=NET_RAW \
                --cap-add=SYS_ADMIN \
                --network host \
                -v "$_SCRIPT_DIR/data:/app/data" \
                -v "$_SCRIPT_DIR/captures:/app/captures" \
                -v "$_SCRIPT_DIR/reports:/app/reports" \
                -v "$_SCRIPT_DIR/logs:/app/logs" \
                --restart unless-stopped \
                "$IMAGE_NAME" >/dev/null 2>&1 && done_ok || { done_fail; exit 1; }
            sleep 3
            echo ""
            panel "WifiPwn — Docker" \
                "▸  Web: http://localhost:1234" \
                "▸  API: http://localhost:8000/docs" \
                "" \
                "logs   → deploy.sh docker logs" \
                "stop   → deploy.sh docker stop"
            ;;
    esac
    exit 0
fi

# ── Modo nativo (host) ────────────────────────────────────────────────
# Verificar si estamos en Docker
if [ -f /.dockerenv ]; then
    IN_DOCKER=true
else
    IN_DOCKER=false
fi

# Verificar permisos de root
if [ "$EUID" -ne 0 ]; then 
    fail "Este script debe ejecutarse como root: ${BOLD}sudo bash deploy.sh${NC}"
    exit 1
fi

# Configurar interfaz eth0 con IP aleatoria
if [ "$IN_DOCKER" = true ]; then
    if ip link show eth0 &>/dev/null; then
        NEW_IP=$(generate_random_ip)
        step "Configurando eth0"
        ip addr flush dev eth0 2>/dev/null || true
        ip addr add ${NEW_IP}/24 dev eth0 2>/dev/null || true
        ip link set eth0 up 2>/dev/null || true
        done_ok
    fi
fi

# Crear directorios de datos si no existen
if [ "$IN_DOCKER" = true ]; then
    DATA_DIR="/app/data"
    CAPTURES_DIR="/app/captures"
    REPORTS_DIR="/app/reports"
    LOGS_DIR="/app/logs"
    TEMPLATES_DIR="/app/templates"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    DATA_DIR="$SCRIPT_DIR/data"
    CAPTURES_DIR="$SCRIPT_DIR/captures"
    REPORTS_DIR="$SCRIPT_DIR/reports"
    LOGS_DIR="$SCRIPT_DIR/logs"
    TEMPLATES_DIR="$SCRIPT_DIR/templates"
fi

mkdir -p "$DATA_DIR" "$CAPTURES_DIR" "$REPORTS_DIR" "$LOGS_DIR" "$TEMPLATES_DIR"

# Inicializar base de datos si no existe
DB_PATH="$DATA_DIR/wifipwn.db"
if [ ! -f "$DB_PATH" ]; then
    step "Inicializando base de datos"
    sqlite3 "$DB_PATH" <<EOF
CREATE TABLE IF NOT EXISTS networks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bssid TEXT UNIQUE NOT NULL,
    essid TEXT,
    channel INTEGER,
    security TEXT,
    cipher TEXT,
    power INTEGER,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    latitude REAL,
    longitude REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS handshakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER,
    capture_file TEXT NOT NULL,
    capture_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cracked INTEGER DEFAULT 0,
    password TEXT,
    FOREIGN KEY (network_id) REFERENCES networks(id)
);

CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    username TEXT,
    password TEXT,
    capture_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS campaign_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    network_id INTEGER,
    status TEXT DEFAULT 'pending',
    notes TEXT,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (network_id) REFERENCES networks(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS deauth_attacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER,
    client_mac TEXT,
    packets_sent INTEGER,
    attack_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (network_id) REFERENCES networks(id)
);

CREATE INDEX IF NOT EXISTS idx_networks_bssid ON networks(bssid);
CREATE INDEX IF NOT EXISTS idx_handshakes_network ON handshakes(network_id);
CREATE INDEX IF NOT EXISTS idx_credentials_date ON credentials(capture_date);

INSERT INTO audit_logs (action, details) VALUES ('Database Initialized', 'Created all tables');
EOF
    done_ok
fi

# Verificar herramientas necesarias
step "Verificando herramientas del sistema"
MISSING=""
for tool in aircrack-ng airodump-ng aireplay-ng airmon-ng hostapd dnsmasq iw; do
    command -v $tool &>/dev/null || MISSING="$MISSING $tool"
done
if [ -z "$MISSING" ]; then
    done_ok
else
    done_fail
    warn "Herramientas no encontradas:${YELLOW}$MISSING${NC}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


# ── WEB MODE: FastAPI backend + Next.js frontend ──────────────────────
echo ""

BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Check backend dir
if [ ! -d "$BACKEND_DIR" ]; then
    fail "No se encuentra $BACKEND_DIR"
    exit 1
fi

# Install Python backend deps
step "Instalando dependencias Python"
pip3 install -q -r "$BACKEND_DIR/requirements.txt" 2>/dev/null || \
    pip3 install -q --break-system-packages -r "$BACKEND_DIR/requirements.txt" 2>/dev/null || \
    python3 -m pip install -q -r "$BACKEND_DIR/requirements.txt" --break-system-packages 2>/dev/null && done_ok || done_fail

# Install Node.js frontend deps + build
if [ -d "$FRONTEND_DIR" ]; then
    if ! command -v npm &>/dev/null; then
        fail "npm no encontrado — instala Node.js >= 18:"
        info "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs"
        exit 1
    fi
    step "Instalando dependencias Node.js"
    cd "$FRONTEND_DIR" && npm install --silent 2>/dev/null && done_ok || done_fail
    step "Construyendo frontend Next.js"
    npm run build --silent 2>/dev/null && done_ok || done_fail
    cd "$SCRIPT_DIR"
fi

# Cleanup on exit
cleanup() {
    echo ""
    info "Deteniendo servicios..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait
    ok "WifiPwn detenido"
}
trap cleanup EXIT INT TERM

# Start FastAPI backend
step "Iniciando API backend"
cd "$BACKEND_DIR"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning &
BACKEND_PID=$!

# Wait for backend with curl health-check (up to 15s)
printf "  ${BLUE}◆${NC}  %-38s" "Esperando backend ..."
for i in $(seq 1 15); do
    sleep 1
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        done_fail
        fail "Backend cerrado inesperadamente. Diagnóstico:"
        echo -e "    ${DIM}cd '$BACKEND_DIR' && python3 -m uvicorn main:app --port 8000${NC}"
        exit 1
    fi
    if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        done_ok
        break
    fi
    printf "."
done
if ! curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    echo ""
    warn "Backend no responde. Comprueba: ${DIM}ss -tlnp | grep 8000${NC}"
fi

# Start Next.js frontend
if [ -d "$FRONTEND_DIR" ]; then
    step "Iniciando frontend Next.js"
    cd "$FRONTEND_DIR"
    npm start &>/dev/null &
    FRONTEND_PID=$!
    sleep 2
    done_ok
fi

echo ""
panel "WifiPwn — Listo" \
    "▸  Web: http://localhost:1234" \
    "▸  API: http://localhost:8000/docs" \
    "" \
    "Ctrl+C para detener"

wait
