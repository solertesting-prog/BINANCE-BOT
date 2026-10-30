# 🌐 Valorize Bot en un servidor (24 horas, accesible desde el móvil)

Con esto tu bot funciona en un servidor en internet **las 24 horas**, aunque apagues tu PC, y lo controlas desde **cualquier navegador** (ordenador o móvil) con usuario y contraseña.

> ⏱️ **Tiempo:** unos 15 minutos.
> 💶 **Coste:** el servidor más barato de Hetzner cuesta unos **6 € al mes** (CX23: 5,49 € + la dirección IP, precios de junio de 2026; compruébalo en su web).
> 🔒 **Seguridad:** acceso cifrado (HTTPS), contraseña obligatoria, bloqueo tras 5 intentos fallidos, cortafuegos y actualizaciones de seguridad automáticas.

## Cómo funciona

```
Tu móvil / PC  ──HTTPS──▶  Servidor en Alemania o Finlandia (Hetzner)
                            ├─ Caddy: certificado HTTPS automático
                            ├─ Valorize Bot: panel + bot, 24 h, se reinicia solo
                            └─ Cortafuegos: solo web segura y administración
```

No hace falta comprar un dominio: el servidor usa una dirección gratuita del tipo `https://95-217-1-2.sslip.io` (tu IP con guiones), con certificado HTTPS real.

---

## Paso 1 · Preparar el texto de instalación (en tu PC)

1. Abre **Documentos → binance-bot**.
2. Doble clic en **`preparar-servidor.bat`**.
3. Escribe la **contraseña** que usarás para entrar al panel desde internet (mínimo 10 caracteres; mejor larga y que no uses en otro sitio). Repítela.
4. El programa crea el texto de instalación y lo deja **copiado en el portapapeles**. También lo guarda en `cloud-init-servidor.txt`.

> Tu contraseña no se guarda en ningún sitio: el texto solo lleva un "hash" (una huella imposible de revertir).

## Paso 2 · Crear el servidor en Hetzner

1. Entra en **https://www.hetzner.com/cloud** y crea una cuenta (te pedirá verificar tu identidad y un método de pago).
2. En la consola de Hetzner Cloud, crea un **proyecto** (por ejemplo "Valorize") y pulsa **Añadir servidor** (*Add Server*).
3. Elige:
   - **Ubicación:** Alemania (Falkenstein o Núremberg) o Finlandia (Helsinki). ⚠️ No elijas EE. UU.: Binance bloquea las conexiones desde allí.
   - **Imagen:** **Ubuntu 24.04**.
   - **Tipo:** el más barato de los compartidos (**CX23**, 2 vCPU / 4 GB). Sobra para el bot.
   - **Red:** deja **IPv4 pública** activada.
   - **Claves SSH:** opcional. Si no pones ninguna, Hetzner te envía una contraseña de administración por email (guárdala, aunque normalmente no la necesitarás).
   - **Configuración de la nube** (*Cloud config*): **pega aquí el texto** del Paso 1 (`Ctrl + V`).
   - **Nombre:** por ejemplo `valorize-bot`.
4. Pulsa **Crear y comprar** (*Create & Buy now*).
5. Apunta la **dirección IP** que aparece (por ejemplo `95.217.1.2`).

## Paso 3 · Esperar y entrar

1. Espera **unos 5 minutos**: el servidor se instala solo (sistema, bot, HTTPS y cortafuegos).
2. Abre en el navegador tu dirección: la IP **con guiones en lugar de puntos** seguida de `.sslip.io`:
   - IP `95.217.1.2` → **`https://95-217-1-2.sslip.io`**
3. Entra con tu contraseña.
4. Se abre el **asistente de configuración** (como en tu PC): elige exchange, modo y monedas, y pulsa **▶ Arrancar**.

> 📱 Guarda la dirección en los favoritos del móvil, o en la pantalla de inicio ("Añadir a pantalla de inicio") para abrirlo como una app.

## Paso 4 · Apagar el bot de tu PC

Para no tener dos bots a la vez, en el panel de tu PC pulsa **⏻** y, si activaste el arranque automático, haz doble clic en `autoarranque-quitar.bat`.

---

## Recomendado

- **Avisos por Telegram:** con el bot en un servidor es la mejor forma de enterarte de compras, ventas y problemas. Configúralos como en el manual (Parte 8) y pon `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` en el `.env` del servidor (ver "Administración" abajo).
- **Dinero real:** en tu exchange, **restringe la clave de API a la IP de tu servidor**. Así, aunque alguien robara la clave, no podría usarla desde otro sitio. Y nunca actives el permiso de retiros.

## Administración (avanzado)

Solo si alguna vez lo necesitas. Desde la consola web de Hetzner (botón **>_** del servidor) o por SSH, como `root`:

| Para... | Comando |
|---|---|
| Ver si funciona | `systemctl status valorize-bot` |
| Ver el registro en directo | `journalctl -u valorize-bot -f` |
| Ver cómo fue la instalación | `cat /var/log/valorize-install.log` |
| Actualizar a la última versión de GitHub | `bash /opt/valorize-bot/deploy/instalar-servidor.sh` |
| Cambiar la contraseña del panel | `sudo -u valorize /opt/valorize-bot/venv/bin/python /opt/valorize-bot/panel.py --set-password` |
| Editar el `.env` (Telegram…) | `nano /opt/valorize-bot/.env` y después `systemctl restart valorize-bot` |
| Reiniciar el bot | `systemctl restart valorize-bot` |

Tus datos (configuración, claves, operaciones) están en `/opt/valorize-bot` y **no se borran al actualizar**.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| La dirección no abre tras 5 minutos | Espera 5 minutos más. Si sigue igual, en la consola de Hetzner ejecuta `cat /var/log/valorize-install.log` y pásame el final |
| Aviso de certificado no válido | El certificado tarda un minuto en emitirse la primera vez. Recarga |
| "Demasiados intentos" | Has fallado la contraseña 5 veces: espera 15 minutos |
| He olvidado la contraseña | Cámbiala con el comando de la tabla de administración |
| Binance da error 451 | El servidor está en un país bloqueado: crea otro en Alemania o Finlandia |

## Usar un dominio propio (opcional)

Si tienes un dominio (por ejemplo `bot.tudominio.com`), crea un registro DNS de tipo **A** que apunte a la IP del servidor y ejecuta, como `root`:

```
DOMAIN=bot.tudominio.com bash /opt/valorize-bot/deploy/instalar-servidor.sh
```
