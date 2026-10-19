"""Configuración del bot. Edita estos valores a tu gusto.

Las claves de la API NUNCA van aquí: ponlas en el archivo .env (ver .env.example).
Cualquier valor a 0 desactiva esa opción.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # --- Mercado ---
    symbols: tuple = ("BTC/USDT",)   # monedas a operar, p. ej. ("BTC/USDT", "ETH/USDT")
    timeframe: str = "4h"            # velas: 15m, 1h, 4h, 1d...

    # --- Estrategia: cruce de medias móviles ---
    fast: int = 20                   # media rápida (nº de velas)
    slow: int = 50                   # media lenta (nº de velas)
    ma_type: str = "ema"             # "sma" (simple) o "ema" (exponencial, reacciona antes)

    # --- Filtros de entrada ---
    trend_filter: int = 200          # solo compra si el precio está sobre esta media larga
    adx_min: float = 20              # solo compra si ADX >= este valor (evita mercados laterales)

    # --- Stops ---
    stop_mode: str = "atr"           # "atr" (se adapta a la volatilidad) o "pct" (porcentaje fijo)
    atr_period: int = 14             # velas para medir la volatilidad (ATR)
    atr_stop_mult: float = 2.5       # [atr] stop inicial = entrada - 2,5 × ATR
    atr_trail_mult: float = 3.0      # [atr] stop dinámico = máximo - 3 × ATR (sube con el precio)
    stop_loss: float = 0.03          # [pct] stop inicial = entrada - 3 %
    trailing_stop: float = 0         # [pct] stop dinámico = máximo - este %
    take_profit: float = 0           # vende al subir este % desde la entrada (0 = dejar correr)

    # --- Tamaño de las operaciones ---
    risk_per_trade: float = 0.01     # arriesga como máximo un 1 % del capital por operación
    position_pct: float = 0.95       # tope: % del capital en una sola operación
    max_open_positions: int = 3      # máximo de monedas con compra abierta a la vez

    # --- Seguridad ---
    max_drawdown: float = 0.20       # si el capital cae un 20 % desde el inicio: vende todo y se detiene
    exchange_stops: bool = True      # [real] deja el stop loss puesto en Binance (protege aunque el PC se apague)
    stop_limit_gap: float = 0.005    # [real] margen del precio límite de la orden stop (0,5 %)

    # --- Costes ---
    fee: float = 0.001               # comisión por operación (Binance spot: 0,1 %)

    # --- Ejecución ---
    mode: str = os.getenv("MODE", "paper")              # "paper" (simulado) o "live" (real)
    testnet: bool = os.getenv("TESTNET", "false").lower() == "true"
    paper_balance: float = 1000.0                       # saldo inicial simulado en USDT
    poll_seconds: int = 60                              # cada cuánto revisa precios y stops
    panel_port: int = int(os.getenv("PANEL_PORT", "8765"))

    # --- Claves (desde .env) ---
    api_key: str = os.getenv("BINANCE_API_KEY", "")
    api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")


CONFIG = Config()
