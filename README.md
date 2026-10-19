# Bot de trading: cruce de medias en Binance

> 📘 **¿Primera vez?** Sigue el [**Manual de instalación paso a paso**](MANUAL_INSTALACION.md): explica todo desde cero, para Windows y Mac, sin necesidad de saber programar.

Bot en Python para Binance spot (solo compras y ventas, sin apalancamiento).
Compra cuando la media móvil rápida cruza por encima de la lenta y vende cuando cruza por debajo. Opcionalmente filtra las entradas para evitar mercados laterales, y protege cada operación con stop loss, trailing stop, take profit y un interruptor general de seguridad.

## Flujo de trabajo recomendado

1. **Backtest** con la configuración por defecto → `python backtest.py --html informe.html`
2. **Optimiza con walk-forward** → `python optimize.py`
3. Si el resultado **fuera de muestra** convence, ajusta `config.py`.
4. **Modo simulado** durante semanas → `python bot.py`
5. **Testnet** de Binance (órdenes reales con dinero ficticio).
6. **Dinero real**, empezando con poco.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `config.py` | Todos los parámetros: par, velas, medias, filtros, riesgo, comisiones |
| `strategy.py` | Indicadores, señales y niveles de salida (lo comparten backtest y bot) |
| `backtest.py` | Prueba la estrategia con datos históricos |
| `optimize.py` | Busca parámetros y los valida en datos no vistos (walk-forward) |
| `report.py` | Genera el informe HTML del backtest |
| `bot.py` | El bot en sí (modo simulado o real) |
| `exchange.py` | Conexión con Binance y descarga de velas |
| `deploy/trading-bot.service` | Servicio para tenerlo funcionando 24/7 en Linux |
| `tests/` | Tests automáticos (no necesitan internet) |

## 1. Instalación

Necesitas Python 3.10 o superior.

```bash
cd trading-bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
python -m pytest tests -q       # opcional: comprueba que todo funciona
```

## 2. La estrategia y sus opciones (`config.py`)

| Parámetro | Qué hace | Por defecto |
|---|---|---|
| `fast` / `slow` | Velas de la media rápida y la lenta | 20 / 50 |
| `ma_type` | `"sma"` (simple) o `"ema"` (exponencial, reacciona antes) | sma |
| `trend_filter` | Solo compra si el precio está sobre esta media larga (p. ej. 200). Evita comprar en mercados bajistas | 0 (no) |
| `adx_min` | Solo compra si el ADX ≥ este valor (p. ej. 20). El ADX mide la fuerza de la tendencia: evita los mercados laterales, donde el cruce de medias pierde dinero | 0 (no) |
| `stop_loss` | Vende si cae este % desde la entrada | 3 % |
| `trailing_stop` | Vende si cae este % desde el **máximo** alcanzado. Deja correr las ganancias y las protege | 0 (no) |
| `take_profit` | Vende si sube este % desde la entrada | 8 % |
| `max_drawdown` | Interruptor: si el capital cae este % desde el inicio, vende todo y se detiene | 20 % |

Cualquier valor a 0 desactiva esa opción.

## 3. Backtest

```bash
python backtest.py                                   # último año, parámetros de config.py
python backtest.py --days 730 --timeframe 4h         # 2 años en velas de 4 h
python backtest.py --ma ema --trend 200 --adx 20 --trailing 0.05 --tp 0
python backtest.py --html informe.html               # informe visual
python backtest.py --export operaciones.csv          # operaciones a CSV
```

El **informe HTML** muestra los indicadores clave, la curva de capital frente a comprar y mantener, el drawdown y la lista de operaciones. Ábrelo con doble clic; funciona sin internet.

Los datos descargados se guardan en `data/` y se reutilizan durante el día.

Fíjate sobre todo en:
- **Rentabilidad vs. comprar y mantener**: si el bot no supera simplemente comprar y esperar, plantéate si merece la pena (aunque un drawdown mucho menor también tiene valor).
- **Máx. drawdown**: la peor caída que habrías sufrido. ¿La aguantarías con dinero real?
- **Profit factor**: por encima de 1,3–1,5 empieza a ser interesante.
- **Operaciones**: con menos de 20–30, el resultado puede ser pura suerte.

## 4. Optimización walk-forward

