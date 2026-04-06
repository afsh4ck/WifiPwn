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
mkdir -p /app/data
mkdir -p /app/captures
mkdir -p /app/reports
mkdir -p /app/logs
mkdir -p /app/templates

# Inicializar base de datos si no existe
DB_PATH="/app/data/wifipwn.db"
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

# Configurar X11 si está disponible
if [ -n "$DISPLAY" ]; then
    echo "[*] Display X11 detectado: $DISPLAY"
    xhost +local:docker 2>/dev/null || true
fi

# Iniciar la aplicación
echo ""
echo "========================================="
echo "      Iniciando WifiPwn GUI"
echo "========================================="
echo ""

cd /app/wifipwn

# Ejecutar con Python
exec python3 main.py "$@"
