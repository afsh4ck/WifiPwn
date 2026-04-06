FROM kalilinux/kali-rolling:latest

ENV DEBIAN_FRONTEND=noninteractive

# ── Herramientas del sistema ──────────────────────────────────────────
# aircrack-ng incluye airodump-ng, aireplay-ng y airmon-ng
RUN apt-get update && apt-get install -y \
    aircrack-ng \
    hostapd \
    dnsmasq \
    iw \
    wireless-tools \
    macchanger \
    hashcat \
    hcxdumptool \
    hcxtools \
    reaver \
    bully \
    python3 \
    python3-pip \
    net-tools \
    iputils-ping \
    curl \
    wget \
    git \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js 20 ────────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Backend: dependencias Python ──────────────────────────────────────
COPY backend/requirements.txt /app/backend/
RUN pip3 install --no-cache-dir -r /app/backend/requirements.txt

# ── Frontend: instalar dependencias y compilar ────────────────────────
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm install

COPY frontend/ /app/frontend/
RUN npm run build

# ── Copiar código fuente del backend ─────────────────────────────────
WORKDIR /app
COPY backend/ /app/backend/
COPY deploy.sh /app/

# ── Directorios de datos ──────────────────────────────────────────────
RUN mkdir -p /app/data /app/captures /app/reports /app/logs /app/templates

RUN chmod +x /app/deploy.sh

EXPOSE 8000 1234

CMD ["bash", "/app/deploy.sh"]
