# 🌐 Valorize Bot en un servidor (24 horas, accesible desde el móvil)

Con esto tu bot funciona en un servidor en internet **las 24 horas**, aunque apagues tu PC, y lo controlas desde **cualquier navegador** (ordenador o móvil) con usuario y contraseña.

> ⏱️ **Tiempo:** unos 15 minutos.
> 💶 **Coste:** **gratis durante 6 meses con AWS** (plan gratuito con créditos), o unos **6 € al mes con Hetzner** (CX23: 5,49 € + la dirección IP, precios de junio de 2026). Elige uno de los dos en el Paso 2.
> 🔒 **Seguridad:** acceso cifrado (HTTPS), contraseña obligatoria, bloqueo tras 5 intentos fallidos, cortafuegos y actualizaciones de seguridad automáticas.

## Cómo funciona

```
Tu móvil / PC  ──HTTPS──▶  Servidor en Europa (AWS o Hetzner)
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

## Paso 2 (opción A) · Crear el servidor en AWS · gratis 6 meses

El **plan gratuito** de AWS para cuentas nuevas da **100 $ de crédito** (ampliable a 200 $) durante **6 meses** y, según AWS, **no te cobra nada mientras estés en él**: si se acaban los créditos o los 6 meses, te pide pasar al plan de pago antes de cobrarte.

1. Crea una cuenta en **https://aws.amazon.com/free** y, cuando te pregunte, elige el **plan gratuito** (*Free plan*). Pedirá una tarjeta para verificar tu identidad.
2. Entra en la consola de AWS. Arriba a la derecha, elige la región **Europa (Fráncfort)** `eu-central-1` o **Europa (España)** `eu-south-2`. ⚠️ No uses regiones de EE. UU.: Binance bloquea las conexiones desde allí.
3. En el buscador de arriba escribe **EC2**, entra y pulsa **Lanzar instancia** (*Launch instance*).
4. Rellena:
   - **Nombre:** `valorize-bot`.
   - **Imagen (AMI):** **Ubuntu** → **Ubuntu Server 24.04 LTS** (marcada como *Apta para la capa gratuita*), arquitectura **64 bits (x86)**.
   - **Tipo de instancia:** **t3.micro** (*Apta para la capa gratuita*). Con ella, los 100 $ de crédito alcanzan para los 6 meses.
   - **Par de claves:** elige **Continuar sin un par de claves**. No hace falta: si alguna vez necesitas entrar, se hace desde el navegador.
   - **Configuración de red:** marca las tres casillas: **Permitir el tráfico SSH**, **Permitir el tráfico HTTPS desde Internet** y **Permitir el tráfico HTTP desde Internet**.
   - **Almacenamiento:** deja lo que viene (8 GB).
   - Abre **Detalles avanzados** (abajo del todo) y, en **Datos de usuario** (*User data*), **pega el texto** del Paso 1 (`Ctrl + V`).
5. Pulsa **Lanzar instancia**.
6. Ve a **Instancias**, selecciona `valorize-bot` y apunta su **Dirección IPv4 pública** (por ejemplo `3.120.5.9`).

> ⏱️ En `t3.micro` la instalación tarda algo más: cuenta **unos 8–10 minutos** antes del Paso 3.
> ⚠️ **No pulses "Terminar"** en la instancia: la borra con todos tus datos. Si la **paras** y la vuelves a **iniciar**, AWS le cambia la IP: el bot actualiza su dirección solo, pero tendrás que usar la nueva (`https://IP-NUEVA-CON-GUIONES.sslip.io`). Si solo la reinicias, no cambia.
> 💡 Para ver cuánto crédito te queda: busca **Facturación** (*Billing*) en la consola → **Capa gratuita** / **Créditos**.

## Paso 2 (opción B) · Crear el servidor en Hetzner · unos 6 €/mes

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

1. Espera **unos 5 minutos** (8–10 en AWS `t3.micro`): el servidor se instala solo (sistema, bot, HTTPS y cortafuegos).
2. Abre en el navegador tu dirección: la IP **con guiones en lugar de puntos** seguida de `.sslip.io`:
   - IP `95.217.1.2` → **`https://95-217-1-2.sslip.io`**
