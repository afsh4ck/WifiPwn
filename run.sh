#!/bin/bash

# WifiPwn Docker Runner Script
# Facilita la ejecución de WifiPwn en Docker con X11 forwarding

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="wifipwn"
IMAGE_NAME="wifipwn:latest"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${CYAN}"
    echo ' _       __ ____ ______ ____ ____  _       __ _   __ '
    echo '| |     / //  _// ____//  _// __ \| |     / // | / / '
    echo '| | /| / / / / / /_    / / / /_/ /| | /| / //  |/ /  '
    echo '| |/ |/ /_/ / / __/  _/ / / ____/ | |/ |/ // /|  /   '
    echo '|__/|__//___//_/    /___//_/      |__/|__//_/ |_/    '
    echo '                                                     '
    echo -e "${BLUE}                    by:afsh4ck${NC}"
    echo ""
}

print_usage() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos:"
    echo "  build       - Construir la imagen Docker"
    echo "  run         - Ejecutar WifiPwn (construye si es necesario)"
    echo "  stop        - Detener el contenedor"
    echo "  restart     - Reiniciar el contenedor"
    echo "  shell       - Abrir shell en el contenedor"
    echo "  logs        - Ver logs del contenedor"
    echo "  clean       - Limpiar contenedores e imagenes"
    echo "  status      - Estado del contenedor"
    echo "  update      - Actualizar imagen y reiniciar"
    echo "  help        - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 run              # Ejecutar WifiPwn"
    echo "  $0 shell            # Abrir shell para debugging"
    echo "  $0 logs -f          # Ver logs en tiempo real"
}

check_x11() {
    if [ -z "$DISPLAY" ]; then
        echo -e "${YELLOW}Advertencia: DISPLAY no configurado${NC}"
        export DISPLAY=:0
        echo "Configurando DISPLAY=:0"
    fi
    
    # Permitir conexiones X11 desde Docker
    if command -v xhost > /dev/null 2>&1; then
        xhost +local:docker 2>/dev/null || true
    fi
}

build_image() {
    echo -e "${BLUE}[*] Construyendo imagen Docker...${NC}"
    cd "$SCRIPT_DIR"
    docker build -t "$IMAGE_NAME" .
    echo -e "${GREEN}[+] Imagen construida exitosamente${NC}"
}

run_container() {
    check_x11
    
    # Verificar si ya existe un contenedor
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${YELLOW}[*] Contenedor existente encontrado${NC}"
        
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo -e "${GREEN}[+] WifiPwn ya esta ejecutandose${NC}"
            echo "    Accede a la aplicacion en la ventana X11"
            return 0
        else
            echo -e "${BLUE}[*] Iniciando contenedor existente...${NC}"
            docker start "$CONTAINER_NAME"
            return 0
        fi
    fi
    
    # Verificar si la imagen existe
    if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
        echo -e "${YELLOW}[!] Imagen no encontrada, construyendo...${NC}"
        build_image
    fi
    
    echo -e "${BLUE}[*] Iniciando WifiPwn en Docker...${NC}"
    
    # Crear directorios si no existen
    mkdir -p "$SCRIPT_DIR/data"
    mkdir -p "$SCRIPT_DIR/captures"
    mkdir -p "$SCRIPT_DIR/reports"
    mkdir -p "$SCRIPT_DIR/logs"
    mkdir -p "$SCRIPT_DIR/config"
    
    # Ejecutar contenedor
    docker run -d \
        --name "$CONTAINER_NAME" \
        --privileged \
        --cap-add=NET_ADMIN \
        --cap-add=NET_RAW \
        --cap-add=SYS_ADMIN \
        --network host \
        -e DISPLAY="$DISPLAY" \
        -e QT_X11_NO_MITSHM=1 \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v "$SCRIPT_DIR/data:/app/data" \
        -v "$SCRIPT_DIR/captures:/app/captures" \
        -v "$SCRIPT_DIR/reports:/app/reports" \
        -v "$SCRIPT_DIR/logs:/app/logs" \
        -v "$SCRIPT_DIR/config:/app/config" \
        -v "$SCRIPT_DIR/templates:/app/templates" \
        --device /dev/net/tun \
        --restart unless-stopped \
        "$IMAGE_NAME"
    
    echo -e "${GREEN}[+] WifiPwn iniciado correctamente${NC}"
    echo ""
    echo -e "${BLUE}Informacion:${NC}"
    echo "  - Contenedor: $CONTAINER_NAME"
    echo "  - Datos: $SCRIPT_DIR/data"
    echo "  - Capturas: $SCRIPT_DIR/captures"
    echo "  - Logs: docker logs -f $CONTAINER_NAME"
    echo ""
    echo "La aplicacion deberia aparecer en una ventana X11"
}

stop_container() {
    echo -e "${BLUE}[*] Deteniendo contenedor...${NC}"
    docker stop "$CONTAINER_NAME" 2>/dev/null || echo -e "${YELLOW}Contenedor no ejecutandose${NC}"
    echo -e "${GREEN}[+] Contenedor detenido${NC}"
}

restart_container() {
    stop_container
    sleep 2
    run_container
}

open_shell() {
    echo -e "${BLUE}[*] Abriendo shell en el contenedor...${NC}"
    docker exec -it "$CONTAINER_NAME" /bin/bash
}

show_logs() {
    echo -e "${BLUE}[*] Logs del contenedor:${NC}"
    docker logs "$@" "$CONTAINER_NAME"
}

clean_docker() {
    echo -e "${YELLOW}[!] Esto eliminara el contenedor y la imagen${NC}"
    read -p "¿Continuar? (s/N): " confirm
    
    if [[ $confirm =~ ^[Ss]$ ]]; then
        echo -e "${BLUE}[*] Limpiando...${NC}"
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
        docker rmi "$IMAGE_NAME" 2>/dev/null || true
        echo -e "${GREEN}[+] Limpieza completada${NC}"
    else
        echo "Cancelado"
    fi
}

show_status() {
    echo -e "${BLUE}Estado de WifiPwn:${NC}"
    echo ""
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${GREEN}Estado: EJECUTANDO${NC}"
        echo ""
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        echo -e "${BLUE}Estadisticas:${NC}"
        docker exec "$CONTAINER_NAME" sqlite3 /app/data/wifipwn.db "SELECT 'Redes: ' || COUNT(*) FROM networks;" 2>/dev/null || echo "  Base de datos no inicializada"
    else
        echo -e "${RED}Estado: DETENIDO${NC}"
    fi
}

update_image() {
    echo -e "${BLUE}[*] Actualizando WifiPwn...${NC}"
    stop_container
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    docker rmi "$IMAGE_NAME" 2>/dev/null || true
    build_image
    run_container
}

# Main
case "${1:-run}" in
    build)
        build_image
        ;;
    run)
        print_banner
        run_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    shell)
        open_shell
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    clean)
        clean_docker
        ;;
    status)
        show_status
        ;;
    update)
        update_image
        ;;
    help|--help|-h)
        print_banner
        print_usage
        ;;
    *)
        echo -e "${RED}Comando desconocido: $1${NC}"
        print_usage
        exit 1
        ;;
esac
