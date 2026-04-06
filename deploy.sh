#!/bin/bash

# WifiPwn Deploy Script
# Configura IP aleatoria en eth0 e inicia la aplicación

set -e

echo ""
echo ' _       __ ____ ______ ____ ____  _       __ _   __ '
echo '| |     / //  _// ____//  _// __ \| |     / // | / / '
echo '| | /| / / / / / /_    / / / /_/ /| | /| / //  |/ /  '
echo '| |/ |/ /_/ / / __/  _/ / / ____/ | |/ |/ // /|  /   '
echo '|__/|__//___//_/    /___//_/      |__/|__//_/ |_/    '
echo '                                                     '
echo '                    by:afsh4ck'
echo ""
echo "========================================="
echo "      WifiPwn - Deployment Script"
echo "========================================="
echo ""

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

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'

if [ "${1:-}" = "docker" ] || [ "${1:-}" = "--docker" ]; then
    shift
    CMD="${1:-run}"
    case "$CMD" in
        build)
            echo -e "${BLUE}[*] Construyendo imagen Docker...${NC}"
            docker build -t "$IMAGE_NAME" "$_SCRIPT_DIR"
            echo -e "${GREEN}[+] Imagen lista${NC}"
            ;;
        stop)
            echo -e "${BLUE}[*] Deteniendo WifiPwn...${NC}"
            docker stop "$CONTAINER_NAME" 2>/dev/null && echo -e "${GREEN}[+] Detenido${NC}" || echo -e "${YELLOW}No estaba en ejecución${NC}"
            ;;
        logs)
            docker logs -f "$CONTAINER_NAME"
            ;;
        status)
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                echo -e "${GREEN}[+] WifiPwn está EJECUTANDO${NC}"
                docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
                echo -e "\n    Interfaz web: http://localhost:1234\n    API docs:     http://localhost:8000/docs"
            else
                echo -e "${RED}[!] WifiPwn está DETENIDO${NC}"
            fi
            ;;
        shell)
            docker exec -it "$CONTAINER_NAME" /bin/bash
            ;;
        clean)
            echo -e "${YELLOW}[!] Eliminando contenedor e imagen...${NC}"
            docker stop "$CONTAINER_NAME" 2>/dev/null || true
            docker rm "$CONTAINER_NAME" 2>/dev/null || true
            docker rmi "$IMAGE_NAME" 2>/dev/null || true
            echo -e "${GREEN}[+] Limpieza completada${NC}"
            ;;
        run|*)
            if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
                echo -e "${YELLOW}[!] Imagen no encontrada, construyendo...${NC}"
                docker build -t "$IMAGE_NAME" "$_SCRIPT_DIR"
            fi
            docker rm "$CONTAINER_NAME" 2>/dev/null || true
            mkdir -p "$_SCRIPT_DIR/data" "$_SCRIPT_DIR/captures" "$_SCRIPT_DIR/reports" "$_SCRIPT_DIR/logs"
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
                "$IMAGE_NAME"
            sleep 3
            echo ""
            echo -e "${GREEN}=========================================${NC}"
            echo -e "${GREEN}  WifiPwn iniciado con Docker${NC}"
            echo -e "${GREEN}  Interfaz web: http://localhost:1234${NC}"
            echo -e "${GREEN}  API docs:     http://localhost:8000/docs${NC}"
            echo -e "${GREEN}=========================================${NC}"
            echo ""
            echo "  deploy.sh docker logs   → ver logs"
            echo "  deploy.sh docker stop   → detener"
            echo "  deploy.sh docker status → estado"
            echo ""
            ;;
    esac
    exit 0
fi

# ── Modo nativo (host) ────────────────────────────────────────────────
# Verificar si estamos en Docker
if [ -f /.dockerenv ]; then
    echo "[*] Ejecutando dentro de contenedor Docker"
    IN_DOCKER=true
else
    echo "[*] Ejecutando en sistema host"
    IN_DOCKER=false
fi

# Configurar interfaz eth0 con IP aleatoria
echo "[*] Configurando interfaz de red..."

