# WifiPwn - Herramienta de Pentesting WiFi

```
 _       __ ____ ______ ____ ____  _       __ _   __ 
| |     / //  _// ____//  _// __ \| |     / // | / / 
| | /| / / / / / /_    / / / /_/ /| | /| / //  |/ /  
| |/ |/ /_/ / / __/  _/ / / ____/ | |/ |/ // /|  /   
|__/|__//___//_/    /___//_/      |__/|__//_/ |_/    
                                                     
                    by:afsh4ck
```

WifiPwn es una herramienta completa de pentesting WiFi con interfaz gráfica de usuario (GUI) desarrollada en Python con PyQt5. Está diseñada para ejecutarse en Kali Linux y aprovechar antenas WiFi externas compatibles con modo monitor e inyección de paquetes.

## Características Principales

- **Dashboard**: Estadísticas en tiempo real, gestión y limpieza de datos
- **Base de Datos SQLite**: Almacenamiento persistente de redes, handshakes y credenciales
- **Panel de Control de Interfaces**: Gestión de interfaces WiFi, activación/desactivación de modo monitor
- **Escaneo de Redes**: Descubrimiento de redes WiFi con información detallada
- **Captura de Handshake**: Captura de handshakes WPA/WPA2 con detección automática
- **Cracking**: Cracking de handshakes usando aircrack-ng o hashcat
- **Deautenticación**: Envío de paquetes de deautenticación
- **Evil Portal**: Creación de puntos de acceso falsos con portal cautivo
- **Campañas de Auditoría**: Gestión de campañas y generación de reportes
- **Tema Oscuro/Claro**: Interfaz personalizable
- **Docker**: Soporte completo para ejecución en contenedores con IP aleatoria

---

## Guía de Despliegue y Uso

### Opción 1: Despliegue con Docker (Recomendado)

#### Requisitos Previos
```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar docker-compose
sudo apt install docker-compose

# Configurar X11 forwarding
sudo apt install x11-xserver-utils
xhost +local:docker
```

#### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/afsh4ck/wifipwn.git
cd wifipwn
```

#### Paso 2: Ejecutar con el Script run.sh
```bash
# Hacer ejecutable el script
chmod +x run.sh

# Construir y ejecutar por primera vez
./run.sh run

# El script mostrará el banner:
#  _       __ ____ ______ ____ ____  _       __ _   __ 
# | |     / //  _// ____//  _// __ \| |     / // | / / 
# | | /| / / / / / /_    / / / /_/ /| | /| / //  |/ /  
# | |/ |/ /_/ / / __/  _/ / / ____/ | |/ |/ // /|  /   
# |__/|__//___//_/    /___//_/      |__/|__//_/ |_/    
#                    by:afsh4ck
```

#### Comandos Disponibles en run.sh
```bash
./run.sh build      # Construir la imagen Docker
./run.sh run        # Ejecutar WifiPwn
./run.sh stop       # Detener el contenedor
./run.sh restart    # Reiniciar el contenedor
./run.sh shell      # Abrir shell en el contenedor
./run.sh logs       # Ver logs
./run.sh logs -f    # Ver logs en tiempo real
./run.sh status     # Ver estado del contenedor
./run.sh update     # Actualizar imagen
./run.sh clean      # Limpiar contenedores e imágenes
./run.sh help       # Mostrar ayuda
```

### Opción 2: Despliegue con Docker Compose

#### Paso 1: Configurar Variables de Entorno
```bash
export DISPLAY=:0
xhost +local:docker
```

#### Paso 2: Ejecutar
```bash
# Construir y ejecutar
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

### Opción 3: Docker Manual

```bash
# Construir imagen
docker build -t wifipwn:latest .

# Crear directorios necesarios
mkdir -p data captures reports logs config

# Ejecutar contenedor
xhost +local:docker
docker run -d \
    --name wifipwn \
    --privileged \
    --cap-add=NET_ADMIN \
    --cap-add=NET_RAW \
    --cap-add=SYS_ADMIN \
    --network host \
    -e DISPLAY=$DISPLAY \
    -e QT_X11_NO_MITSHM=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/captures:/app/captures \
    -v $(pwd)/reports:/app/reports \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/config:/app/config \
    -v $(pwd)/templates:/app/templates \
    --device /dev/net/tun \
    --restart unless-stopped \
    wifipwn:latest
```

