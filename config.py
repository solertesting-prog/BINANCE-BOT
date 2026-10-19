"""Configuración del bot. Edita estos valores a tu gusto.

Las claves de la API NUNCA van aquí: ponlas en el archivo .env (ver .env.example).
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # --- Mercado ---
    symbol: str = "BTC/USDT"     # par a operar
    timeframe: str = "1h"        # velas: 15m, 1h, 4h, 1d...

    # --- Estrategia: cruce de medias móviles ---
    fast: int = 20               # media rápida (nº de velas)
    slow: int = 50               # media lenta (nº de velas)
    ma_type: str = "sma"         # "sma" (simple) o "ema" (exponencial, reacciona antes)

    # --- Filtros de entrada (0 = desactivado) ---
    trend_filter: int = 0        # solo compra si el precio está sobre esta media larga (p. ej. 200)
    adx_min: float = 0           # solo compra si ADX >= este valor (p. ej. 20); evita mercados laterales

    # --- Gestión de riesgo (0 = desactivado) ---
    position_pct: float = 0.95   # % del saldo en USDT que se usa por operación (0.95 = 95 %)
    stop_loss: float = 0.03      # cierra si el precio cae un 3 % desde la entrada
    trailing_stop: float = 0     # cierra si cae este % desde el máximo alcanzado (p. ej. 0.05)
    take_profit: float = 0.08    # cierra si sube un 8 % desde la entrada
    max_drawdown: float = 0.20   # interruptor: el bot se detiene si el capital cae un 20 % desde el inicio

    # --- Costes ---
    fee: float = 0.001           # comisión por operación (Binance spot: 0,1 %)

    # --- Modo de ejecución ---
    mode: str = os.getenv("MODE", "paper")              # "paper" (simulado) o "live" (real)
    testnet: bool = os.getenv("TESTNET", "false").lower() == "true"
    paper_balance: float = 1000.0                       # saldo inicial simulado en USDT
    poll_seconds: int = 60                              # cada cuánto revisa el precio (stop / take profit)

    # --- Claves (desde .env) ---
    api_key: str = os.getenv("BINANCE_API_KEY", "")
    api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")


CONFIG = Config()
