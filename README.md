# Trading Bot para Binance

Bot de trading automático para Binance spot (solo compras en largo, sin apalancamiento), con **panel de control en el navegador**, gestión del riesgo profesional y protección con stops puestos en el propio exchange.

> 📘 **¿Primera vez?** Sigue el [**Manual paso a paso**](MANUAL_INSTALACION.md). En Windows se instala con un doble clic y se usa desde un icono en el escritorio.

## Características

**Estrategia**
- Cruce de medias móviles (EMA 20/50) con filtro de tendencia (EMA 200) y filtro de fuerza (ADX ≥ 20) para evitar mercados laterales.
- **Stops según la volatilidad (ATR):** stop inicial a 2,5 × ATR y trailing a 3 × ATR, que sube con el precio.
- **Tamaño según el riesgo:** cada operación arriesga como máximo un 1 % del capital.
- **Varias monedas** a la vez, con límite de posiciones abiertas.
- Interruptor de seguridad: vende todo y se detiene si el capital cae un 20 %.

**Ejecución robusta**
- En modo real deja el **stop loss puesto en Binance** (STOP_LOSS_LIMIT), así protege aunque el PC se apague, y lo sube con el trailing. El bot vigila además el precio por su cuenta.
- **Reconciliación** al arrancar: detecta stops ejecutados o ventas manuales hechas mientras estaba apagado.
- Reintenta las consultas si falla la red; las órdenes nunca se repiten a ciegas.
- Estado persistente y atómico: continúa donde estaba tras un reinicio.

**Panel de control** (`http://127.0.0.1:8765`)
- Gráfico de velas con las medias, las compras y ventas del bot y las líneas de entrada y stop.
- Capital, resultado, posiciones con su P&L y su stop, curva de capital, historial y registro en vivo.
- Botones para arrancar, parar y cerrar posiciones.
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
| Icono **Trading Bot** / `abrir-panel.bat` | `python panel.py` |
| `backtest.bat` | `python backtest.py --html informe.html` |
| | `python optimize.py --days 1095` |
| `arrancar-bot.bat` | `python bot.py` (sin panel) |
| `estado-bot.bat` | `python bot.py --status` |

El modo de ejecución (simulado / testnet / real) y las claves van en `.env` (ver `.env.example`). La estrategia se configura en `config.py`.

## Estructura

| Archivo | Contenido |
|---|---|
| `config.py` | Parámetros de la estrategia, del riesgo y de la ejecución |
| `strategy.py` | Indicadores, señales, stops y tamaño de posición (compartido por backtest y bot) |
| `bot.py` | Motor: brokers simulado y real, stops en el exchange, reconciliación y estado |
| `panel.py` + `web/panel.html` | Servidor local y la interfaz del panel |
| `backtest.py`, `report.py`, `optimize.py` | Backtest, informe HTML y optimización walk-forward |
| `exchange.py` | Conexión con Binance (ccxt) y descarga de velas |
| `tests/` | 20 tests sin conexión: estrategia, backtest, motor (con un Binance simulado) y panel |
| `deploy/trading-bot.service` | Servicio systemd para un servidor Linux |

## Aviso

Esto es una herramienta, no una recomendación de inversión. Los resultados pasados no garantizan los futuros. Usa solo dinero que puedas permitirte perder.