---

## Guía de Uso de la Aplicación

### 1. Dashboard - Panel Principal

Al iniciar WifiPwn, verás el **Dashboard** con:

- **Estadísticas en tiempo real**:
  - Redes descubiertas
  - Handshakes capturados
  - Handshakes crackeados
  - Credenciales capturadas
  - Campañas activas
  - Ataques deauth realizados

- **Gestión de Datos**:
  - Botón "Limpiar Redes": Elimina todas las redes de la BD
  - Botón "Limpiar Handshakes": Elimina todos los handshakes
  - Botón "Limpiar Credenciales": Elimina todas las credenciales
  - Botón **LIMPIAR TODO**: Elimina TODOS los datos (doble confirmación)
  - Botón "Exportar Datos a JSON": Exporta la base de datos completa

- **Últimas Actividades**: Tabla con el historial de acciones

### 2. Interfaces - Control de Interfaces WiFi

```
Pestaña: Interfaces
```

**Funciones disponibles:**
1. **Tabla de Interfaces**: Muestra todas las interfaces WiFi detectadas
   - Nombre de la interfaz
   - Dirección MAC
   - Modo (managed/monitor)
   - Estado (up/down)
   - Chipset

2. **Activar/Desactivar Modo Monitor**:
   - Selecciona una interfaz de la tabla
   - Haz clic en "Activar Modo Monitor"
   - El sistema ejecutará `airmon-ng start <interfaz>`

3. **Acciones Rápidas**:
   - **Refrescar**: Actualiza la lista de interfaces
   - **Matar Procesos Conflictivos**: Ejecuta `airmon-ng check kill`
   - **Resetear Interfaz**: Reinicia la interfaz seleccionada
   - **Cambiar MAC Aleatoria**: Cambia la MAC usando macchanger

### 3. Escaneo - Descubrimiento de Redes

```
Pestaña: Escaneo
```

**Pasos para escanear:**
1. Selecciona la interfaz en modo monitor del desplegable
2. Configura filtros opcionales:
   - ☑ Solo WPA/WPA2
   - ☑ Incluir 5GHz

3. Haz clic en **"Iniciar Escaneo"**
   - El comando `airodump-ng` se ejecuta en background
   - Las redes encontradas se guardan automáticamente en la BD

4. **Tabla de Resultados** muestra:
   - BSSID (MAC del AP)
   - Canal
   - ESSID (Nombre de la red)
   - Seguridad (WPA/WPA2/WEP/OPN)
   - Señal (dBm)
   - Beacons e IVs

5. **Acciones sobre redes**:
   - Seleccionar como objetivo
   - Copiar BSSID al portapapeles
   - Exportar resultados a JSON

### 4. Handshake - Captura de Handshakes

```
Pestaña: Handshake
```

**Para capturar un handshake:**

1. **Configurar Objetivo**:
   - BSSID: MAC del AP objetivo (ej: `00:11:22:33:44:55`)
   - Canal: Número de canal (1-14)
   - ESSID: Nombre de la red (opcional)

2. **Configurar Captura**:
   - Archivo de salida: Ruta donde guardar el .cap
   - ☑ Enviar Deauth automáticamente (opcional)
   - Número de paquetes deauth

3. Haz clic en **"Iniciar Captura"**
   - Se ejecuta `airodump-ng -c <canal> --bssid <bssid>`
   - El sistema monitorea el archivo en busca de handshakes

4. **Indicadores de Estado**:
   - 🟡 Capturando... (en progreso)
   - 🟢 **HANDSHAKE DETECTADO!** (éxito)
   - 🔴 No se encontró handshake

5. **Acciones manuales**:
   - **Enviar Deauth Manual**: Fuerza la reconexión de clientes
   - **Verificar Handshake**: Comprueba si el .cap contiene handshake

### 5. Cracking - Crackear Handshakes

```
Pestaña: Cracking
```

**Para crackear un handshake:**

