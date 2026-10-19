"""Configuración del bot.

Lo más cómodo es configurarlo desde el panel (botón ⚙ Configuración): exchange, modo, claves
y monedas se guardan solos. Aquí puedes ajustar a mano el resto de la estrategia.

De dónde sale cada valor (de más a menos prioridad):
  1. .env           -> modo (MODE, TESTNET) y claves de API. Privado, nunca se sube a GitHub.
  2. settings.json  -> lo elegido en el asistente del panel (exchange, monedas, velas, riesgo).
  3. Los valores por defecto de esta clase.
Cualquier valor a 0 desactiva esa opción.
"""
import json
import os
from dataclasses import dataclass, fields
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
SETTINGS_FILE = ROOT / "settings.json"

# Campos que el asistente del panel puede guardar en settings.json
SETUP_FIELDS = ("exchange", "symbols", "timeframe", "risk_per_trade", "max_open_positions",
                "position_pct", "fee", "paper_balance")
# Credenciales: nombre en ccxt -> campo de Config
CRED_FIELDS = {"apiKey": "api_key", "secret": "api_secret", "password": "api_password", "uid": "api_uid"}


@dataclass(frozen=True)
class Config:
    # --- Mercado ---
    exchange: str = "binance"        # id del exchange en ccxt: binance, kraken, coinbase, okx, bybit...
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
    exchange_stops: bool = True      # [real] deja el stop loss puesto en el exchange (protege aunque el PC se apague)
    stop_limit_gap: float = 0.005    # [real] margen del precio límite de la orden stop (0,5 %)

    # --- Costes ---
    fee: float = 0.001               # comisión por operación (el asistente pone la del exchange)

    # --- Ejecución (se rellenan desde .env) ---
    mode: str = "paper"              # "paper" (simulado) o "live" (real)
    testnet: bool = False            # usar el entorno de pruebas del exchange
    paper_balance: float = 1000.0    # saldo inicial simulado
    poll_seconds: int = 60           # cada cuánto revisa precios y stops
    panel_port: int = 8765

    # --- Claves (desde .env; nunca escribirlas aquí) ---
    api_key: str = ""
    api_secret: str = ""
    api_password: str = ""           # "passphrase" (OKX, KuCoin, Bitget, Coinbase Exchange...)
    api_uid: str = ""
    telegram_token: str = ""
    telegram_chat_id: str = ""

    @property
    def quote(self) -> str:
        return self.symbols[0].split("/")[1]


def env_name(exchange: str, field: str, testnet: bool = False) -> str:
    """Nombre de la variable de .env para una clave: BINANCE_API_KEY, KRAKEN_API_SECRET,
    OKX_TESTNET_API_PASSWORD... (cada exchange y modo guarda sus propias claves)."""
    prefix = exchange.upper().replace("-", "_") + ("_TESTNET" if testnet else "")
    return f"{prefix}_{field.upper()}"


def read_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def load_config(**overrides) -> Config:
    """Construye la configuración actual leyendo settings.json y .env (siempre de nuevo)."""
    load_dotenv(ENV_FILE, override=True)
    names = {f.name for f in fields(Config)}
    kw = {k: v for k, v in read_settings().items() if k in SETUP_FIELDS}
    if "symbols" in kw:
        kw["symbols"] = tuple(kw["symbols"])
    kw["mode"] = os.getenv("MODE", "paper").strip().lower()
    kw["testnet"] = os.getenv("TESTNET", "false").strip().lower() == "true"
    kw["panel_port"] = int(os.getenv("PANEL_PORT", "8765"))
    ex = kw.get("exchange", Config.exchange)
    for field in CRED_FIELDS.values():
        value = os.getenv(env_name(ex, field, kw["testnet"]), "")
        if not value and kw["testnet"]:          # compatibilidad: claves de testnet sin prefijo
            value = os.getenv(env_name(ex, field), "")
        kw[field] = value.strip()
    kw["telegram_token"] = os.getenv("TELEGRAM_TOKEN", "").strip()
    kw["telegram_chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    kw.update({k: v for k, v in overrides.items() if k in names})
    return Config(**kw)


CONFIG = load_config()
