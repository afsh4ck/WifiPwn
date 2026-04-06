# WifiPwn — Herramienta de Pentesting WiFi

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
+----------------------------------------------------------+
|                   Cliente (Navegador)                    |
|            Next.js 14  ->  http://localhost:1234         |
+-------------------------+--------------------------------+
                          |  HTTP /api/* + WebSocket /ws
+-------------------------v--------------------------------+
|                    FastAPI Backend                       |
|              Python  ->  http://localhost:8000           |
|   /api/dashboard  /api/scanner  /api/handshake  ...     |
+-------------------------+--------------------------------+
                          |  subprocess / threads
+-------------------------v--------------------------------+
|          Herramientas del sistema (Kali Linux)           |
|   aircrack-ng  airodump-ng  aireplay-ng  airmon-ng      |
|   hostapd  dnsmasq  iw  macchanger                      |
+----------------------------------------------------------+
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

### Despliegue automático

El script `deploy.sh` instala dependencias, construye el frontend y lanza ambos servicios:

```bash
chmod +x deploy.sh
sudo bash deploy.sh
```

Una vez en marcha:
- **Interfaz web**: http://localhost:1234
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
npm start        # producción en puerto 1234
# o:
npm run dev      # desarrollo con hot-reload
```

---

### Despliegue con Docker

```bash
# Iniciar (construye la imagen si es necesario)
sudo bash deploy.sh docker

# Comandos disponibles
sudo bash deploy.sh docker build   # Construir imagen
sudo bash deploy.sh docker stop    # Detener
sudo bash deploy.sh docker logs    # Ver logs en tiempo real
sudo bash deploy.sh docker status  # Estado del contenedor
sudo bash deploy.sh docker shell   # Shell en el contenedor
sudo bash deploy.sh docker clean   # Limpiar contenedor e imagen
```

---

## Flujo de trabajo típico

### 1. Capturar y crackear un handshake

```
1. Interfaces -> Activar modo monitor en wlan0

2. Escáner -> Seleccionar wlan0mon -> Iniciar escaneo
   Las redes aparecen en tiempo real

3. Handshake -> Seleccionar BSSID/canal -> Iniciar captura
   -> "Enviar deauth" para forzar reconexión
   -> Esperar "HANDSHAKE CAPTURADO" [OK]

4. Cracking -> Seleccionar el .cap -> Elegir wordlist
   -> Output en streaming en el terminal web

5. Dashboard -> Verificar estadísticas actualizadas
```

### 2. Evil Portal (Rogue AP)

```
1. Evil Portal -> Configurar SSID, canal e interfaz

2. Iniciar portal -> hostapd + dnsmasq se inician

3. Las credenciales aparecen en tiempo real vía WebSocket

4. Detener portal -> Exportar credenciales
```

---

## Estructura del proyecto

```
WifiPwn/
+-- backend/                    # API FastAPI (Python)
|   +-- main.py                 # Punto de entrada FastAPI
|   +-- requirements.txt
|   +-- core/
|   |   +-- command_runner.py   # Ejecutor de comandos con threads
|   |   +-- database.py         # SQLite
|   |   +-- wifi_manager.py     # Operaciones WiFi
|   |   +-- config.py
|   |   +-- utils.py
|   +-- api/
|       +-- websocket.py        # Gestor WebSocket con broadcast
|       +-- routes/
|           +-- dashboard.py
|           +-- interfaces.py
|           +-- scanner.py
|           +-- handshake.py
|           +-- cracking.py
|           +-- deauth.py
|           +-- evil_portal.py
|           +-- campaigns.py
|
+-- frontend/                   # UI Next.js 14 (TypeScript)
|   +-- app/                    # App Router
|   |   +-- layout.tsx
|   |   +-- page.tsx            # Dashboard
|   |   +-- interfaces/page.tsx
|   |   +-- scanner/page.tsx
|   |   +-- handshake/page.tsx
|   |   +-- cracking/page.tsx
|   |   +-- deauth/page.tsx
|   |   +-- evil-portal/page.tsx
|   |   +-- campaigns/page.tsx
|   +-- components/
|   |   +-- layout/             # Sidebar, Header
|   |   +-- ui/                 # Terminal, StatsCard, Badge, NetworkTable
|   +-- lib/
|   |   +-- api.ts              # Cliente REST tipado
|   |   +-- websocket.ts        # Hook useWebSocket con reconexión auto
|   +-- types/index.ts          # Interfaces TypeScript
|
+-- deploy.sh                   # Script de arranque
+-- run.sh                      # Wrapper Docker
+-- docker-compose.yml
+-- Dockerfile
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

> **ADVERTENCIA: USO EXCLUSIVO EN ENTORNOS AUTORIZADOS**
>
> Esta herramienta está diseñada para auditorías de seguridad WiFi autorizadas y fines educativos. El uso en redes sin permiso explícito del propietario es **ilegal** y puede conllevar responsabilidades penales.
>
> El autor **no se responsabiliza** del uso indebido. El usuario asume toda la responsabilidad legal.

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