1. **Seleccionar Archivo**:
   - Archivo .cap: Ruta al archivo de captura
   - BSSID: MAC del AP

2. **Seleccionar Método**:
   - ○ Aircrack-ng (recomendado)
   - ○ Hashcat (usa GPU, más rápido)

3. **Seleccionar Diccionario**:
   - Wordlist por defecto: `/usr/share/wordlists/rockyou.txt`
   - O seleccionar archivo personalizado

4. Haz clic en **"Iniciar Cracking"**
   - El proceso se ejecuta en background
   - Se muestra el progreso en tiempo real
   - La contraseña se guarda en la BD si se encuentra

5. **Resultados**:
   - Si se encuentra: Se muestra "KEY FOUND! [password]"
   - Si no: "Contraseña no encontrada en el diccionario"

### 6. Deauth - Ataques de Deautenticación

```
Pestaña: Deauth
```

**Configuración del ataque:**

1. **Objetivo**:
   - BSSID del AP: MAC del punto de acceso
   - Cliente (opcional): MAC específica o dejar vacío para broadcast

2. **Opciones**:
   - Número de paquetes: Cantidad de paquetes a enviar (1-1000)
   - Delay entre ráfagas: Tiempo entre envíos (ms)
   - ☑ Ataque continuo: Repite el ataque automáticamente

3. Haz clic en **"Iniciar Ataque"**
   - Ejecuta `aireplay-ng -0 <paquetes> -a <bssid>`
   - Estado muestra: "ATACANDO..." en rojo

4. **Detener**:
   - Haz clic en "Detener Ataque" para finalizar

### 7. Evil Portal - Portal Cautivo Falso

```
Pestaña: Evil Portal
```

**Para crear un AP falso:**

1. **Configurar AP**:
   - ESSID: Nombre de la red falsa (ej: "FreeWiFi")
   - Canal: 1-14
   - Password: Dejar vacío para AP abierto
   - Interfaz: Seleccionar interfaz física

2. **Plantilla**:
   - Seleccionar archivo HTML del portal
   - Por defecto: `templates/default_portal.html`

3. Haz clic en **"Iniciar Evil Portal"**
   - Se inicia `hostapd` para crear el AP
   - Se inicia `dnsmasq` para DHCP
   - Se redirige tráfico HTTP al portal

4. **Credenciales Capturadas**:
   - Se muestran en tiempo real en la tabla
   - Columnas: Hora, Usuario, Contraseña
   - Botón "Guardar": Exporta a archivo de texto
   - Botón "Limpiar": Borra la tabla

### 8. Auditoría - Campañas de Auditoría

```
Pestaña: Auditoría
```

**Crear una campaña:**

1. **Nueva Campaña**:
   - Nombre: Identificador de la campaña
   - Descripción: Detalles de la auditoría

2. **Agregar Objetivos**:
   - Haz clic en "Agregar Objetivo"
   - Introduce BSSID, ESSID, canal
   - Estado: pending/active/completed

3. **Guardar/Cargar**:
   - "Guardar Campaña": Almacena en la BD
   - "Cargar Campaña": Carga campaña existente

4. **Reportes**:
   - Pestaña "Reportes"
   - "Generar Reporte HTML": Crea informe detallado
   - "Generar Reporte PDF": Exporta a PDF

---

## Estructura del Proyecto

```
wifipwn/
├── wifipwn/                   # Código fuente
│   ├── core/                  # Módulos core
│   │   ├── config.py         # Configuración
│   │   ├── utils.py          # Utilidades
│   │   ├── wifi_manager.py   # Gestión WiFi
│   │   ├── database.py       # Base de datos SQLite
│   │   └── command_runner.py # Ejecutor de comandos
│   ├── modules/              # Módulos GUI
│   │   ├── dashboard.py      # Dashboard principal
│   │   ├── interface_panel.py
│   │   ├── network_scanner.py
│   │   ├── handshake_capture.py
│   │   ├── cracking.py
│   │   ├── deauth.py
│   │   ├── evil_portal.py
│   │   └── audit_campaign.py
│   └── main.py               # Punto de entrada
├── data/                     # Base de datos SQLite
├── captures/                 # Archivos .cap
├── reports/                  # Reportes generados
├── logs/                     # Logs de la aplicación
├── templates/                # Plantillas HTML
├── Dockerfile               # Imagen Docker
├── docker-compose.yml       # Configuración Docker
├── deploy.sh               # Script de despliegue
├── run.sh                  # Script de ejecución
└── requirements.txt        # Dependencias Python
```