```bash
python optimize.py                       # último año, 3 tramos de prueba
python optimize.py --days 730 --folds 4
python optimize.py --quick               # rejilla pequeña, para probar rápido
```

Optimizar es peligroso: si pruebas cientos de combinaciones, alguna saldrá espectacular en el pasado por pura casualidad. El optimizador lo detecta imitando la realidad: busca los mejores parámetros con una parte del histórico y los prueba **sin tocarlos** en el tramo siguiente, que no ha visto. Repite avanzando en el tiempo.

Lo que cuenta es la línea **"Resultado fuera de muestra"**. Si en entrenamiento sale +100 % y en prueba −5 %, esos parámetros no sirven. También avisa si los parámetros elegidos cambian mucho de un tramo a otro, otra señal de sobreajuste.

La rejilla de combinaciones está al principio de `optimize.py` (`GRID`); puedes ampliarla, pero cuantas más combinaciones, más riesgo de sobreajuste.

## 5. Modo simulado (paper)

En `.env` deja `MODE=paper` y ejecuta:

```bash
python bot.py            # arranca
python bot.py --status   # en otra terminal: posición, stop actual y resultados
```

Usa precios reales de Binance con 1000 USDT ficticios y no necesita claves. Déjalo correr varias semanas. Cada operación cerrada se apunta en `trades_log.csv`; el detalle, en `bot.log`. Para empezar de cero, borra `state.json` y `trades_log.csv`.

## 6. Testnet de Binance

1. Crea claves en https://testnet.binance.vision (inicias sesión con GitHub).
2. En `.env`: `MODE=live`, `TESTNET=true` y pon esas claves.
3. `python bot.py`: envía órdenes reales a la testnet, con dinero ficticio.

## 7. Dinero real

Solo cuando el backtest, la optimización y semanas de modo simulado te convenzan:

1. En Binance: Perfil → Gestión de API → Crear API.
2. Permisos: activa **solo** "Enable Spot & Margin Trading". **Nunca actives retiros.** Restringe a la IP de tu servidor si puedes.
3. En `.env`: `MODE=live`, `TESTNET=false` y tus claves.
4. Empieza con una cantidad pequeña que puedas permitirte perder. El bot usa el 95 % del USDT libre de la cuenta (`position_pct`). Al vender, solo vende la cantidad que compró él, no el resto de tu BTC.

## 8. Funcionamiento 24/7

Tu ordenador no sirve si se apaga o se suspende. Opciones: un VPS barato (unos 5 €/mes) o una Raspberry Pi.

En Linux, el archivo `deploy/trading-bot.service` lo convierte en un servicio que arranca solo y se reinicia si falla. Las instrucciones están dentro del archivo.

## Avisos por Telegram (opcional)

1. Habla con @BotFather en Telegram, crea un bot y copia el token.
2. Escribe a tu bot y abre `https://api.telegram.org/bot<TOKEN>/getUpdates` para ver tu `chat_id`.
3. Rellena `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`.

Recibirás cada compra y venta, el aviso si salta el interruptor de seguridad y un resumen diario del capital.

## Seguridad incluida

- Stop loss, trailing stop y take profit por operación, revisados cada minuto (no solo al cierre de vela).
- Interruptor de drawdown: vende y se detiene; para reactivarlo hay que borrar `state.json` a mano.
- Señales solo con velas **cerradas** y una vez por vela.
- El bot y el backtest usan exactamente la misma lógica (comprobado por los tests).
- Comprueba el mínimo de orden de Binance antes de comprar.
- Estado guardado de forma atómica: un corte de luz no lo corrompe.
- Si hay un error de red, lo registra y reintenta en el siguiente ciclo.
- `.gitignore` evita subir por error tus claves (`.env`) a GitHub.

## Limitaciones conocidas

- El backtest incluye comisiones pero no deslizamiento (la diferencia entre el precio esperado y el real en órdenes de mercado). En BTC/USDT es pequeño, en pares poco líquidos no.
- Solo opera un par a la vez. Para varios pares, lanza varias copias en carpetas distintas con su propio `config.py`.

## Aviso

Esto es una herramienta, no una recomendación de inversión. Los resultados pasados no garantizan los futuros. Usa solo dinero que puedas permitirte perder.
