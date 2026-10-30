#!/usr/bin/env bash
# Instala Valorize Bot en un servidor Ubuntu (22.04 / 24.04) con acceso web seguro (HTTPS).
#
# Lo normal es NO ejecutarlo a mano: lo lanza solo el texto de "cloud-init" que genera
# preparar-servidor.bat (ver SERVIDOR.md). También puede ejecutarse como root:
#     PANEL_PASSWORD_HASH='scrypt:...' bash deploy/instalar-servidor.sh
#
# Variables opcionales:
#   PANEL_PASSWORD_HASH  hash de la contraseña del panel (sin él, el panel no se abre a internet)
#   DOMAIN               dominio propio (si no, se usa <ip>.sslip.io, gratis y sin configurar nada)
#   REPO                 repositorio de GitHub del bot
#
# Volver a ejecutarlo actualiza el bot a la última versión de GitHub sin borrar tus datos.
set -euo pipefail

REPO="${REPO:-https://github.com/solertesting-prog/BINANCE-BOT.git}"
APP_USER="valorize"
APP_DIR="/opt/valorize-bot"
PORT=8765
export DEBIAN_FRONTEND=noninteractive

echo "==> [1/7] Paquetes del sistema"
apt-get update -q
apt-get install -yq python3-venv python3-pip git ufw curl gnupg debian-keyring debian-archive-keyring \
  apt-transport-https unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades || true      # parches de seguridad automáticos

echo "==> [2/7] Caddy (servidor web con HTTPS automático)"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    -o /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q
  apt-get install -yq caddy
fi

echo "==> [3/7] Usuario y código del bot"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --home-dir "/home/$APP_USER" \
  --shell /usr/sbin/nologin "$APP_USER"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --depth 1 "$REPO" "$APP_DIR"
fi
chown -R "$APP_USER:" "$APP_DIR"
sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only     # actualiza (como el usuario del bot)

echo "==> [4/7] Entorno de Python"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "==> [5/7] Configuración (.env)"
if [ -z "${DOMAIN:-}" ]; then
  IP="$(curl -4 -fsS https://api.ipify.org || hostname -I | awk '{print $1}')"
  DOMAIN="$(echo "$IP" | tr . -).sslip.io"
fi
ENV_FILE="$APP_DIR/.env"
[ -f "$ENV_FILE" ] || cp "$APP_DIR/.env.example" "$ENV_FILE"
set_env() {
  if grep -q "^$1=" "$ENV_FILE"; then sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"; else echo "$1=$2" >> "$ENV_FILE"; fi
}
set_env PANEL_HOSTS "$DOMAIN"
if [ -n "${PANEL_PASSWORD_HASH:-}" ]; then set_env PANEL_PASSWORD_HASH "$PANEL_PASSWORD_HASH"; fi
chown "$APP_USER:" "$ENV_FILE"
chmod 600 "$ENV_FILE"                     # solo el usuario del bot puede leer las claves

echo "==> [6/7] Servicio (arranca solo y se reinicia si falla)"
cat > /etc/systemd/system/valorize-bot.service <<EOF
[Unit]
Description=Valorize Bot (panel y bot de trading)
After=network-online.target
Wants=network-online.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python panel.py --no-browser --port $PORT
Restart=always
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
	encode gzip
	reverse_proxy 127.0.0.1:$PORT
}
EOF

echo "==> [7/7] Cortafuegos y arranque"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
systemctl daemon-reload
systemctl enable --now valorize-bot
systemctl restart valorize-bot
systemctl enable caddy
systemctl restart caddy

echo "https://$DOMAIN" > /root/valorize-url.txt
echo
echo "=========================================================="
echo "  Valorize Bot instalado: https://$DOMAIN"
if [ -z "$(grep '^PANEL_PASSWORD_HASH=' "$ENV_FILE" | cut -d= -f2-)" ]; then
  echo "  FALTA LA CONTRASEÑA: el panel no se abrirá hasta crearla con:"
  echo "  sudo -u $APP_USER $APP_DIR/venv/bin/python $APP_DIR/panel.py --set-password && systemctl restart valorize-bot"
fi
echo "=========================================================="
