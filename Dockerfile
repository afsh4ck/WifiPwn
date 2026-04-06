FROM kalilinux/kali-rolling:latest

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV QT_X11_NO_MITSHM=1
ENV QT_QPA_PLATFORM=xcb

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    # Herramientas WiFi
    aircrack-ng \
    airodump-ng \
    aireplay-ng \
    airmon-ng \
    hostapd \
    dnsmasq \
    iw \
    wireless-tools \
    macchanger \
    # Herramientas adicionales
    hashcat \
    hcxdumptool \
    hcxtools \
    reaver \
    bully \
    # Python y PyQt5
    python3 \
    python3-pip \
    python3-pyqt5 \
    python3-pyqt5.qtcharts \
    libqt5widgets5 \
    libqt5gui5 \
    libqt5core5a \
    # Utilidades
    net-tools \
    iputils-ping \
    curl \
    wget \
    git \
    vim \
    # Para X11 forwarding
    libx11-xcb1 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Base de datos
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de la aplicación
WORKDIR /app/wifipwn

# Copiar requirements primero para aprovechar cache
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copiar todo el código
COPY wifipwn/ /app/wifipwn/
COPY deploy.sh /app/

# Crear directorios necesarios
RUN mkdir -p /app/data /app/captures /app/reports /app/logs /app/templates

# Dar permisos
RUN chmod +x /app/deploy.sh

# Crear un script de inicio que muestre el banner y ejecute deploy.sh
RUN echo '#!/bin/bash\n\
echo ""\n\
echo " _       __ ____ ______ ____ ____  _       __ _   __ "\n\
echo "| |     / //  _// ____//  _// __ \\| |     / // | / / "\n\
echo "| | /| / / / / / /_    / / / /_/ /| | /| / //  |/ /  "\n\
echo "| |/ |/ /_/ / / __/  _/ / / ____/ | |/ |/ // /|  /   "\n\
echo "|__/|__//___//_/    /___//_/      |__/|__//_/ |_/    "\n\
echo "                                                     "\n\
echo "                    by:afsh4ck"\n\
echo ""\n\
exec /app/deploy.sh' > /app/start.sh && chmod +x /app/start.sh

# Puerto para el portal cautivo (si se usa)
EXPOSE 80 443 8080

# Comando por defecto
CMD ["/app/start.sh"]
