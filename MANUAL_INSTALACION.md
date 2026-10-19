# 📘 Manual del Trading Bot, paso a paso

Este manual está pensado para alguien que **nunca ha programado**. En Windows todo se hace con **doble clic**: no hace falta escribir comandos.

> ⏱️ **Tiempo:** unos 15 minutos la primera vez.
> 💸 **Dinero:** no necesitas poner dinero para probarlo. Hasta la Parte 9 todo es simulado.
> 🍎 **¿Usas Mac?** Ve al [Anexo para Mac](#anexo-instalación-en-mac).

---

## Índice

1. [Qué es y cómo funciona](#1-qué-es-y-cómo-funciona)
2. [Instalar Python](#2-instalar-python)
3. [Descargar el bot](#3-descargar-el-bot)
4. [Instalar el bot (doble clic)](#4-instalar-el-bot-doble-clic)
5. [El panel de control](#5-el-panel-de-control)
6. [Probar la estrategia con datos pasados (backtest)](#6-probar-la-estrategia-con-datos-pasados-backtest)
7. [Recibir avisos en el móvil por Telegram](#7-recibir-avisos-en-el-móvil-por-telegram)
8. [Probar con la testnet de Binance](#8-probar-con-la-testnet-de-binance)
9. [Pasar a dinero real](#9-pasar-a-dinero-real)
10. [Cambiar la configuración](#10-cambiar-la-configuración)
11. [Que funcione siempre: arranque automático y servidor](#11-que-funcione-siempre-arranque-automático-y-servidor)
12. [Problemas frecuentes y soluciones](#12-problemas-frecuentes-y-soluciones)
13. [Resumen de archivos](#13-resumen-de-archivos)

---

## 1. Qué es y cómo funciona

El bot **compra y vende criptomonedas solo** en Binance, siguiendo unas reglas fijas:

- **Cuándo compra:** cuando la media de los últimos 20 periodos cruza por encima de la de 50 (el precio empieza a subir con fuerza), siempre que el mercado esté en tendencia alcista (precio por encima de la media de 200) y con movimiento claro (ADX ≥ 20).
- **Cuánto compra:** lo justo para que, si sale mal, pierdas como máximo un **1 % de tu capital** en esa operación.
- **Cuándo vende:**
  - Si el precio cae hasta el **stop loss**, una distancia calculada según lo que suele moverse la moneda (2,5 × ATR).
  - Si después de subir cae desde su máximo (**trailing stop**, 3 × ATR). El stop va subiendo con el precio para proteger lo ganado.
  - Si las medias se cruzan a la baja.
- **Seguridad:** si el capital total cae un **20 %**, vende todo y se detiene.

Tú no tienes que operar: lo controlas desde un **panel en el navegador**, donde ves el gráfico, las posiciones y los resultados.

---

## 2. Instalar Python

Python es el "motor" que hace funcionar el bot. Solo se instala una vez. **Si ya lo tienes, sáltate esta parte.**

1. Entra en **https://www.python.org/downloads/** y pulsa el botón amarillo **"Download Python 3.x.x"**.
2. Abre el archivo descargado (en la carpeta *Descargas*).
3. ⚠️ **MUY IMPORTANTE:** en la primera pantalla del instalador, abajo, **marca la casilla "Add python.exe to PATH"**. Si no la marcas, nada funcionará después.
4. Pulsa **"Install Now"**, espera y pulsa **"Close"**.

---

## 3. Descargar el bot

1. Entra en **https://github.com/solertesting-prog/BINANCE-BOT** (inicia sesión si el repositorio es privado).
2. Pulsa el botón verde **"<> Code"** y luego **"Download ZIP"**.
3. En *Descargas*: clic derecho sobre el ZIP → **"Extraer todo..."** → *Extraer*.
4. Mueve la carpeta resultante a **Documentos** y llámala **`binance-bot`**.

Al abrir `Documentos\binance-bot` debes ver archivos como `instalar.bat`, `panel.py`, `bot.py`... (Si ves otra carpeta dentro con el mismo nombre, entra en ella: esa es la buena.)

---

## 4. Instalar el bot (doble clic)

1. Abre la carpeta **`Documentos\binance-bot`**.
2. Haz **doble clic en `instalar.bat`**.
3. Si aparece un aviso azul de **"Windows protegió su PC"**: pulsa **"Más información"** → **"Ejecutar de todas formas"**. (Sale porque Windows no conoce el archivo; es normal.)
4. Se abre una ventana negra que lo hace todo sola en 1–2 minutos:
   - prepara Python e instala las piezas del bot,
   - crea tu archivo de configuración privada (`.env`) en **modo simulado**,
   - comprueba que todo funciona (debe poner **`passed`**),
   - crea el icono **"Trading Bot"** en tu escritorio.
5. Al final pregunta **"¿Quieres que el panel se abra solo al encender el PC? [S,N]"**. Pulsa **S** (recomendado) o **N**.
6. Se abre el **panel** en tu navegador. 🎉

A partir de ahora, para abrir el bot **solo tienes que hacer doble clic en el icono "Trading Bot" del escritorio**.

---

## 5. El panel de control

El panel se abre en tu navegador en la dirección **http://127.0.0.1:8765**. Solo funciona en tu ordenador: nadie más puede verlo ni controlarlo.

### Qué ves

| Zona | Qué muestra |
|---|---|
| **Barra superior** | Modo (**Simulado** / **Testnet** / **Dinero real**), estado (● En marcha / Parado) y los botones |
| **Capital** | Lo que vale tu cuenta ahora (dinero + monedas compradas) |
| **Resultado total** | Cuánto has ganado o perdido desde que empezaste |
| **Disponible** | USDT sin invertir |
| **Posiciones** | Cuántas compras hay abiertas y cuánto dinero hay invertido |
| **Operaciones** | Operaciones cerradas, % de acierto y resultado |
| **Gráfico** | Velas de la moneda con las medias, las compras ▲ y ventas ▼ del bot, y las líneas de entrada y stop de la posición abierta. Pasa el ratón para ver los valores de cada vela. Cambia de moneda con las pestañas |
| **Posiciones abiertas** | Cada compra con su resultado, su stop actual y el botón **Cerrar posición** |
| **Estrategia** | La configuración que está usando |
| **Evolución del capital** | Gráfico de tu capital a lo largo del tiempo |
| **Operaciones cerradas** y **Registro** | Historial completo y todo lo que hace el bot |

### Botones

| Botón | Qué hace |
|---|---|
| **▶ Arrancar** | El bot empieza a operar |
| **■ Parar** | El bot deja de abrir y cerrar operaciones. Las posiciones abiertas se mantienen (en modo real, su stop sigue puesto en Binance) |
| **Cerrar posición** | Vende esa moneda ahora mismo, a precio de mercado |
| **⏻** | Apaga el panel y el bot por completo |

### Cosas importantes

- **Puedes cerrar la pestaña del navegador**: el bot sigue funcionando en segundo plano. Para volver a verlo, doble clic en el icono del escritorio.
- **El bot puede pasar días sin operar.** Es normal: espera a que se den todas las condiciones.
- El bot revisa los precios **cada minuto** y la estrategia **cada vez que se cierra una vela de 4 horas**.
- Si apagas el PC con el bot en marcha, **al volver a abrir el panel continúa solo** donde estaba.
- 💤 **El PC no debe suspenderse** mientras quieras que opere: *Configuración → Sistema → Inicio/apagado y suspensión* → "Nunca" (al menos cuando está enchufado).

> 📅 **Recomendación:** déjalo en modo simulado **varias semanas** antes de pensar en dinero real.

### Volver a empezar la simulación desde cero

Pulsa ⏻ para apagar el panel y borra los archivos `state.json` y `trades_log.csv` de la carpeta del bot. Al abrirlo de nuevo, empieza con 1.000 USDT ficticios.

---

## 6. Probar la estrategia con datos pasados (backtest)

Un **backtest** simula qué habría pasado si el bot hubiera funcionado durante el último año, usando precios reales de Binance.

**Forma fácil:** doble clic en **`backtest.bat`**. Al terminar, se abre un informe con gráficos en el navegador.

### Cómo leer los resultados

| Dato | Qué significa | Qué buscar |
|---|---|---|
| **Rentabilidad** | Cuánto habrías ganado o perdido | Positiva |
| **Comprar y mantener** | Lo que habrías ganado comprando el primer día y esperando | El bot debería ganar más, o parecido con mucho menos riesgo |
| **Máx. drawdown** | La peor caída por el camino | ¿Aguantarías ver bajar tu dinero ese %? |
| **Operaciones** | Cuántas compras-ventas hizo | Con menos de 20–30, puede ser pura suerte |
| **Profit factor** | Lo ganado entre lo perdido | Por encima de 1,3–1,5 empieza a ser interesante |

### Pruebas avanzadas (opcional)

Abre una terminal en la carpeta (haz clic en la barra de dirección del Explorador, escribe `cmd` y pulsa Enter) y escribe, por ejemplo:

```
backtest.bat --days 1095
backtest.bat --symbol BTC/USDT,ETH/USDT,SOL/USDT
backtest.bat --timeframe 1d --risk 0.02
```

| Opción | Qué hace |
|---|---|
| `--days 1095` | Prueba 3 años en lugar de 1 |
| `--symbol ETH/USDT` | Otra moneda (o varias separadas por comas) |
| `--timeframe 1h` | Velas de 1 hora (`1h`, `4h`, `1d`) |
| `--risk 0.02` | Arriesga un 2 % por operación |
| `--stop pct --sl 0.03` | Stop fijo del 3 % en lugar de por volatilidad |
| `--atr-stop 3 --atr-trail 4` | Stops más holgados |
| `--trend 0` / `--adx 0` | Quita los filtros |

Para buscar automáticamente la mejor combinación, usa el optimizador (tarda unos minutos):

```
venv\Scripts\python optimize.py --days 1095
```

👉 Fíjate solo en la línea **"Resultado fuera de muestra"**: es lo que habría pasado de verdad. Ignora los números espectaculares del "Top 5": suelen ser casualidad.

---

## 7. Recibir avisos en el móvil por Telegram

Te llegará un mensaje cada vez que el bot compre o venda, un resumen diario y cualquier aviso importante.

1. En Telegram, busca **@BotFather** (con la marca azul de verificado) y escríbele `/newbot`.
2. Ponle un **nombre** (por ejemplo `Mi trading bot`) y un **usuario** que termine en `bot` (por ejemplo `albert_trading_bot`).
3. Te dará un **token**, algo como `7123456789:AAH-xxxxxxxx`. Cópialo y no lo compartas.
4. Busca tu bot nuevo en Telegram, ábrelo y pulsa **Iniciar**.
5. En el navegador abre esta dirección **cambiando `TU_TOKEN` por tu token** (sin espacios):
   `https://api.telegram.org/botTU_TOKEN/getUpdates`
6. Busca `"chat":{"id":` seguido de un número: ese número es tu **chat_id**. (Si sale `"result":[]`, escribe algo a tu bot y recarga.)
7. Abre el archivo `.env` de la carpeta del bot con el Bloc de notas (clic derecho → *Abrir con* → *Bloc de notas*) y rellena:
   ```
   TELEGRAM_TOKEN=7123456789:AAH-xxxxxxxx
   TELEGRAM_CHAT_ID=123456789
   ```
8. Guarda (`Ctrl + G` o `Ctrl + S`). En el panel pulsa ⏻ y vuelve a abrirlo desde el icono. Te llegará "🤖 Bot iniciado" cuando lo arranques.

---

## 8. Probar con la testnet de Binance

La **testnet** es una copia de Binance con dinero de mentira. Sirve para comprobar que el bot envía **órdenes reales** (incluido el stop puesto en Binance) sin arriesgar nada.

1. Entra en **https://testnet.binance.vision/** → **"Log In with GitHub"**.
2. Pulsa **"Generate HMAC_SHA256 Key"**, ponle una descripción y pulsa *Generate*.
3. Copia la **API Key** y la **Secret Key** (la Secret Key solo se muestra una vez).
4. Abre `.env` con el Bloc de notas y déjalo así:
   ```
   MODE=live
   TESTNET=true
   BINANCE_API_KEY=pega_aqui_tu_api_key
   BINANCE_API_SECRET=pega_aqui_tu_secret_key
   ```
5. Pulsa ⏻ en el panel, borra `state.json` y `trades_log.csv`, y abre el panel de nuevo. Arriba debe poner **Testnet**.

---

## 9. Pasar a dinero real

> ⚠️ **Antes de seguir, sé honesto contigo:**
> - ¿Lo has tenido **varias semanas** en simulado y los resultados te convencen?
> - ¿Vas a usar **solo dinero que puedes permitirte perder entero**?
>
> Si alguna respuesta es "no", espera. Ningún bot garantiza ganancias.

### 9.1 Crear las claves de API en Binance

1. Entra en **https://www.binance.com** → icono de perfil → **"Gestión de API"**.
2. **"Crear API"** → **"Generada por el sistema"** → nombre `trading-bot` → verificación de seguridad.
3. Copia la **API Key** y la **Secret Key** (solo se muestra una vez).
4. **"Editar restricciones"** y deja los permisos **exactamente así**:
   - ✅ **Activar lectura**
   - ✅ **Activar el trading spot y de margen**
   - ❌ **Activar retiros → NUNCA.** Así, aunque alguien robara tus claves, no podría sacar dinero.
   - ❌ Todo lo demás, desactivado.
5. Si tienes IP fija (o usas un servidor), restringe el acceso a esa IP.

### 9.2 Configurar el bot

1. Abre `.env` con el Bloc de notas:
   ```
   MODE=live
   TESTNET=false
   BINANCE_API_KEY=tu_api_key_real
   BINANCE_API_SECRET=tu_secret_key_real
   ```
2. Pulsa ⏻ en el panel, borra `state.json` y `trades_log.csv`, y vuelve a abrirlo. Arriba debe poner **Dinero real** en rojo.

### 9.3 Preparar la cuenta

- El bot usa el **USDT de tu cuenta Spot**. **Deja ahí solo lo que quieras que use**; el resto, muévelo a *Fondos* o *Earn*.
- Solo vende lo que **él** ha comprado: no toca otras monedas que tengas.
- **Empieza con poco** (por ejemplo 100–200 USDT). Con riesgo del 1 %, las compras serán pequeñas y Binance exige un mínimo de unos 5–10 USDT por orden.

### 9.4 Protecciones en modo real

- **Stop puesto en Binance:** al comprar, el bot deja una orden de stop loss **dentro de Binance**. Si tu PC se apaga o pierde internet, Binance venderá igualmente si el precio cae hasta ahí. El panel lo indica con "· en Binance". Cuando el trailing stop sube, el bot mueve esa orden.
- **Doble vigilancia:** además, el bot vigila el precio cada minuto por su cuenta.
- **Reconciliación:** al arrancar, comprueba si mientras estaba apagado saltó algún stop o vendiste algo a mano, y lo apunta.
- **Reintentos:** si falla la conexión, reintenta las consultas. Las órdenes de compra o venta **nunca** se repiten a ciegas.

### 🔒 Reglas de seguridad

- **Nunca compartas el archivo `.env`** ni hagas capturas donde se vean tus claves. No se sube a GitHub (está excluido a propósito).
- Si crees que alguien ha visto tus claves: Binance → Gestión de API → **bórralas** y crea otras.
- No tengas el bot funcionando a la vez en dos ordenadores con la misma cuenta.

---

## 10. Cambiar la configuración

Toda la estrategia está en **`config.py`**.

1. Pulsa ⏻ en el panel.
2. Clic derecho sobre `config.py` → *Abrir con* → **Bloc de notas**.
3. Cambia **solo el valor** que hay después del `=` y guarda.
4. Vuelve a abrir el panel desde el icono.

⚠️ **Cuidado al editar:** no borres espacios del principio de la línea, ni los `:` ni el `=`. Los decimales van con **punto** (`0.05`, no `0,05`). Los textos van entre comillas (`"ema"`). `0.01` significa 1 %.

### Ajustes principales

| Ajuste | Qué hace | Valor por defecto |
|---|---|---|
| `symbols` | Monedas que opera | `("BTC/USDT",)` · varias: `("BTC/USDT", "ETH/USDT", "SOL/USDT")` |
| `timeframe` | Tamaño de las velas | `"4h"` |
| `fast` / `slow` | Medias móviles | `20` / `50` |
| `ma_type` | Tipo de media | `"ema"` |
| `trend_filter` | Solo compra sobre la media de N velas (0 = no) | `200` |
| `adx_min` | Solo compra con tendencia clara (0 = no) | `20` |
| `stop_mode` | `"atr"` (según volatilidad) o `"pct"` (porcentaje fijo) | `"atr"` |
| `atr_stop_mult` | Stop inicial a N × ATR | `2.5` |
| `atr_trail_mult` | Trailing a N × ATR del máximo (0 = no) | `3.0` |
| `stop_loss` / `trailing_stop` | Stops en % (modo `"pct"`) | `0.03` / `0` |
| `take_profit` | Vender al ganar este % (0 = dejar correr) | `0` |
| `risk_per_trade` | Pérdida máxima por operación | `0.01` (1 %) |
| `position_pct` | Tope de capital en una sola compra | `0.95` |
| `max_open_positions` | Monedas con compra abierta a la vez | `3` |
| `max_drawdown` | Se detiene si pierdes este % en total | `0.20` |
| `exchange_stops` | Poner el stop dentro de Binance (modo real) | `True` |
| `paper_balance` | Saldo ficticio del simulado | `1000.0` |

> 💡 Con **varias monedas**, baja `position_pct` (por ejemplo a `0.4`) para que una sola no se quede con todo el dinero.
> 💡 Antes de cambiar algo, pruébalo con el backtest (Parte 6).

---

## 11. Que funcione siempre: arranque automático y servidor

### Arranque automático al encender el PC

- **Activar:** doble clic en `autoarranque-activar.bat`.
- **Quitar:** doble clic en `autoarranque-quitar.bat`.

Con el arranque automático, al encender el PC el panel se abre en segundo plano (sin ventana) y, si el bot estaba en marcha, continúa solo. Para verlo, doble clic en el icono del escritorio.

### Servidor en la nube (opcional, avanzado)

Si no quieres tener tu PC encendido siempre, puedes alquilar un servidor Linux por unos 4–6 €/mes (Hetzner, Contabo, OVH...). Elige uno en **Europa** (Binance bloquea algunos países, como EE. UU.). Instrucciones resumidas, con **Ubuntu 24.04**:

```
apt update && apt install -y python3-venv git
adduser bot
su - bot
git clone https://github.com/solertesting-prog/BINANCE-BOT.git trading-bot
cd trading-bot && python3 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env
exit
sed 's/usuario/bot/g' /home/bot/trading-bot/deploy/trading-bot.service > /etc/systemd/system/trading-bot.service
systemctl daemon-reload && systemctl enable --now trading-bot
```

Comprueba con `systemctl status trading-bot` (debe poner `active (running)`) y mira el registro con `journalctl -u trading-bot -f`. En el servidor el bot funciona sin panel; el estado se consulta con `venv/bin/python bot.py --status`.

---

## 12. Problemas frecuentes y soluciones

### Al hacer doble clic en el icono no pasa nada
- Espera unos segundos: el panel tarda un poco en arrancar.
- Abre tú el navegador en **http://127.0.0.1:8765**.
- Si sigue sin abrir, mira si hay un archivo **`panel_error.txt`** en la carpeta del bot: ahí está el motivo. Cópialo y pregunta a Claude.
- Prueba con `arrancar-bot.bat`, que muestra los errores en pantalla.

### El panel pone un aviso rojo "No se pudo conectar con Binance"
- Comprueba tu conexión a internet.
- Si estás en modo real: revisa las claves en `.env` (sin espacios), que tengas activado **"Spot & Margin Trading"**, y que `TESTNET` sea `true` con claves de testnet y `false` con claves reales.
- Error **451** o *restricted location*: Binance bloquea tu ubicación (por ejemplo, servidores en EE. UU.).

### "python" no se reconoce como un comando
No marcaste **"Add python.exe to PATH"**. Vuelve a abrir el instalador de Python → **Modify** → *Next* → marca **"Add Python to environment variables"** → *Install*. Después, repite `instalar.bat`.

### `Timestamp for this request is outside of the recvWindow`
El reloj de tu PC no está en hora: *Configuración → Hora e idioma → Fecha y hora* → **"Sincronizar ahora"**.

### "Saldo insuficiente para comprar"
No hay USDT suficiente en tu cuenta **Spot**, o la compra calculada es menor que el mínimo de Binance. Añade USDT o sube `risk_per_trade`.

### "No se pudo colocar el stop en Binance"
Suele pasar con cantidades muy pequeñas (por debajo del mínimo de Binance). El bot **sigue vigilando el precio por su cuenta**, pero esa protección solo funciona con el PC encendido. Usa importes algo mayores.

### Banner rojo "Interruptor de seguridad activado"
El bot perdió más del límite (20 %), vendió todo y se paró para protegerte. **Piensa qué ha pasado antes de seguir.** Para continuar, pulsa **Reactivar** y luego **Arrancar**.

### El bot lleva días sin operar
Es normal con velas de 4 horas y los filtros activados. Mira en el **Registro** del panel que siga apareciendo "vela … cerrada" cada 4 horas.

### El puerto 8765 está ocupado
Añade `PANEL_PORT=8766` al archivo `.env` y abre el panel en **http://127.0.0.1:8766**.

### Otro error
Copia el mensaje (del panel, de `bot.log` o de `panel_error.txt`) y pregúntale a Claude.

---

## 13. Resumen de archivos

| Archivo | Para qué sirve |
|---|---|
| 🖱️ **Icono "Trading Bot"** (escritorio) | Abre el panel. Es lo único que necesitas usar a diario |
| `instalar.bat` | Instala o actualiza todo (repetirlo no borra tus datos) |
| `abrir-panel.bat` | Igual que el icono del escritorio |
| `backtest.bat` | Prueba la estrategia con el último año y abre el informe |
| `autoarranque-activar.bat` / `autoarranque-quitar.bat` | Abrir el panel solo al encender el PC |
| `arrancar-bot.bat` / `estado-bot.bat` | Modo consola sin panel (alternativa) |
| `.env` | Tus claves y el modo (simulado / testnet / real). **Privado** |
| `config.py` | La estrategia y la gestión del riesgo |
| `state.json` | Lo que recuerda el bot (posiciones abiertas, saldo simulado) |
| `trades_log.csv` | Todas las operaciones cerradas (se abre con Excel) |
| `bot.log` | Registro detallado de todo lo que hace |

### Actualizar a una versión nueva

1. Pulsa ⏻ en el panel.
2. Descarga el ZIP nuevo de GitHub y copia sus archivos **encima** de tu carpeta `binance-bot`, reemplazando. **No borres** `.env`, `state.json` ni `trades_log.csv`, y si modificaste `config.py`, guárdalo antes.
3. Doble clic en `instalar.bat`.

---

## Anexo: instalación en Mac

1. Instala Python desde **https://www.python.org/downloads/** y, al terminar, haz doble clic en **"Install Certificates.command"** (en la carpeta de Python que se abre).
2. Descarga y descomprime el bot en *Documentos* (Parte 3).
3. Abre **Terminal**, escribe `cd ` (con espacio), arrastra la carpeta del bot a la ventana y pulsa Enter.
4. Ejecuta, uno a uno:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   python -m pytest tests -q
   python panel.py
   ```
5. El panel se abre en el navegador. Para volver a abrirlo otro día: Terminal → `cd` a la carpeta → `source venv/bin/activate` → `python panel.py`.
6. El backtest se lanza con `python backtest.py --html informe.html` y se abre con `open informe.html`. El archivo `.env` se edita con `open -e .env`.

---

> ⚠️ **Aviso final:** este bot es una herramienta, no una recomendación de inversión. Los resultados pasados no garantizan los futuros. Las criptomonedas son muy volátiles. Usa solo dinero que puedas permitirte perder.
