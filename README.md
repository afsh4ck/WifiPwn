# WifiPwn â€” Herramienta de Pentesting WiFi

```
 _       __ ____ ______ ____ ____  _       __ _   __ 
| |     / //  _// ____//  _// __ \| |     / // | / / 
| | /| / / / / / /_    / / / /_/ /| | /| / //  |/ /  
| |/ |/ /_/ / / __/  _/ / / ____/ | |/ |/ // /|  /   
|__/|__//___//_/    /___//_/      |__/|__//_/ |_/    
                                                     
                    by:afsh4ck
```

WifiPwn es una plataforma completa de auditoría WiFi con una interfaz web moderna construida sobre **FastAPI + Next.js 14**. Diseñada para Kali Linux con antenas WiFi externas compatibles con modo monitor e inyección de paquetes.

## Características

| Módulo | Descripción |
|---|---|
| **Dashboard** | Estadísticas en tiempo real con log de actividad vía WebSocket |
| **Interfaces** | Gestión de interfaces WiFi, modo monitor, cambio de MAC aleatoria |
| **Escáner** | Descubrimiento en vivo de redes WiFi con actualizaciones WebSocket |
| **Handshake** | Captura de handshakes WPA/WPA2 + deauth integrado |
| **Cracking** | Cracking con aircrack-ng/hashcat con output en tiempo real |
| **Deauth** | Ataques de deautenticación punto a punto o broadcast |
| **Evil Portal** | Rogue AP con portal cautivo y captura de credenciales en vivo |
| **Campañas** | Gestión de auditorías, objetivos y generación de reportes HTML |

---

## Arquitectura

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                     Cliente (Navegador)                  â”‚
â”‚              Next.js 14 â†’ http://localhost:3000          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                       â”‚ HTTP /api/* + WebSocket /ws
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                  FastAPI Backend                          â”‚
â”‚              Python â†’ http://localhost:8000              â”‚
â”‚   /api/dashboard  /api/scanner  /api/handshake  ...     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                       â”‚ subprocess / threads
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚         Herramientas del sistema (Kali Linux)            â”‚
â”‚   aircrack-ng  airodump-ng  aireplay-ng  airmon-ng      â”‚
â”‚   hostapd  dnsmasq  iw  macchanger                      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Comunicación en tiempo real:** Las páginas de escaneo, cracking y handshake reciben actualizaciones instantáneas vía WebSocket (`ws://localhost:8000/ws`) sin necesidad de refrescar la página.

---

## Requisitos

- **OS**: Kali Linux (recomendado) o cualquier distro con las herramientas de aircrack-ng
- **Hardware**: Antena WiFi con soporte de modo monitor e inyección de paquetes
- **Software**:
  - Python 3.10+
  - Node.js 18+ y npm
  - Paquetes de sistema: `aircrack-ng`, `hostapd`, `dnsmasq`, `iw`, `macchanger`

---

## Instalación y Despliegue

### Clonar el repositorio

```bash
git clone https://github.com/afsh4ck/WifiPwn.git
cd WifiPwn
```

### Instalar herramientas del sistema

```bash
sudo apt update && sudo apt install -y \
    aircrack-ng \
    hostapd \
    dnsmasq \
    iw \
    macchanger \
    nodejs \
    npm
```

### Despliegue automático (modo web)

El script `deploy.sh` instala dependencias, construye el frontend y lanza ambos servicios:

```bash
chmod +x deploy.sh
sudo bash deploy.sh
```

Una vez en marcha:
- **Interfaz web**: http://localhost:3000
- **API REST + Docs**: http://localhost:8000/docs

Para detener, presiona `Ctrl+C`. El script limpia todos los procesos automáticamente.

---

### Despliegue manual paso a paso

#### 1. Backend (FastAPI)

```bash
cd backend
pip3 install -r requirements.txt
sudo python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

#### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run build
npm start        # producción en puerto 3000
# o:
npm run dev      # desarrollo con hot-reload
```

---

### Modo legacy (GUI PyQt5)

Si prefieres la interfaz gráfica original PyQt5:

```bash
# Requiere entorno gráfico (X11)
sudo bash deploy.sh --legacy
```

---

### Despliegue con Docker

```bash
chmod +x run.sh
./run.sh run

# Comandos disponibles
./run.sh build      # Construir imagen
./run.sh run        # Ejecutar
./run.sh stop       # Detener
./run.sh shell      # Shell en el contenedor
./run.sh logs       # Ver logs
./run.sh clean      # Limpiar contenedor e imagen
```

O con Docker Compose:

```bash
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

---

## Flujo de trabajo típico

### 1. Capturar y crackear un handshake

```
1. Interfaces â†’ Activar modo monitor en wlan0

2. Escáner â†’ Seleccionar wlan0mon â†’ Iniciar escaneo
   Las redes aparecen en tiempo real

3. Handshake â†’ Seleccionar BSSID/canal â†’ Iniciar captura
   â†’ "Enviar deauth" para forzar reconexión
   â†’ Esperar "HANDSHAKE CAPTURADO" âœ“

4. Cracking â†’ Seleccionar el .cap â†’ Elegir wordlist
   â†’ Output en streaming en el terminal web

5. Dashboard â†’ Verificar estadísticas actualizadas
```

### 2. Evil Portal (Rogue AP)

```
1. Evil Portal â†’ Configurar SSID, canal e interfaz

2. Iniciar portal â†’ hostapd + dnsmasq se inician

3. Las credenciales aparecen en tiempo real vía WebSocket