3. Entra con tu contraseña.
4. Se abre el **asistente de configuración** (como en tu PC): elige exchange, modo y monedas, y pulsa **▶ Arrancar**.

> 📱 Guarda la dirección en los favoritos del móvil, o en la pantalla de inicio ("Añadir a pantalla de inicio") para abrirlo como una app.

## Paso 4 · Apagar el bot de tu PC

Para no tener dos bots a la vez, en el panel de tu PC pulsa **⏻** y, si activaste el arranque automático, haz doble clic en `autoarranque-quitar.bat`.

---

## Recomendado

- **Avisos por Telegram:** con el bot en un servidor es la mejor forma de enterarte de compras, ventas y problemas. En el panel pulsa **🔔 Avisos** y sigue los 3 pasos (crear tu bot con @BotFather, pegar el token y escribirle). Se activan al momento, sin reiniciar nada.
- **Dinero real:** en tu exchange, **restringe la clave de API a la IP de tu servidor** (en AWS, si vas a hacerlo, asigna antes una *IP elástica* para que no cambie). Así, aunque alguien robara la clave, no podría usarla desde otro sitio. Y nunca actives el permiso de retiros.

## Administración (avanzado)

Solo si alguna vez lo necesitas. Abre una terminal del servidor desde el navegador:
- **AWS:** selecciona la instancia → **Conectar** → pestaña **EC2 Instance Connect** → **Conectar**. Antes de los comandos escribe `sudo -i` y pulsa Enter.
- **Hetzner:** botón **>_** del servidor (entras como `root`).

| Para... | Comando |
|---|---|
| Ver si funciona | `systemctl status valorize-bot` |
| Ver el registro en directo | `journalctl -u valorize-bot -f` |
| Ver cómo fue la instalación | `cat /var/log/valorize-install.log` |
| Actualizar a la última versión de GitHub | `bash /opt/valorize-bot/deploy/instalar-servidor.sh` |
| Cambiar la contraseña del panel | `sudo -u valorize /opt/valorize-bot/venv/bin/python /opt/valorize-bot/panel.py --set-password` |
| Editar el `.env` a mano | `nano /opt/valorize-bot/.env` y después `systemctl restart valorize-bot` |
| Reiniciar el bot | `systemctl restart valorize-bot` |

Tus datos (configuración, claves, operaciones) están en `/opt/valorize-bot` y **no se borran al actualizar**.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| La dirección no abre tras 5 minutos | Espera 5 minutos más (en AWS `t3.micro` puede tardar 10). Si sigue igual, abre la terminal (ver Administración) y ejecuta `cat /var/log/valorize-install.log`, y pásame el final |
| En AWS no abre nada | Revisa que al crearla marcaste **HTTP** y **HTTPS** en la configuración de red. Si no: instancia → **Seguridad** → grupo de seguridad → **Editar reglas de entrada** → añade HTTP (80) y HTTPS (443) desde `0.0.0.0/0` |
| Después de parar e iniciar en AWS ya no abre | La IP ha cambiado: usa la nueva IP pública con guiones + `.sslip.io` |
| Aviso de certificado no válido | El certificado tarda un minuto en emitirse la primera vez. Recarga |
| "Demasiados intentos" | Has fallado la contraseña 5 veces: espera 15 minutos |
| He olvidado la contraseña | Cámbiala con el comando de la tabla de administración |
| Binance da error 451 | El servidor está en un país bloqueado: créalo en Europa (AWS Fráncfort/España, Hetzner Alemania/Finlandia) |

## Usar un dominio propio (opcional)

Si tienes un dominio (por ejemplo `bot.tudominio.com`), crea un registro DNS de tipo **A** que apunte a la IP del servidor (en AWS, usa una IP elástica para que no cambie) y ejecuta, como `root`:

```
DOMAIN=bot.tudominio.com bash /opt/valorize-bot/deploy/instalar-servidor.sh
```
