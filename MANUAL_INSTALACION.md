# 📘 Manual de instalación del bot, paso a paso

Este manual está pensado para alguien que **nunca ha programado ni usado la terminal**. Sigue los pasos en orden, sin saltarte ninguno, y copia los comandos tal cual.

Hay instrucciones para **Windows** 🪟 y para **Mac** 🍎. Haz solo las de tu sistema.

> ⏱️ **Tiempo:** unos 30–45 minutos la primera vez.
> 💸 **Dinero:** no necesitas poner dinero para probarlo. Hasta la Parte 9 todo es simulado.

---

## Índice

1. [Antes de empezar: tres palabras que debes conocer](#1-antes-de-empezar-tres-palabras-que-debes-conocer)
2. [Instalar Python](#2-instalar-python)
3. [Descargar el bot](#3-descargar-el-bot)
4. [Abrir la terminal dentro de la carpeta del bot](#4-abrir-la-terminal-dentro-de-la-carpeta-del-bot)
5. [Preparar el bot (solo la primera vez)](#5-preparar-el-bot-solo-la-primera-vez)
6. [Primera prueba: el backtest](#6-primera-prueba-el-backtest)
7. [Buscar la mejor configuración (opcional)](#7-buscar-la-mejor-configuración-opcional)
8. [Arrancar el bot en modo simulado](#8-arrancar-el-bot-en-modo-simulado)
9. [Recibir avisos en el móvil por Telegram (opcional)](#9-recibir-avisos-en-el-móvil-por-telegram-opcional)
10. [Probar con la testnet de Binance](#10-probar-con-la-testnet-de-binance)
11. [Pasar a dinero real](#11-pasar-a-dinero-real)
12. [Cambiar la configuración](#12-cambiar-la-configuración)
13. [Dejarlo funcionando 24 horas (servidor)](#13-dejarlo-funcionando-24-horas-servidor)
14. [Problemas frecuentes y soluciones](#14-problemas-frecuentes-y-soluciones)
15. [Chuleta de comandos](#15-chuleta-de-comandos)

---

## 1. Antes de empezar: tres palabras que debes conocer

- **Terminal**: una ventana negra (o blanca) donde escribes órdenes en lugar de hacer clic. En Windows se llama "Símbolo del sistema" o `cmd`; en Mac, "Terminal".
- **Comando**: una línea de texto que escribes en la terminal y ejecutas pulsando **Enter**. En este manual aparecen en cajas grises, así:
  ```
  python --version
  ```
  Puedes copiarlo y pegarlo. En la terminal de Windows se pega con **clic derecho** o `Ctrl + V`; en Mac con `Cmd + V`.
- **Carpeta del bot**: la carpeta donde están los archivos del bot (`bot.py`, `config.py`...). Casi todos los comandos hay que ejecutarlos **estando dentro de esa carpeta**.

> 💡 Si un comando muestra un error, **no sigas**. Ve a la [Parte 14](#14-problemas-frecuentes-y-soluciones), donde están los errores más comunes.

---

## 2. Instalar Python

Python es el "motor" que hace funcionar el bot. Solo se instala una vez.

### 🪟 Windows

1. Abre el navegador y entra en **https://www.python.org/downloads/**
2. Pulsa el botón amarillo grande **"Download Python 3.x.x"** (cualquier versión 3.10 o superior sirve).
3. Abre el archivo descargado (está en la carpeta *Descargas*).
4. ⚠️ **MUY IMPORTANTE:** en la primera pantalla del instalador, abajo, **marca la casilla "Add python.exe to PATH"**. Si no la marcas, nada funcionará después.
5. Pulsa **"Install Now"** y espera a que termine. Pulsa **"Close"**.

**Comprueba que funciona:**

1. Pulsa la tecla **Windows**, escribe `cmd` y pulsa **Enter**. Se abre una ventana negra.
2. Escribe esto y pulsa Enter:
   ```
   python --version
   ```
3. Debe salir algo como `Python 3.12.6`. ✅ Si sale eso, perfecto. Cierra la ventana.

❌ Si sale *"python no se reconoce como un comando..."*, es que no marcaste la casilla del paso 4. Vuelve a abrir el instalador, elige **"Modify"** → *Next* → marca **"Add Python to environment variables"** → *Install*. Cierra y vuelve a abrir la ventana negra.

### 🍎 Mac

1. Entra en **https://www.python.org/downloads/** y pulsa **"Download Python 3.x.x"**.
2. Abre el archivo `.pkg` descargado y pulsa **Continuar** en todas las pantallas hasta **Instalar**. Te pedirá tu contraseña del Mac.
3. Al terminar se abre una carpeta de Python. Haz **doble clic en "Install Certificates.command"** (esto evita errores de conexión más adelante). Se abre una ventana, espera a que diga *"[Process completed]"* y ciérrala.

**Comprueba que funciona:**

1. Pulsa `Cmd + Espacio`, escribe `Terminal` y pulsa Enter.
2. Escribe:
   ```
   python3 --version
   ```
3. Debe salir algo como `Python 3.12.6`. ✅

> 🍎 **En Mac, usa siempre `python3` en lugar de `python`** la primera vez (al crear el entorno, Parte 5). Después, con el entorno activado, ya funciona `python` a secas.

---

## 3. Descargar el bot

1. Entra en **https://github.com/solertesting-prog/BINANCE-BOT** (inicia sesión en GitHub si el repositorio es privado).
2. Pulsa el botón verde **"<> Code"** y después **"Download ZIP"**.
3. Ve a tu carpeta *Descargas* y **descomprime** el ZIP:
   - 🪟 Windows: clic derecho sobre el ZIP → **"Extraer todo..."** → *Extraer*.
   - 🍎 Mac: doble clic sobre el ZIP.
4. Se crea una carpeta llamada **`BINANCE-BOT-main`**. Muévela a un sitio fácil, por ejemplo a **Documentos**, y cámbiale el nombre a **`binance-bot`** (clic derecho → *Cambiar nombre*).

Al final debes tener una carpeta `Documentos/binance-bot` que dentro tiene archivos como `bot.py`, `config.py`, `README.md`...

> ⚠️ Comprueba que al abrir `binance-bot` ves directamente `bot.py`. Si ves **otra carpeta dentro** con el mismo nombre, entra en ella: esa es la buena.

---

## 4. Abrir la terminal dentro de la carpeta del bot

Esto lo harás **cada vez** que quieras usar el bot.

### 🪟 Windows (la forma más fácil)

1. Abre la carpeta `binance-bot` con el Explorador de archivos (donde ves `bot.py`).
2. Haz clic en la **barra de dirección** de arriba (donde pone algo como `Este equipo > Documentos > binance-bot`). El texto se vuelve azul.
3. **Borra lo que hay, escribe `cmd` y pulsa Enter.**
4. Se abre la ventana negra, ya colocada en la carpeta del bot. Verás algo como:
   ```
   C:\Users\TuNombre\Documents\binance-bot>
   ```

> 🪟 Usa **cmd** (Símbolo del sistema), no PowerShell. Los comandos de este manual están pensados para cmd.

### 🍎 Mac

1. Abre **Terminal** (`Cmd + Espacio` → `Terminal`).
2. Escribe `cd ` (las letras **c**, **d** y **un espacio**). **No pulses Enter todavía.**
3. Arrastra la carpeta `binance-bot` desde el Finder **y suéltala dentro de la ventana de Terminal**. Se escribe sola la ruta.
4. Ahora sí, pulsa **Enter**.

**Comprueba que estás en el sitio correcto** (Windows y Mac):

- 🪟 Windows: escribe `dir` y pulsa Enter.
- 🍎 Mac: escribe `ls` y pulsa Enter.

Debe aparecer una lista con `bot.py`, `config.py`, etc. ✅ Si no aparecen, no estás en la carpeta correcta; repite esta parte.

---

## 5. Preparar el bot (solo la primera vez)

> 🪟 **Atajo para Windows:** haz **doble clic en `instalar.bat`** dentro de la carpeta del bot. Hace automáticamente todos los pasos 5.1 a 5.5. Si al final pone `9 passed`, salta directamente a la Parte 6.
>
> Además tienes `backtest.bat` (Parte 6), `arrancar-bot.bat` (Parte 8) y `estado-bot.bat` (ver cómo va), que también funcionan con doble clic.
>
> Si prefieres hacerlo a mano (o usas Mac), sigue los pasos de abajo.

Con la terminal abierta **dentro de la carpeta del bot** (Parte 4), ejecuta estos comandos **uno a uno**, pulsando Enter después de cada uno y esperando a que termine.

### Paso 5.1 — Crear el "entorno virtual"

Es una cajita aislada donde se instalan las piezas que necesita el bot, sin ensuciar tu ordenador.

- 🪟 Windows:
  ```
  python -m venv venv
  ```
- 🍎 Mac:
  ```
  python3 -m venv venv
  ```

Tarda unos segundos y no muestra nada. Es normal. Aparecerá una carpeta nueva llamada `venv`.

### Paso 5.2 — Activar el entorno

- 🪟 Windows:
  ```
  venv\Scripts\activate
  ```
- 🍎 Mac:
  ```
  source venv/bin/activate
  ```

✅ Sabrás que ha funcionado porque al principio de la línea aparece **`(venv)`**, así:
```
(venv) C:\Users\TuNombre\Documents\binance-bot>
```

> 🔁 **Tendrás que activar el entorno cada vez que abras una terminal nueva** para usar el bot. Si no ves `(venv)` al principio, actívalo.

### Paso 5.3 — Instalar las piezas del bot

```
pip install -r requirements.txt
```

Saldrán muchas líneas de texto durante uno o dos minutos. Al final debe decir algo como `Successfully installed ccxt-... pandas-...`. ✅

(Si sale un aviso amarillo de *"A new release of pip is available"*, ignóralo; no es un error.)

### Paso 5.4 — Comprobar que todo funciona

```
python -m pytest tests -q
```

Debe terminar con algo como **`9 passed`**. ✅ Esto significa que el bot funciona correctamente en tu ordenador.

### Paso 5.5 — Crear tu archivo de configuración privada (`.env`)

El archivo `.env` guarda cosas privadas (como tus claves de Binance). Se crea copiando una plantilla:

- 🪟 Windows:
  ```
  copy .env.example .env
  ```
- 🍎 Mac:
  ```
  cp .env.example .env
  ```

Por ahora **no hace falta tocarlo**: viene preparado en modo simulado (`MODE=paper`), que no usa dinero ni claves.

> 👀 En Mac, los archivos que empiezan por punto (como `.env`) están ocultos en el Finder. Para verlos, pulsa `Cmd + Mayús + .` (punto) dentro de la carpeta.

🎉 **¡Instalación terminada!**

---

## 6. Primera prueba: el backtest

Un **backtest** simula qué habría pasado si el bot hubiera funcionado durante el último año, usando precios reales de Binance. No usa dinero.

Con la terminal en la carpeta del bot y `(venv)` activado:

```
python backtest.py --html informe.html
```

Tarda un poco la primera vez (descarga un año de precios de Bitcoin). Luego muestra un resumen como este:

```
=== Backtest BTC/USDT 1h | SMA 20/50 | SL 3.0% | TP 8.0% ===
Periodo:            2025-10-19 → 2026-10-19
Capital final:      1087.20 USDT
Rentabilidad:       +8.72%
Comprar y mantener: +15.30%
Máx. drawdown:      -12.40%
...
```

**Abre el informe con gráficos:**

- 🪟 Windows:
  ```
  start informe.html
  ```
- 🍎 Mac:
  ```
  open informe.html
  ```

Se abre en el navegador.

### ¿Cómo leo los resultados?

| Dato | Qué significa | Qué buscar |
|---|---|---|
| **Rentabilidad** | Cuánto habrías ganado o perdido | Positiva, claro |
| **Comprar y mantener** | Cuánto habrías ganado comprando Bitcoin el primer día sin hacer nada más | Lo ideal es que el bot gane más, o parecido pero con menos caídas |
| **Máx. drawdown** | La peor caída que habrías sufrido por el camino | Pregúntate: ¿aguantaría ver mi dinero bajar este %? |
| **Operaciones** | Cuántas compras-ventas hizo | Con menos de 20–30, el resultado puede ser suerte |
| **Profit factor** | Lo ganado entre lo perdido | Por encima de 1,3–1,5 empieza a ser interesante |

### Probar otras configuraciones

Puedes probar variantes sin tocar nada, añadiendo opciones al comando:

```
python backtest.py --ma ema --trend 200 --adx 20 --trailing 0.05 --tp 0
```

| Opción | Qué hace |
|---|---|
| `--days 730` | Prueba 2 años en lugar de 1 |
| `--timeframe 4h` | Usa velas de 4 horas en lugar de 1 hora |
| `--fast 10 --slow 30` | Cambia las medias móviles |
| `--ma ema` | Usa medias exponenciales (reaccionan antes) |
| `--trend 200` | Solo compra cuando el precio está por encima de la media de 200 |
| `--adx 20` | Solo compra cuando hay tendencia clara (evita mercados laterales) |
| `--trailing 0.05` | Vende si cae un 5 % desde el máximo alcanzado |
| `--sl 0.03` | Stop loss del 3 % |
| `--tp 0.08` | Take profit del 8 % (`--tp 0` lo desactiva) |
| `--symbol ETH/USDT` | Prueba con Ethereum u otra moneda |

---

## 7. Buscar la mejor configuración (opcional)

El **optimizador** prueba cientos de combinaciones automáticamente y, lo más importante, comprueba si funcionan en datos que **no ha visto** (para no engañarte con resultados de pura suerte).

```
python optimize.py
```

Tarda entre 1 y 5 minutos. Al final verás algo así:

```
=== Resultado fuera de muestra (lo que habría pasado de verdad) ===
  Optimizando en cada tramo: +11.9%
  Config actual (config.py): -12.8%
  Comprar y mantener:        -1.2%
```

👉 **La línea importante es "Resultado fuera de muestra".** Ignora los números espectaculares del "Top 5": suelen ser casualidad.

Si te sale un aviso ⚠️ de que *los parámetros cambian mucho entre tramos*, significa que no hay una configuración fiable: mejor no cambiar nada.

Si quieres aplicar una configuración, ve a la [Parte 12](#12-cambiar-la-configuración).

---

## 8. Arrancar el bot en modo simulado

Ahora el bot funcionará **en tiempo real** con precios reales de Binance, pero con **1000 USDT ficticios**. Es la mejor forma de ver cómo se comporta antes de arriesgar nada.

```
python bot.py
```

Verás algo como:

```
2026-10-19 11:00:05 INFO 🤖 Bot iniciado | BTC/USDT 1h | SMA 20/50 | SL 3.0% | TP 8.0% | modo paper
2026-10-19 11:00:06 INFO Vela cerrada 2026-10-19 10:00 | precio 67234.10 | señal 0 | capital 1000.00
```

- **"señal 0"** significa "no hacer nada". Es lo normal la mayor parte del tiempo. El bot puede pasar **días** sin operar.
- Revisa el precio cada minuto y analiza la estrategia cada hora.
- Cuando compre o venda, lo verás con 🟢 COMPRA o 🔴 VENTA.

### ⚠️ Reglas importantes

- **No cierres la ventana**: si la cierras, el bot se para.
- **Tu ordenador no debe apagarse ni suspenderse.**
  - 🪟 Windows: *Configuración → Sistema → Inicio/apagado y suspensión* → pon "Nunca" en suspensión (al menos cuando está enchufado).
  - 🍎 Mac: *Ajustes del Sistema → Batería* (o *Pantalla*) → *Opciones* → activa "Evitar la suspensión automática cuando la pantalla esté apagada".
- **Para parar el bot**: pulsa `Ctrl + C` en la ventana. Puedes volver a arrancarlo cuando quieras; **recuerda dónde lo dejó** (lo guarda en `state.json`).

### Ver cómo va

Abre **otra** terminal en la carpeta del bot (Parte 4), activa el entorno (Paso 5.2) y escribe:

```
python bot.py --status
```

Te muestra si tiene una compra abierta, el stop actual, el saldo simulado y las últimas operaciones.

También puedes abrir el archivo **`trades_log.csv`** con Excel para ver todas las operaciones cerradas.

> 📅 **Recomendación:** déjalo en modo simulado **varias semanas** antes de pensar en dinero real.

### Volver a empezar desde cero

Para el bot (`Ctrl + C`) y borra los archivos `state.json` y `trades_log.csv` de la carpeta del bot. Al arrancarlo de nuevo, empieza con 1000 USDT ficticios.

---

## 9. Recibir avisos en el móvil por Telegram (opcional)

Así te llega un mensaje al móvil cada vez que el bot compra o vende, y un resumen diario.

1. Instala **Telegram** en el móvil si no lo tienes.
2. Busca el usuario **@BotFather** (tiene una marca azul de verificado) y ábrelo.
3. Escríbele `/newbot`.
4. Te pedirá un **nombre** (pon el que quieras, por ejemplo `Mi bot trading`) y luego un **usuario** que termine en `bot` (por ejemplo `albert_trading_bot`).
5. Te responderá con un mensaje que contiene un **token**, algo como:
   `7123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   Cópialo. ⚠️ No lo compartas con nadie.
6. Busca tu bot nuevo en Telegram (por el usuario que le pusiste), ábrelo y pulsa **Iniciar** (o escríbele "hola").
7. En el navegador del ordenador, abre esta dirección **cambiando `TU_TOKEN` por tu token**:
   ```
   https://api.telegram.org/botTU_TOKEN/getUpdates
   ```
   (Ojo: entre `bot` y el token **no hay espacio ni barra**.)
8. Verás un texto. Busca `"chat":{"id":` seguido de un número, por ejemplo `"chat":{"id":123456789`. Ese número es tu **chat_id**.
   (Si sale vacío `"result":[]`, escribe otro mensaje a tu bot y recarga la página.)
9. Abre el archivo `.env`:
   - 🪟 Windows: `notepad .env`
   - 🍎 Mac: `open -e .env`
10. Rellena estas dos líneas (sin espacios ni comillas):
    ```
    TELEGRAM_TOKEN=7123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TELEGRAM_CHAT_ID=123456789
    ```
11. **Guarda** el archivo (`Ctrl + S` o `Cmd + S`) y ciérralo.
12. Si el bot estaba en marcha, páralo (`Ctrl + C`) y arráncalo otra vez con `python bot.py`. Te llegará un mensaje "🤖 Bot iniciado". ✅

---

## 10. Probar con la testnet de Binance

La **testnet** es una copia de Binance con dinero de mentira. Sirve para comprobar que el bot envía órdenes reales correctamente sin arriesgar nada.

1. Entra en **https://testnet.binance.vision/**
2. Pulsa **"Log In with GitHub"** e inicia sesión con tu cuenta de GitHub.
3. Pulsa **"Generate HMAC_SHA256 Key"**.
4. Escribe una descripción cualquiera (por ejemplo `bot`) y pulsa **Generate**.
5. Te mostrará **API Key** y **Secret Key**. ⚠️ **Copia las dos ahora**: la Secret Key solo se muestra una vez.
6. Abre el archivo `.env` (`notepad .env` en Windows, `open -e .env` en Mac) y déjalo así:
   ```
   MODE=live
   TESTNET=true
   BINANCE_API_KEY=pega_aqui_tu_api_key
   BINANCE_API_SECRET=pega_aqui_tu_secret_key
   ```
7. Guarda y cierra.
8. Borra `state.json` y `trades_log.csv` si existen (para no mezclar con el modo simulado).
9. Arranca el bot:
   ```
   python bot.py
   ```
   Debe decir `modo live (testnet)`. ✅

La testnet te da saldo ficticio automáticamente. Ojo: a veces Binance reinicia la testnet y borra los saldos; es normal.

---

## 11. Pasar a dinero real

> ⚠️ **Antes de seguir, sé honesto contigo:**
> - ¿Lo has tenido **varias semanas** en modo simulado?
> - ¿Los resultados te convencen?
> - ¿Vas a usar **solo dinero que puedes permitirte perder entero**?
>
> Si alguna respuesta es "no", espera. Ningún bot garantiza ganancias.

### 11.1 Crear las claves de API en Binance

1. Entra en **https://www.binance.com** con tu cuenta (debe estar verificada).
2. Pulsa en tu **icono de perfil** (arriba a la derecha) → **"Gestión de API"** (*API Management*).
3. Pulsa **"Crear API"** → elige **"Generada por el sistema"** → ponle un nombre (por ejemplo `bot-trading`).
4. Completa la verificación de seguridad (código de email, SMS o app).
5. Copia la **API Key** y la **Secret Key**. ⚠️ La Secret Key solo se muestra una vez.
6. Pulsa **"Editar restricciones"** y deja los permisos **exactamente así**:
   - ✅ **Activar lectura** (Enable Reading)
   - ✅ **Activar el trading spot y de margen** (Enable Spot & Margin Trading)
   - ❌ **Activar retiros** (Enable Withdrawals) → **NUNCA lo actives.** Así, aunque alguien robara tus claves, no podría sacar dinero de tu cuenta.
   - ❌ Todo lo demás, desactivado.
7. **Restricción de IP** (muy recomendable si usas un servidor con IP fija): elige "Restringir el acceso solo a IPs de confianza" y pon la IP del servidor. En casa la IP suele cambiar, así que puedes dejarlo sin restringir, pero entonces es aún más importante no tener activados los retiros.
8. Guarda.

### 11.2 Configurar el bot

1. Abre `.env` y déjalo así:
   ```
   MODE=live
   TESTNET=false
   BINANCE_API_KEY=tu_api_key_real
   BINANCE_API_SECRET=tu_secret_key_real
   ```
2. Guarda y cierra.
3. Borra `state.json` y `trades_log.csv` (para empezar limpio).

### 11.3 Preparar la cuenta

- El bot opera con el **USDT libre** de tu cuenta Spot. Usa el **95 %** de ese saldo en cada compra.
- 👉 **Deja en la cuenta Spot solo los USDT que quieras que use el bot.** El resto, muévelo a otra cartera (por ejemplo, a *Fondos* o *Earn*).
- Binance exige un mínimo de unos **5–10 USDT** por orden.
- **Empieza con poco** (por ejemplo, 50–100 USDT) durante las primeras semanas.

### 11.4 Arrancar

```
python bot.py
```

Debe decir `modo live` (sin "testnet"). A partir de aquí opera con dinero real. 💰

### 🔒 Reglas de seguridad

- **Nunca compartas el archivo `.env`** ni hagas capturas de pantalla donde se vean tus claves.
- El archivo `.env` **no se sube a GitHub** (está excluido a propósito). No lo cambies.
- Si crees que alguien ha visto tus claves: entra en Binance → Gestión de API → **bórralas** y crea unas nuevas.

---

## 12. Cambiar la configuración

Todos los ajustes de la estrategia están en el archivo **`config.py`**.

1. Para el bot si está en marcha (`Ctrl + C`).
2. Abre `config.py`:
   - 🪟 Windows: `notepad config.py`
   - 🍎 Mac: `open -e config.py`
3. Cambia **solo el número** que hay después del `=`. Por ejemplo, para activar el filtro de tendencia:

   Antes:
   ```python
   trend_filter: int = 0        # solo compra si el precio...
   ```
   Después:
   ```python
   trend_filter: int = 200      # solo compra si el precio...
   ```

4. Guarda y vuelve a arrancar el bot.

⚠️ **Cuidado al editar:**
- No borres los espacios del principio de la línea.
- No borres los dos puntos `:` ni el `=`.
- Los decimales van con **punto**, no con coma: `0.05`, **no** `0,05`.
- Los textos van entre comillas: `ma_type: str = "ema"`.
- `0.03` significa **3 %**; `0.05` significa **5 %**.

### Ajustes más útiles

| Ajuste | Qué hace | Ejemplo |
|---|---|---|
| `symbol` | Moneda que opera | `"BTC/USDT"`, `"ETH/USDT"` |
| `timeframe` | Tamaño de las velas | `"1h"`, `"4h"`, `"1d"` |
| `fast` / `slow` | Medias móviles | `20` / `50` |
| `ma_type` | Tipo de media | `"sma"` o `"ema"` |
| `trend_filter` | Filtro de tendencia (0 = no) | `200` |
| `adx_min` | Filtro de mercado lateral (0 = no) | `20` |
| `position_pct` | % del saldo por operación | `0.95` (95 %) |
| `stop_loss` | Venta si cae este % | `0.03` (3 %) |
| `trailing_stop` | Venta si cae este % desde el máximo (0 = no) | `0.05` (5 %) |
| `take_profit` | Venta si sube este % (0 = no) | `0.08` (8 %) |
| `max_drawdown` | Se detiene si pierdes este % en total | `0.20` (20 %) |
| `paper_balance` | Saldo ficticio del modo simulado | `1000.0` |

> 💡 Antes de cambiar algo, pruébalo con el backtest (Parte 6) para ver si mejora.

---

## 13. Dejarlo funcionando 24 horas (servidor)

Si no quieres tener tu ordenador encendido siempre, puedes alquilar un **servidor en la nube (VPS)** por unos 4–6 € al mes (por ejemplo Hetzner, Contabo, DigitalOcean u OVH). Esta parte es algo más técnica; hazla solo cuando el bot ya te funcione en tu ordenador.

1. Contrata un VPS con **Ubuntu 24.04** (el plan más barato sobra).
   ⚠️ Elige un servidor en **Europa**: Binance bloquea las conexiones desde algunos países (por ejemplo, Estados Unidos).
2. El proveedor te dará una **IP** (por ejemplo `95.216.12.34`) y una contraseña de `root`.
3. Conéctate desde tu terminal (funciona igual en Windows y Mac):
   ```
   ssh root@95.216.12.34
   ```
   Escribe `yes` si pregunta y luego la contraseña (no se ve mientras la escribes; es normal).
4. Ya dentro del servidor, copia estos comandos uno a uno:
   ```
   apt update && apt install -y python3-venv git
   adduser bot
   su - bot
   git clone https://github.com/solertesting-prog/BINANCE-BOT.git trading-bot
   cd trading-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env
   ```
   - `adduser bot` te pedirá una contraseña para el usuario nuevo; el resto de preguntas puedes dejarlas vacías pulsando Enter.
   - Si el repositorio es **privado**, `git clone` te pedirá usuario y contraseña de GitHub. Como contraseña necesitas un *token*: en GitHub → *Settings → Developer settings → Personal access tokens → Generate new token*.
   - `nano .env` abre el editor: rellena tus datos, guarda con `Ctrl + O`, Enter, y sal con `Ctrl + X`.
5. Vuelve al usuario administrador e instala el servicio:
   ```
   exit
   sed 's/usuario/bot/g' /home/bot/trading-bot/deploy/trading-bot.service > /etc/systemd/system/trading-bot.service
   systemctl daemon-reload
   systemctl enable --now trading-bot
   ```
6. Comprueba que funciona:
   ```
   systemctl status trading-bot
   ```
   Debe poner **`active (running)`** en verde. ✅ Pulsa `q` para salir.

Ya puedes cerrar la terminal: el bot sigue funcionando en el servidor, se reinicia solo si falla y arranca solo si el servidor se reinicia.

**Comandos útiles en el servidor:**

| Para... | Comando |
|---|---|
| Ver el log en directo | `journalctl -u trading-bot -f` (salir: `Ctrl + C`) |
| Ver el estado del bot | `cd /home/bot/trading-bot && sudo -u bot venv/bin/python bot.py --status` |
| Reiniciar tras cambiar la configuración | `systemctl restart trading-bot` |
| Pararlo | `systemctl stop trading-bot` |

> ⚠️ No tengas el bot funcionando a la vez en tu ordenador y en el servidor con la misma cuenta de Binance: se pisarían las órdenes.

---

## 14. Problemas frecuentes y soluciones

### "python" no se reconoce como un comando (Windows)
No marcaste **"Add python.exe to PATH"** al instalar. Mira la solución al final de la [Parte 2](#2-instalar-python). Cierra y vuelve a abrir la terminal después.

### `command not found: python` (Mac)
Usa `python3` en lugar de `python`. Con el entorno activado `(venv)`, `python` ya funciona.

### `No module named 'ccxt'` (o `pandas`, `dotenv`...)
El entorno no está activado. Comprueba que ves `(venv)` al principio de la línea. Si no, actívalo (Paso 5.2). Si sigue fallando, repite `pip install -r requirements.txt`.

### `No such file or directory: 'requirements.txt'` o `can't open file 'bot.py'`
No estás dentro de la carpeta del bot. Repite la [Parte 4](#4-abrir-la-terminal-dentro-de-la-carpeta-del-bot).

### `venv\Scripts\activate` no funciona / "la ejecución de scripts está deshabilitada"
Estás en **PowerShell** en lugar de **cmd**. Cierra la ventana y ábrela con el método de la Parte 4 (escribiendo `cmd` en la barra de dirección).

### `Faltan BINANCE_API_KEY / BINANCE_API_SECRET en el archivo .env`
Tienes `MODE=live` pero no has puesto las claves, o el archivo `.env` no existe o no se llama exactamente `.env`.
- En Windows, a veces el Bloc de notas lo guarda como `.env.txt`. Escribe `dir` en la terminal y comprueba el nombre. Si es `.env.txt`, renómbralo con: `ren .env.txt .env`

### Error `451` o `Service unavailable from a restricted location`
Binance bloquea tu ubicación o la de tu servidor (por ejemplo, servidores en EE. UU.). Usa un servidor en Europa.

### `Invalid API-key, IP, or permissions for action`
- Revisa que copiaste bien las claves (sin espacios al principio o al final).
- Revisa que tienes activado **"Spot & Margin Trading"** en Binance.
- Si pusiste restricción de IP, comprueba que la IP es la correcta.
- Si usas claves de la **testnet**, `TESTNET` debe estar en `true`. Con claves reales, en `false`.

### `Timestamp for this request is outside of the recvWindow`
El reloj de tu ordenador no está en hora. El bot intenta corregirlo solo, pero si persiste:
- 🪟 Windows: *Configuración → Hora e idioma → Fecha y hora* → pulsa **"Sincronizar ahora"**.
- 🍎 Mac: *Ajustes del Sistema → General → Fecha y hora* → activa "Ajustar automáticamente".

### `Saldo insuficiente para comprar`
No tienes USDT suficiente en la cuenta **Spot** (mínimo unos 10 USDT). Pasa USDT a Spot desde la app de Binance.

### `El bot está detenido por el interruptor de drawdown`
El bot perdió más del límite de seguridad (20 % por defecto), vendió y se paró para protegerte. **Antes de reactivarlo, piensa qué ha pasado.** Si quieres continuar, borra el archivo `state.json` y arráncalo.

### El bot lleva días sin hacer nada
Es normal. Con velas de 1 hora, la estrategia puede pasar días sin señal, sobre todo con los filtros activados. Comprueba con `python bot.py --status` que sigue vivo y mira `bot.log`.

### El backtest falla con un error de conexión o SSL (Mac)
No ejecutaste "Install Certificates.command". Ve a *Aplicaciones → Python 3.x* y haz doble clic en él.

### Otro error que no sale aquí
Copia el mensaje de error completo (las últimas 10–15 líneas) y pregúntale a Claude o búscalo en Google.

---

## 15. Chuleta de comandos

**Cada vez que abras una terminal nueva:**

| | 🪟 Windows | 🍎 Mac |
|---|---|---|
| 1. Ir a la carpeta | Barra de dirección → `cmd` | `cd ` + arrastrar carpeta + Enter |
| 2. Activar entorno | `venv\Scripts\activate` | `source venv/bin/activate` |

**Después (igual en los dos sistemas):**

| Para... | Comando |
|---|---|
| Hacer un backtest con informe | `python backtest.py --html informe.html` |
| Abrir el informe | `start informe.html` (Win) / `open informe.html` (Mac) |
| Buscar la mejor configuración | `python optimize.py` |
| Arrancar el bot | `python bot.py` |
| Ver cómo va el bot | `python bot.py --status` |
| Parar el bot | `Ctrl + C` |
| Comprobar que todo funciona | `python -m pytest tests -q` |
| Editar la configuración privada | `notepad .env` (Win) / `open -e .env` (Mac) |
| Editar la estrategia | `notepad config.py` (Win) / `open -e config.py` (Mac) |

### Actualizar el bot a una versión nueva

1. Para el bot (`Ctrl + C`).
2. Descarga el ZIP nuevo de GitHub (Parte 3) y descomprímelo.
3. Copia **desde la carpeta vieja a la nueva** estos archivos, para no perder tus datos: `.env`, `state.json`, `trades_log.csv` y, si lo modificaste, `config.py`.
4. En la carpeta nueva, repite los pasos 5.1, 5.2 y 5.3.

---

> ⚠️ **Aviso final:** este bot es una herramienta, no una recomendación de inversión. Los resultados pasados no garantizan los futuros. Las criptomonedas son muy volátiles. Usa solo dinero que puedas permitirte perder.
