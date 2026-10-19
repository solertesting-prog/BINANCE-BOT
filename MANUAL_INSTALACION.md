# 📘 Manual del Trading Bot, paso a paso

Funciona con **Binance, Kraken, Coinbase, OKX, Bybit, KuCoin, Bitget, Bitvavo, Bitfinex, Gate.io, Crypto.com, MEXC, HTX, Bitstamp** y muchos más (la lista completa está en el asistente).

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
5. [Conectar tu exchange (asistente)](#5-conectar-tu-exchange-asistente)
6. [El panel de control](#6-el-panel-de-control)
7. [Probar la estrategia con datos pasados (backtest)](#7-probar-la-estrategia-con-datos-pasados-backtest)
8. [Recibir avisos en el móvil por Telegram](#8-recibir-avisos-en-el-móvil-por-telegram)
9. [Probar con la testnet](#9-probar-con-la-testnet)
10. [Pasar a dinero real](#10-pasar-a-dinero-real)
11. [Ajustes avanzados de la estrategia](#11-ajustes-avanzados-de-la-estrategia)
12. [Que funcione siempre: arranque automático y servidor](#12-que-funcione-siempre-arranque-automático-y-servidor)
13. [Problemas frecuentes y soluciones](#13-problemas-frecuentes-y-soluciones)
14. [Resumen de archivos](#14-resumen-de-archivos)

---

## 1. Qué es y cómo funciona

El bot **compra y vende criptomonedas solo** en tu exchange, siguiendo unas reglas fijas:

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
6. Se abre el **panel** en tu navegador y, la primera vez, el **asistente de configuración** (Parte 5). 🎉

A partir de ahora, para abrir el bot **solo tienes que hacer doble clic en el icono "Trading Bot" del escritorio**.

---

## 5. Conectar tu exchange (asistente)

La primera vez que abres el panel aparece un asistente de 5 pasos. Puedes volver a abrirlo cuando quieras con el botón **⚙ Configuración** de arriba.

**1. Exchange.** Elige el tuyo. Cada uno muestra etiquetas:
- **Testnet**: tiene entorno de pruebas con dinero de mentira.
- **Stop en el exchange**: permite dejar el stop loss puesto dentro del exchange, de modo que protege aunque tu PC se apague.
- **No compatible**: el bot no puede funcionar ahí y te dice por qué. Por ejemplo, **bitFlyer** no ofrece velas históricas, que el bot necesita para calcular la estrategia.

En "¿Otro exchange?" tienes la lista completa; el asistente te dice si cada uno es compatible.

**2. Modo.**
- **Simulado** (recomendado para empezar): precios reales de ese exchange y dinero ficticio. Eliges el saldo inicial. No necesita claves.
- **Testnet**: órdenes de verdad en el entorno de pruebas (solo si el exchange lo tiene).
- **Dinero real.**

**3. Claves** (solo para testnet o dinero real). El asistente te explica cómo crearlas y te pide exactamente los datos que necesita ese exchange: **API Key** y **Secret Key**, y en algunos (OKX, KuCoin, Bitget…) también la **Passphrase**.
- Permisos de la clave: ✅ **Lectura** · ✅ **Trading spot** · ❌ **Retiros: nunca**.
- Pulsa **🔌 Probar conexión**: si todo está bien, verás ✓ y tu saldo. No te deja seguir hasta que funcione.
- Las claves se guardan **solo en el archivo `.env` de tu ordenador**. Al volver a abrir el asistente solo verás los 4 últimos caracteres. Si dejas un campo vacío, se mantiene la clave guardada.

**4. Monedas.**
- **Moneda de cuenta**: con qué compras (USDT, USDC, EUR, USD…). Todas las monedas del bot deben usar la misma.
- **Monedas a operar**: hasta 10. Busca por nombre y pulsa para añadir o quitar.
- **Velas**: 1 hora, 4 horas (recomendado) o 1 día.
- **Riesgo por operación**: 0,5 %, 1 % (recomendado) o 2 %. Es lo máximo que pierdes en una operación si salta el stop.

**5. Confirmar.** Revisa el resumen y los avisos, y pulsa **Guardar y aplicar**.

> ℹ️ Si cambias de exchange o de modo, el bot se queda **parado**: pulsa **▶ Arrancar** cuando quieras. Si solo cambias monedas o riesgo y estaba en marcha, sigue funcionando con la nueva configuración.
> 🛡️ No se puede cambiar de exchange o de modo **con posiciones abiertas**: ciérralas antes.

---

## 6. El panel de control

El panel se abre en tu navegador en la dirección **http://127.0.0.1:8765**. Solo funciona en tu ordenador: nadie más puede verlo ni controlarlo.

### Qué ves

| Zona | Qué muestra |
|---|---|
| **Barra superior** | Modo (**Simulado** / **Testnet** / **Dinero real**), exchange, estado (● En marcha / Parado) y los botones |
| **Capital** | Lo que vale tu cuenta ahora (dinero + monedas compradas) |
| **Resultado total** | Cuánto has ganado o perdido desde que empezaste |
| **Disponible** | Dinero sin invertir (en tu moneda de cuenta: USDT, EUR…) |
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
| **⚙ Configuración** | Abre el asistente: exchange, modo, claves y monedas |
| **▶ Arrancar** | El bot empieza a operar |
| **■ Parar** | El bot deja de abrir y cerrar operaciones. Las posiciones abiertas se mantienen (en modo real, su stop sigue puesto en el exchange) |
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

Pulsa ⏻ para apagar el panel y borra los archivos `state.json` y `trades_log.csv` de la carpeta del bot. Al abrirlo de nuevo, empieza con el saldo ficticio elegido en el asistente. (Cambiar el saldo ficticio en el asistente también reinicia la simulación, si no hay posiciones abiertas.)

---

## 7. Probar la estrategia con datos pasados (backtest)

Un **backtest** simula qué habría pasado si el bot hubiera funcionado durante el último año, usando precios reales de tu exchange.

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

## 8. Recibir avisos en el móvil por Telegram

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

## 9. Probar con la testnet

La **testnet** es una copia del exchange con dinero de mentira. Sirve para comprobar que el bot envía **órdenes reales** (incluido el stop puesto en el exchange) sin arriesgar nada. Solo la tienen algunos exchanges (en el asistente llevan la etiqueta **Testnet**).

1. Crea claves en la web de pruebas del exchange. Son **distintas** de las reales. En Binance: **https://testnet.binance.vision/** → "Log In with GitHub" → "Generate HMAC_SHA256 Key".
2. En el panel: **⚙ Configuración** → tu exchange → modo **Testnet** → pega las claves → **Probar conexión** → elige monedas → **Guardar y aplicar**.
3. Arriba pondrá **Testnet**. Pulsa **▶ Arrancar**.

---

## 10. Pasar a dinero real

> ⚠️ **Antes de seguir, sé honesto contigo:**
> - ¿Lo has tenido **varias semanas** en simulado y los resultados te convencen?
> - ¿Vas a usar **solo dinero que puedes permitirte perder entero**?
>
> Si alguna respuesta es "no", espera. Ningún bot garantiza ganancias.

### 10.1 Crear las claves de API en tu exchange

En la web de tu exchange, busca la sección **API** en los ajustes de la cuenta (en Binance: icono de perfil → **Gestión de API** → **Crear API**). Crea una clave y deja los permisos **exactamente así**:
- ✅ **Lectura**
- ✅ **Trading spot**
- ❌ **Retiros → NUNCA.** Así, aunque alguien robara tus claves, no podría sacar dinero.
- ❌ Todo lo demás (futuros, margen, transferencias), desactivado.

Si el exchange lo permite y tienes IP fija (o usas un servidor), restringe la clave a esa IP. Copia la Secret Key en el momento: la mayoría de exchanges solo la muestran una vez.

### 10.2 Configurar el bot

En el panel: **⚙ Configuración** → tu exchange → **Dinero real** → pega las claves → **Probar conexión** (debe salir ✓ y tu saldo) → elige monedas → **Guardar y aplicar**. Arriba pondrá **Dinero real** en rojo. Pulsa **▶ Arrancar** cuando quieras empezar.

### 10.3 Preparar la cuenta

- El bot usa el saldo de tu **moneda de cuenta** (USDT, EUR…) en la cuenta **Spot**. **Deja ahí solo lo que quieras que use**; el resto, muévelo a otra cartera del exchange.
- Solo vende lo que **él** ha comprado: no toca otras monedas que tengas.
- **Empieza con poco** (por ejemplo 100–200). Con riesgo del 1 %, las compras serán pequeñas, y cada exchange exige un importe mínimo por orden (normalmente 5–10 USDT o EUR).

### 10.4 Protecciones en modo real

- **Stop puesto en el exchange:** al comprar, el bot deja una orden de stop loss **dentro del exchange**. Si tu PC se apaga o pierde internet, el exchange venderá igualmente si el precio cae hasta ahí. El panel lo indica con "· en el exchange". Cuando el trailing stop sube, el bot mueve esa orden. En Binance usa su orden nativa STOP_LOSS_LIMIT y en los demás la orden stop estándar. En cualquier caso, **compruébalo primero en testnet o con poco dinero**: la lógica está probada con un exchange simulado, no con dinero real en cada exchange. Si el exchange no permite stops (por ejemplo Bitstamp), el bot vigila el precio solo mientras el PC esté encendido.
- **Doble vigilancia:** además, el bot vigila el precio cada minuto por su cuenta.
- **Reconciliación:** al arrancar, comprueba si mientras estaba apagado saltó algún stop o vendiste algo a mano, y lo apunta.
- **Reintentos:** si falla la conexión, reintenta las consultas. Las órdenes de compra o venta **nunca** se repiten a ciegas.

### 🔒 Reglas de seguridad

- **Nunca compartas el archivo `.env`** ni hagas capturas donde se vean tus claves. No se sube a GitHub (está excluido a propósito).
- Si crees que alguien ha visto tus claves: en la web del exchange, **bórralas** y crea otras.
- No tengas el bot funcionando a la vez en dos ordenadores con la misma cuenta.

---

## 11. Ajustes avanzados de la estrategia

Exchange, modo, claves, monedas, velas y riesgo se cambian desde **⚙ Configuración** en el panel. El resto de la estrategia está en **`config.py`**.

1. Pulsa ⏻ en el panel.
2. Clic derecho sobre `config.py` → *Abrir con* → **Bloc de notas**.
3. Cambia **solo el valor** que hay después del `=` y guarda.
4. Vuelve a abrir el panel desde el icono.

⚠️ **Cuidado al editar:** no borres espacios del principio de la línea, ni los `:` ni el `=`. Los decimales van con **punto** (`0.05`, no `0,05`). Los textos van entre comillas (`"ema"`). `0.01` significa 1 %.

### Ajustes principales

| Ajuste | Qué hace | Valor por defecto |
|---|---|---|
| `fast` / `slow` | Medias móviles | `20` / `50` |
| `ma_type` | Tipo de media | `"ema"` |
| `trend_filter` | Solo compra sobre la media de N velas (0 = no) | `200` |
| `adx_min` | Solo compra con tendencia clara (0 = no) | `20` |
| `stop_mode` | `"atr"` (según volatilidad) o `"pct"` (porcentaje fijo) | `"atr"` |
| `atr_stop_mult` | Stop inicial a N × ATR | `2.5` |
| `atr_trail_mult` | Trailing a N × ATR del máximo (0 = no) | `3.0` |
| `stop_loss` / `trailing_stop` | Stops en % (modo `"pct"`) | `0.03` / `0` |
| `take_profit` | Vender al ganar este % (0 = dejar correr) | `0` |
| `position_pct` | Tope de capital en una sola compra | `0.95` |
| `max_open_positions` | Monedas con compra abierta a la vez | `3` |
| `max_drawdown` | Se detiene si pierdes este % en total | `0.20` |
| `exchange_stops` | Poner el stop dentro del exchange (modo real) | `True` |

> 💡 Con **varias monedas**, baja `position_pct` (por ejemplo a `0.4`) para que una sola no se quede con todo el dinero.
> 💡 Antes de cambiar algo, pruébalo con el backtest (Parte 6).

---

## 12. Que funcione siempre: arranque automático y servidor

### Arranque automático al encender el PC

- **Activar:** doble clic en `autoarranque-activar.bat`.
- **Quitar:** doble clic en `autoarranque-quitar.bat`.

Con el arranque automático, al encender el PC el panel se abre en segundo plano (sin ventana) y, si el bot estaba en marcha, continúa solo. Para verlo, doble clic en el icono del escritorio.

### Servidor en la nube (opcional, avanzado)

Si no quieres tener tu PC encendido siempre, puedes alquilar un servidor Linux por unos 4–6 €/mes (Hetzner, Contabo, OVH...). Elige uno en **Europa** (algunos exchanges, como Binance, bloquean ciertos países como EE. UU.). Configura antes el bot en tu PC con el asistente y copia al servidor los archivos `.env` y `settings.json`. Instrucciones resumidas, con **Ubuntu 24.04**:

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

## 13. Problemas frecuentes y soluciones

### Al hacer doble clic en el icono no pasa nada
- Espera unos segundos: el panel tarda un poco en arrancar.
- Abre tú el navegador en **http://127.0.0.1:8765**.
- Si sigue sin abrir, mira si hay un archivo **`panel_error.txt`** en la carpeta del bot: ahí está el motivo. Cópialo y pregunta a Claude.
- Prueba con `arrancar-bot.bat`, que muestra los errores en pantalla.

### El panel pone un aviso rojo "No se pudo conectar con el exchange"
- Comprueba tu conexión a internet.
- Abre **⚙ Configuración** y pulsa **Probar conexión**: te dirá qué falla (claves incorrectas, faltan permisos, reloj desajustado…).
- Las claves de **testnet** y las **reales** son distintas: usa cada una en su modo.
- Error **451** o *restricted location*: el exchange bloquea tu ubicación (por ejemplo, Binance con servidores en EE. UU.).

### Mi exchange aparece como "No compatible"
El asistente explica el motivo. El más habitual: el exchange no ofrece **velas históricas** a través de su API (le pasa a **bitFlyer**), sin las cuales el bot no puede calcular la estrategia. Usa otro exchange de la lista.

### "python" no se reconoce como un comando
No marcaste **"Add python.exe to PATH"**. Vuelve a abrir el instalador de Python → **Modify** → *Next* → marca **"Add Python to environment variables"** → *Install*. Después, repite `instalar.bat`.

### `Timestamp for this request is outside of the recvWindow`
El reloj de tu PC no está en hora: *Configuración → Hora e idioma → Fecha y hora* → **"Sincronizar ahora"**.

### "Saldo insuficiente para comprar"
No hay saldo suficiente de tu moneda de cuenta en **Spot**, o la compra calculada es menor que el mínimo del exchange. Añade saldo o sube el riesgo por operación en ⚙ Configuración.

### "No se pudo colocar el stop en …"
Suele pasar con cantidades muy pequeñas (por debajo del mínimo del exchange) o si el exchange no admite ese tipo de orden. El bot **sigue vigilando el precio por su cuenta**, pero esa protección solo funciona con el PC encendido. Usa importes algo mayores.

### Banner rojo "Interruptor de seguridad activado"
El bot perdió más del límite (20 %), vendió todo y se paró para protegerte. **Piensa qué ha pasado antes de seguir.** Para continuar, pulsa **Reactivar** y luego **Arrancar**.

### El bot lleva días sin operar
Es normal con velas de 4 horas y los filtros activados. Mira en el **Registro** del panel que siga apareciendo "vela … cerrada" cada 4 horas.

### El puerto 8765 está ocupado
Añade `PANEL_PORT=8766` al archivo `.env` y abre el panel en **http://127.0.0.1:8766**.

### Otro error
Copia el mensaje (del panel, de `bot.log` o de `panel_error.txt`) y pregúntale a Claude.

---

## 14. Resumen de archivos

| Archivo | Para qué sirve |
|---|---|
| 🖱️ **Icono "Trading Bot"** (escritorio) | Abre el panel. Es lo único que necesitas usar a diario |
| `instalar.bat` | Instala o actualiza todo (repetirlo no borra tus datos) |
| `abrir-panel.bat` | Igual que el icono del escritorio |
| `backtest.bat` | Prueba la estrategia con el último año y abre el informe |
| `autoarranque-activar.bat` / `autoarranque-quitar.bat` | Abrir el panel solo al encender el PC |
| `arrancar-bot.bat` / `estado-bot.bat` | Modo consola sin panel (alternativa) |
| `.env` | Tus claves y el modo (simulado / testnet / real). Lo rellena el asistente. **Privado** |
| `settings.json` | Exchange, monedas, velas y riesgo elegidos en el asistente |
| `config.py` | Ajustes avanzados de la estrategia |
| `state.json` | Lo que recuerda el bot (posiciones abiertas, saldo simulado) |
| `trades_log.csv` | Todas las operaciones cerradas (se abre con Excel) |
| `bot.log` | Registro detallado de todo lo que hace |

### Actualizar a una versión nueva

1. Pulsa ⏻ en el panel.
2. Descarga el ZIP nuevo de GitHub y copia sus archivos **encima** de tu carpeta `binance-bot`, reemplazando. **No borres** `.env`, `settings.json`, `state.json` ni `trades_log.csv`, y si modificaste `config.py`, guárdalo antes.
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
6. La primera vez se abre el asistente para conectar tu exchange (Parte 5). El backtest se lanza con `python backtest.py --html informe.html` y se abre con `open informe.html`.

---

> ⚠️ **Aviso final:** este bot es una herramienta, no una recomendación de inversión. Los resultados pasados no garantizan los futuros. Las criptomonedas son muy volátiles. Usa solo dinero que puedas permitirte perder.
