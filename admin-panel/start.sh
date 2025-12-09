#!/bin/bash
#
# KaliRoot Admin Panel - Start Script
# Inicia ambos servidores con un solo comando
#
# Uso:
#   ./start.sh          # Inicia ambos servidores
#   ./start.sh web      # Solo servidor web (puerto 8080)
#   ./start.sh api      # Solo API server (puerto 8081)
#   ./start.sh stop     # Detiene todos los servidores
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Función para mostrar banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║          🛡️  KaliRoot Admin Panel                 ║"
    echo "╚═══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Función para detener servidores
stop_servers() {
    echo -e "${YELLOW}🛑 Deteniendo servidores...${NC}"
    
    # Matar servidor web (puerto 8080)
    fuser -k 8080/tcp 2>/dev/null
    
    # Matar API server (puerto 8081)
    fuser -k 8081/tcp 2>/dev/null
    pkill -f "api_server.py" 2>/dev/null
    
    echo -e "${GREEN}✅ Servidores detenidos${NC}"
}

# Función para verificar puertos
check_ports() {
    local port=$1
    if lsof -i :$port >/dev/null 2>&1; then
        echo -e "${RED}⚠️  Puerto $port ya está en uso${NC}"
        return 1
    fi
    return 0
}

# Función para iniciar servidor web
start_web() {
    echo -e "${BLUE}🌐 Iniciando servidor web en puerto 8080...${NC}"
    
    if ! check_ports 8080; then
        echo -e "${YELLOW}   Liberando puerto 8080...${NC}"
        fuser -k 8080/tcp 2>/dev/null
        sleep 1
    fi
    
    python3 -m http.server 8080 &
    WEB_PID=$!
    echo -e "${GREEN}✅ Servidor web iniciado (PID: $WEB_PID)${NC}"
    echo -e "${CYAN}   📍 http://localhost:8080${NC}"
}

# Función para iniciar API server
start_api() {
    echo -e "${BLUE}🔌 Iniciando API server en puerto 8081...${NC}"
    
    # Verificar que existe el venv
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}   Creando entorno virtual...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        pip install telethon fastapi uvicorn aiofiles
    fi
    
    if ! check_ports 8081; then
        echo -e "${YELLOW}   Liberando puerto 8081...${NC}"
        fuser -k 8081/tcp 2>/dev/null
        sleep 1
    fi
    
    source venv/bin/activate
    python3 api_server.py &
    API_PID=$!
    echo -e "${GREEN}✅ API server iniciado (PID: $API_PID)${NC}"
    echo -e "${CYAN}   📍 http://localhost:8081/docs${NC}"
}

# Función principal
main() {
    show_banner
    
    case "$1" in
        stop)
            stop_servers
            ;;
        web)
            start_web
            echo ""
            echo -e "${GREEN}🚀 Servidor web listo!${NC}"
            echo -e "   Abre ${CYAN}http://localhost:8080${NC} en tu navegador"
            echo ""
            echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}"
            wait
            ;;
        api)
            start_api
            echo ""
            echo -e "${GREEN}🚀 API server listo!${NC}"
            echo ""
            echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}"
            wait
            ;;
        *)
            # Iniciar ambos
            start_web
            sleep 1
            start_api
            
            echo ""
            echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
            echo -e "${GREEN}🚀 Admin Panel listo!${NC}"
            echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
            echo ""
            echo -e "   🌐 Admin Panel:  ${CYAN}http://localhost:8080${NC}"
            echo -e "   🔌 API Docs:     ${CYAN}http://localhost:8081/docs${NC}"
            echo ""
            echo -e "${YELLOW}Presiona Ctrl+C para detener ambos servidores${NC}"
            echo ""
            
            # Esperar a que terminen
            trap "stop_servers; exit 0" SIGINT SIGTERM
            wait
            ;;
    esac
}

main "$@"