if [ "$IN_DOCKER" = true ]; then
    # En Docker, configurar eth0 si existe
    if ip link show eth0 &>/dev/null; then
        # Generar IP aleatoria
        NEW_IP=$(generate_random_ip)
        NETMASK=$(generate_random_netmask)
        
        echo "[*] Asignando IP aleatoria: $NEW_IP/$NETMASK"
        
        # Configurar interfaz
        ip addr flush dev eth0 2>/dev/null || true
        ip addr add ${NEW_IP}/24 dev eth0 2>/dev/null || true
        ip link set eth0 up 2>/dev/null || true
        
        echo "[+] IP configurada: $NEW_IP"
    else
        echo "[!] Interfaz eth0 no encontrada"
    fi
else
    # En host, solo mostrar información
    echo "[*] Interfaz eth0:"
    ip addr show eth0 2>/dev/null || echo "    No disponible"
fi

# Verificar permisos de root
if [ "$EUID" -ne 0 ]; then 
    echo "[!] Este script debe ejecutarse como root (sudo)"
    exit 1
fi

# Crear directorios de datos si no existen
echo "[*] Creando directorios de datos..."

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

mkdir -p "$DATA_DIR"
mkdir -p "$CAPTURES_DIR"
mkdir -p "$REPORTS_DIR"
mkdir -p "$LOGS_DIR"
mkdir -p "$TEMPLATES_DIR"

# Inicializar base de datos si no existe
DB_PATH="$DATA_DIR/wifipwn.db"
if [ ! -f "$DB_PATH" ]; then
    echo "[*] Inicializando base de datos en $DB_PATH..."
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
    echo "[+] Base de datos inicializada"
else
    echo "[*] Base de datos existente encontrada"
fi

# Verificar herramientas necesarias
echo "[*] Verificando herramientas..."
TOOLS="aircrack-ng airodump-ng aireplay-ng airmon-ng hostapd dnsmasq iw"
for tool in $TOOLS; do
    if command -v $tool &> /dev/null; then
        echo "    [+] $tool: OK"
    else
        echo "    [!] $tool: NO ENCONTRADO"
    fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


# ── WEB MODE: FastAPI backend + Next.js frontend ──────────────────────
echo ""
echo "========================================="
echo "   Iniciando WifiPwn Web (API + Next.js)"
echo "========================================="
echo ""

BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Check backend dir
if [ ! -d "$BACKEND_DIR" ]; then
    echo "[!] No se encuentra $BACKEND_DIR"
    exit 1
fi

# Install Python backend deps
echo "[*] Instalando dependencias Python del backend..."
pip3 install -q -r "$BACKEND_DIR/requirements.txt"

# Install Node.js frontend deps
if [ -d "$FRONTEND_DIR" ]; then
    echo "[*] Instalando dependencias Node.js del frontend..."
    cd "$FRONTEND_DIR"
    if ! command -v npm &>/dev/null; then
        echo "[!] npm no encontrado. Instala Node.js >= 18"
        echo "    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -"
        echo "    apt-get install -y nodejs"
        exit 1
    fi
    npm install --silent
    echo "[*] Construyendo frontend Next.js..."
    npm run build
    cd "$SCRIPT_DIR"
fi

# Cleanup on exit
cleanup() {
    echo ""
    echo "[*] Deteniendo servicios..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait
    echo "[+] WifiPwn detenido"
}
trap cleanup EXIT INT TERM

# Start FastAPI backend
echo "[*] Iniciando API backend (puerto 8000)..."
cd "$BACKEND_DIR"
sudo python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "[!] Error: el backend no pudo iniciarse"
    exit 1
fi
echo "[+] Backend API listo en http://localhost:8000"

# Start Next.js frontend
if [ -d "$FRONTEND_DIR" ]; then
    echo "[*] Iniciando frontend Next.js (puerto 1234)..."
    cd "$FRONTEND_DIR"
    npm start &
    FRONTEND_PID=$!
    sleep 2
    echo "[+] Frontend listo en http://localhost:1234"
fi

echo ""
echo "========================================="
echo "  WifiPwn Web Interface"
echo "  => http://localhost:1234"
echo "  => API: http://localhost:8000/docs"
echo "========================================="
echo ""
echo "Presiona Ctrl+C para detener todos los servicios"
echo ""

wait