---

## Flujo de Trabajo Típico

### Escenario 1: Capturar y Crackear un Handshake

```
1. Dashboard → Verificar que no hay datos previos (opcional: Limpiar Todo)

2. Interfaces → Seleccionar wlan0 → Activar Modo Monitor
   → Se crea interfaz wlan0mon

3. Escaneo → Seleccionar wlan0mon → Iniciar Escaneo
   → Esperar a detectar redes → Detener escaneo
   → Seleccionar red objetivo de la tabla

4. Handshake → El BSSID y canal se autocompletan
   → Configurar archivo de salida
   → ☑ Enviar Deauth automáticamente
   → Iniciar Captura
   → Esperar "HANDSHAKE DETECTADO!"
   → Detener captura

5. Cracking → Seleccionar archivo .cap generado
   → Introducir BSSID
   → Seleccionar wordlist
   → Iniciar Cracking
   → Esperar resultado

6. Dashboard → Verificar estadísticas actualizadas
```

### Escenario 2: Evil Portal

```
1. Interfaces → Asegurar que tenemos interfaz en modo managed

2. Evil Portal → Configurar:
   ESSID: "Starbucks_Free_WiFi"
   Canal: 6
   Password: (dejar vacío)
   
3. Iniciar Evil Portal → El AP se crea

4. Esperar a que víctimas se conecten
   → Las credenciales aparecen en la tabla

5. Guardar credenciales → Exportar a archivo

6. Detener Evil Portal
```

---

## Configuración IP Aleatoria

El script `deploy.sh` configura automáticamente una IP aleatoria en el rango privado:

- **Rango 10.x.x.x**: 10.0.0.0/8
- **Rango 172.16-31.x.x**: 172.16.0.0/12

Esto permite ejecutar múltiples instancias sin conflictos de red.

---

## Resolución de Problemas

### Error: "Cannot connect to X server"
```bash
# Permitir conexiones X11
xhost +local:docker

# Verificar DISPLAY
echo $DISPLAY
# Si está vacío:
export DISPLAY=:0
```

### Error: "Interface not found"
```bash
# Verificar interfaces disponibles
iw dev

# O dentro del contenedor
./run.sh shell
iw dev
```

### Error: "Operation not permitted"
```bash
# Asegurar privilegios
sudo ./run.sh run

# O en docker-compose, verificar:
# privileged: true
# cap_add:
#   - NET_ADMIN
```

### La interfaz no entra en modo monitor
```bash
# Dentro del contenedor
airmon-ng check kill
airmon-ng start wlan0
```

---

## Advertencia Legal

**⚠️ ESTA HERRAMIENTA ESTÁ DESTINADA ÚNICAMENTE PARA FINES EDUCATIVOS Y DE AUDITORÍA DE SEGURIDAD AUTORIZADA.**

El uso de esta herramienta en redes sin permiso explícito del propietario es **ILEGAL** y puede constituir un delito según las leyes de:
- Acceso no autorizado a sistemas informáticos
- Interceptación de comunicaciones
- Suplantación de identidad

El autor **NO SE HACE RESPONSABLE** del uso indebido de esta herramienta. El usuario asume toda la responsabilidad por el uso que haga de ella.

**Requisitos legales:**
- Obtener permiso por escrito del propietario de la red
- Documentar el alcance de la auditoría
- No interceptar tráfico de terceros sin consentimiento
- Eliminar todos los datos recopilados tras la auditoría

---

## Licencia

MIT License

Copyright (c) 2024 afsh4ck

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

---

## Autor

**afsh4ck**

- GitHub: [@afsh4ck](https://github.com/afsh4ck)
- Herramienta creada para fines educativos y de auditoría de seguridad

---

## Agradecimientos

- Aircrack-ng team
- Kali Linux team
- Docker team
- Comunidad de seguridad informática