4. Detener portal â†’ Exportar credenciales
```

---

## Estructura del proyecto

```
WifiPwn/
â”œâ”€â”€ backend/                    # API FastAPI (Python)
â”‚   â”œâ”€â”€ main.py                 # Punto de entrada FastAPI
â”‚   â”œâ”€â”€ requirements.txt
â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”œâ”€â”€ command_runner.py   # Ejecutor de comandos con threads
â”‚   â”‚   â”œâ”€â”€ database.py         # SQLite
â”‚   â”‚   â”œâ”€â”€ wifi_manager.py     # Operaciones WiFi
â”‚   â”‚   â”œâ”€â”€ config.py
â”‚   â”‚   â””â”€â”€ utils.py
â”‚   â””â”€â”€ api/
â”‚       â”œâ”€â”€ websocket.py        # Gestor WebSocket con broadcast
â”‚       â””â”€â”€ routes/
â”‚           â”œâ”€â”€ dashboard.py
â”‚           â”œâ”€â”€ interfaces.py
â”‚           â”œâ”€â”€ scanner.py
â”‚           â”œâ”€â”€ handshake.py
â”‚           â”œâ”€â”€ cracking.py
â”‚           â”œâ”€â”€ deauth.py
â”‚           â”œâ”€â”€ evil_portal.py
â”‚           â””â”€â”€ campaigns.py
â”‚
â”œâ”€â”€ frontend/                   # UI Next.js 14 (TypeScript)
â”‚   â”œâ”€â”€ app/                    # App Router
â”‚   â”‚   â”œâ”€â”€ layout.tsx
â”‚   â”‚   â”œâ”€â”€ page.tsx            # Dashboard
â”‚   â”‚   â”œâ”€â”€ interfaces/page.tsx
â”‚   â”‚   â”œâ”€â”€ scanner/page.tsx
â”‚   â”‚   â”œâ”€â”€ handshake/page.tsx
â”‚   â”‚   â”œâ”€â”€ cracking/page.tsx
â”‚   â”‚   â”œâ”€â”€ deauth/page.tsx
â”‚   â”‚   â”œâ”€â”€ evil-portal/page.tsx
â”‚   â”‚   â””â”€â”€ campaigns/page.tsx
â”‚   â”œâ”€â”€ components/
â”‚   â”‚   â”œâ”€â”€ layout/             # Sidebar, Header
â”‚   â”‚   â””â”€â”€ ui/                 # Terminal, StatsCard, Badge, NetworkTable
â”‚   â”œâ”€â”€ lib/
â”‚   â”‚   â”œâ”€â”€ api.ts              # Cliente REST tipado
â”‚   â”‚   â””â”€â”€ websocket.ts        # Hook useWebSocket con reconexión auto
â”‚   â””â”€â”€ types/index.ts          # Interfaces TypeScript
â”‚
â”œâ”€â”€ wifipwn/                    # GUI PyQt5 (legacy)
â”‚
â”œâ”€â”€ deploy.sh                   # Script principal (web + --legacy)
â”œâ”€â”€ run.sh                      # Wrapper Docker
â”œâ”€â”€ docker-compose.yml
â””â”€â”€ Dockerfile
```

---

## API Reference

Documentación Swagger completa en **http://localhost:8000/docs**

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado del servicio |
| GET | `/api/dashboard/stats` | Estadísticas globales |
| GET | `/api/interfaces` | Listar interfaces WiFi |
| POST | `/api/interfaces/monitor/enable` | Activar modo monitor |
| POST | `/api/scanner/start` | Iniciar airodump-ng |
| POST | `/api/handshake/start` | Iniciar captura |
| POST | `/api/handshake/deauth` | Enviar deauth |
| POST | `/api/cracking/start` | Iniciar aircrack-ng |
| POST | `/api/deauth/send` | Ataque deauth |
| POST | `/api/evil-portal/start` | Iniciar Rogue AP |
| GET | `/api/evil-portal/credentials` | Credenciales capturadas |
| GET/POST | `/api/campaigns` | CRUD campañas |
| WS | `/ws` | Stream de eventos en tiempo real |

### Eventos WebSocket

```typescript
{ type: 'log',                 data: { level, message } }
{ type: 'scan_update',         data: { networks: Network[] } }
{ type: 'command_output',      data: { cmd_id, line } }
{ type: 'handshake_detected',  data: { bssid } }
{ type: 'credential_captured', data: { username, password } }
```

---

## Resolución de problemas

### El backend no arranca
```bash
# Verificar permisos root
sudo python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# Ver si el puerto está en uso
ss -tlnp | grep 8000
```

### El frontend no conecta con la API
```bash
# Verificar que el backend está en marcha
curl http://localhost:8000/api/health
```

### WebSocket desconectado
El frontend reintenta la conexión cada 3 segundos automáticamente. Si persiste, verifica que el backend esté corriendo.

### Interface not found / no monitor mode
```bash
sudo airmon-ng check kill
sudo airmon-ng start wlan0
```

### "Operation not permitted"
El backend requiere **permisos de root** para interactuar con interfaces WiFi. Usar `sudo`.

---

## Aviso Legal

**âš ï¸ USO EXCLUSIVO EN ENTORNOS AUTORIZADOS**

Esta herramienta está diseñada para auditorías de seguridad WiFi autorizadas y fines educativos. El uso en redes sin permiso explícito del propietario es **ilegal** y puede conllevar responsabilidades penales.

El autor **no se responsabiliza** del uso indebido. El usuario asume toda la responsabilidad legal.

---

## Licencia

MIT License © 2024 afsh4ck

---

## Autor

**afsh4ck** — [@afsh4ck](https://github.com/afsh4ck)

---

## Agradecimientos

- Aircrack-ng team
- Kali Linux team
- Comunidad de seguridad informática
