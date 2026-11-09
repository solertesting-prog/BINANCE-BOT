# Valorize Bot

Valorize Bot es un bot de trading automático para el mercado spot (solo compras en largo, sin apalancamiento) de **Binance, Kraken, Coinbase, OKX, Bybit, KuCoin, Bitget, Bitvavo, Bitfinex, Gate.io y muchos más** (vía [ccxt](https://github.com/ccxt/ccxt)). Incluye **panel de control en el navegador** con asistente de configuración, gestión del riesgo profesional y protección con stops puestos en el propio exchange.

> 📘 **¿Primera vez?** Sigue el [**Manual paso a paso**](MANUAL_INSTALACION.md). En Windows se instala con un doble clic y se usa desde un icono en el escritorio.

## Características

**Estrategia**
- Cruce de medias móviles (EMA 20/50) con filtro de tendencia (EMA 200) y filtro de fuerza (ADX ≥ 20) para evitar mercados laterales.
- **Filtro de mercado** opcional: no comprar otras monedas mientras BTC esté bajo su media de 200 velas (desactivado por defecto: en el backtest de 3 años no mejoró el resultado total).
- **Stops según la volatilidad (ATR):** stop inicial a 2,5 × ATR y trailing a 3 × ATR, que sube con el precio.
- **Tamaño según el riesgo:** cada operación arriesga como máximo un 1 % del capital.
- **Varias monedas** a la vez (botón ⭐ Recomendadas con 6 de las más líquidas), con límite de posiciones abiertas.
- Interruptor de seguridad: vende todo y se detiene si el capital cae un 20 %.

**Laboratorio, explicaciones y página pública**
- **🧪 Laboratorio en la sombra:** variantes de tu estrategia (más riesgo, medias 10/30, sin filtro de fuerza, filtro de BTC, adaptativa) compiten en paralelo con dinero ficticio y los mismos precios en vivo. El panel muestra la clasificación y un botón para pasar a usar la que elijas.
- **💬 Qué está pensando el bot:** para cada moneda, el tipo de mercado (alcista, lateral, bajista) y una frase en lenguaje llano: por qué no compra, qué espera o cuándo vendería. También con `/porque` en Telegram.
- **Estrategia adaptativa** (opcional, `strategy_mode = "adaptive"`): sigue tendencias cuando las hay, compra caídas exageradas en mercado lateral (RSI + banda de Bollinger) y se queda fuera en mercado bajista. Pruébala primero en el laboratorio o con `python backtest.py --mode adaptive`.
- **🔗 Página pública de resultados:** enlace de solo lectura, opcional, con la evolución en porcentaje, las operaciones y la comparación con comprar y mantener BTC. Nunca muestra importes e indica si los resultados son simulados o reales.

**Multi-exchange y asistente de configuración**
- Asistente en el panel: exchange → modo (simulado / testnet / real) → claves con **prueba de conexión** → monedas, velas y riesgo.
- Detecta lo que permite cada exchange (testnet, stops en el exchange, tipo de claves) y marca los no compatibles con el motivo (p. ej. bitFlyer no ofrece velas).
- Claves por exchange y modo, guardadas solo en `.env`; el panel nunca las devuelve completas.

**Ejecución robusta**
- En modo real deja el **stop loss puesto en el exchange** (STOP_LOSS_LIMIT en Binance; orden stop estándar de ccxt en los demás), así protege aunque el PC se apague, y lo sube con el trailing. El bot vigila además el precio por su cuenta.
- **Reconciliación** al arrancar: detecta stops ejecutados o ventas manuales hechas mientras estaba apagado.
- Reintenta las consultas si falla la red; las órdenes nunca se repiten a ciegas.
- Estado persistente y atómico: continúa donde estaba tras un reinicio.

**Licencias (preparadas para vender el bot)**
- 🆓 **Ahora mismo es gratuito:** `REQUIRE_LICENSE = False` en `licensing.py`. Para empezar a cobrar, ponlo a `True` (ver [VENTA_LICENCIAS.md](VENTA_LICENCIAS.md)).
- Activación online con **Lemon Squeezy**: suscripciones, límite de PCs por licencia, revalidación cada 6 h y 72 h de gracia sin internet.
- Licencia atada al PC, caché firmada (no se puede copiar ni editar) y modo simulado gratis como prueba (configurable).
- `compilar.bat` genera un `.exe` compilado (Nuitka) para entregar a los clientes sin el código fuente.
- Guía del vendedor en [VENTA_LICENCIAS.md](VENTA_LICENCIAS.md) y manual del cliente en [MANUAL_CLIENTE.md](MANUAL_CLIENTE.md).

**Servidor 24/7 con acceso web** ([SERVIDOR.md](SERVIDOR.md))
- `preparar-servidor.bat` genera un texto *cloud-init*: al crear un servidor (AWS gratis 6 meses, Hetzner ~6 €/mes...) se instala solo.
- Memoria de intercambio automática en servidores de 1 GB y dirección que se actualiza sola si cambia la IP pública.
- HTTPS automático con Caddy (dominio gratuito `<ip>.sslip.io` o uno propio), servicio que se reinicia solo, cortafuegos y parches automáticos.
- Login con contraseña (hash scrypt), cookie segura, bloqueo tras 5 intentos fallidos y lista de dominios permitidos. La sesión dura 7 días y sobrevive a reinicios y actualizaciones.
- **Verificación en dos pasos** (TOTP: Google Authenticator, Authy...) opcional.
- **Botón ⬆ Actualizar** en el panel: instala la última versión de GitHub y se reinicia solo.
- **Aviso de caída** con healthchecks.io (latido cada 5 minutos) y **copia de seguridad diaria** (14 días).

**Plataforma multiusuario (beta privada)** ([PLATAFORMA.md](PLATAFORMA.md))
- En `https://app.<tu-dirección>`: registro solo por invitación, cada usuario con su panel y su propio bot **simulado**.
- Panel de administración: invitar, desactivar usuarios y enlaces para restablecer la contraseña.
- Verificación en dos pasos y avisos por Telegram por usuario; datos de mercado compartidos con caché.

**Panel de control** (`http://127.0.0.1:8765`)
- Gráfico de velas con las medias, las compras y ventas del bot y las líneas de entrada y stop.
- Capital, resultado, posiciones con su P&L y su stop, curva de capital, historial y registro en vivo.
- Botones para arrancar, parar y cerrar posiciones.
- **🔔 Avisos por Telegram** configurables desde el panel: pegas el token de tu bot, detecta tu chat solo y envía un mensaje de prueba.
- **Comandos por Telegram:** `/estado`, `/posiciones`, `/parar`, `/arrancar` (solo desde tu chat).
- **⬇ Excel:** descarga el historial de operaciones listo para Excel.
- Solo accesible desde tu ordenador y protegido contra peticiones de otras webs.

**Herramientas**
- Backtest con informe HTML, que comparte la lógica exacta con el bot (comprobado por los tests).
- Optimizador walk-forward que valida los parámetros en datos no vistos.
- Avisos por Telegram, modo simulado, testnet y real.
- Instalador para Windows con icono en el escritorio y arranque automático.

## Uso rápido

| Windows (doble clic) | Equivalente en consola |
|---|---|
| `instalar.bat` | `python -m venv venv` + `pip install -r requirements.txt` |
| Icono **Valorize Bot** / `abrir-panel.bat` | `python panel.py` |
| `backtest.bat` | `python backtest.py --html informe.html` |
| | `python optimize.py --days 1095` |
| `arrancar-bot.bat` | `python bot.py` (sin panel) |
| `estado-bot.bat` | `python bot.py --status` |

Exchange, modo, claves y monedas se configuran desde el panel (**⚙ Configuración**): se guardan en `.env` (modo y claves, privado) y `settings.json`. Los ajustes avanzados de la estrategia están en `config.py`.

## Estructura

| Archivo | Contenido |
|---|---|
| `config.py` | Parámetros de la estrategia, del riesgo y de la ejecución |
| `strategy.py` | Indicadores, señales, stops y tamaño de posición (compartido por backtest y bot) |
| `bot.py` | Motor: brokers simulado y real, stops en el exchange, reconciliación y estado |
| `panel.py` + `web/panel.html` | Servidor local y la interfaz del panel |
| `setup_api.py` | Asistente: catálogo de exchanges, mercados, prueba de conexión y guardado |
| `telegram_setup.py`, `telegram_bot.py` | Conexión de los avisos por Telegram desde el panel y comandos del chat |
| `plataforma.py`, `plataforma_db.py`, `web/plataforma_*.html` | Plataforma multiusuario: cuentas, invitaciones, un bot por usuario y administración |
| `lab.py` | Laboratorio en la sombra: variantes en paralelo con dinero ficticio |
| `public_page.py`, `web/publico.html` | Página pública de resultados (solo lectura) |
| `maintenance.py` | Copias de seguridad diarias y latido (aviso de caída) |
| `updater.py` | Actualización desde el panel en el servidor |
| `licensing.py` | Licencias con Lemon Squeezy (datos de tu tienda al principio del archivo) |
| `compilar.bat`, `cliente/` | Compilación a `.exe` e instalador para clientes |
| `backtest.py`, `report.py`, `optimize.py` | Backtest, informe HTML y optimización walk-forward |
| `exchange.py` | Conexión con el exchange (ccxt), capacidades de cada uno y descarga de velas |
| `tests/` | 52 tests sin conexión: estrategia, backtest, motor, asistente, licencias y acceso con contraseña (con exchanges y servidor de licencias simulados) y panel |
| `auth.py`, `web/login.html` | Acceso con contraseña al panel (para usarlo por internet) |
| `deploy/instalar-servidor.sh`, `deploy/generar_cloud_init.py`, `preparar-servidor.bat` | Instalación automática en un servidor (ver SERVIDOR.md) |
| `deploy/valorize-bot.service` | Servicio systemd básico (alternativa manual) |

## Aviso

Esto es una herramienta, no una recomendación de inversión. Los resultados pasados no garantizan los futuros. Usa solo dinero que puedas permitirte perder.
