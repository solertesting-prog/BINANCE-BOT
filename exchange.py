"""Conexión con los exchanges (vía ccxt), catálogo de exchanges y descarga de velas."""
import time

import ccxt
import pandas as pd

from config import Config

# Exchanges que se muestran destacados en el asistente (id de ccxt, nombre)
FEATURED = [("binance", "Binance"), ("kraken", "Kraken"), ("coinbase", "Coinbase"), ("bitflyer", "bitFlyer"),
            ("okx", "OKX"), ("bybit", "Bybit"), ("kucoin", "KuCoin"), ("bitget", "Bitget"),
            ("bitvavo", "Bitvavo"), ("bitfinex", "Bitfinex"), ("gate", "Gate.io"), ("cryptocom", "Crypto.com"),
            ("mexc", "MEXC"), ("htx", "HTX"), ("bitstamp", "Bitstamp")]
CRED_LABELS = {"apiKey": "API Key", "secret": "Secret Key", "password": "Passphrase (contraseña de la API)",
               "uid": "UID / ID de usuario"}
STOP_METHODS = ("createStopLossOrder", "createTriggerOrder", "createStopOrder")


def exchange_class(exchange_id: str):
    cls = getattr(ccxt, exchange_id, None)
    if not isinstance(cls, type):
        raise SystemExit(f"Exchange desconocido: {exchange_id}")
    return cls


def make_exchange(cfg: Config, private: bool = False, credentials: dict = None):
    """Crea la conexión con el exchange de la configuración.

    private=True usa las claves (de cfg o de `credentials`, con nombres de ccxt: apiKey, secret...).
    """
    cls = exchange_class(cfg.exchange)
    # adjustForTimeDifference: corrige solo si el reloj del ordenador va adelantado o atrasado
    params = {"enableRateLimit": True,
              "options": {"defaultType": "spot", "adjustForTimeDifference": True}}
    if private:
        creds = credentials if credentials is not None else {
            "apiKey": cfg.api_key, "secret": cfg.api_secret, "password": cfg.api_password, "uid": cfg.api_uid}
        params.update({k: v for k, v in creds.items() if v})
    ex = cls(params)
    if private:
        missing = [CRED_LABELS.get(k, k) for k, needed in (ex.requiredCredentials or {}).items()
                   if needed and not params.get(k)]
        if missing:
            raise SystemExit(f"Faltan claves de {ex.name}: {', '.join(missing)}. "
                             f"Introdúcelas en el panel (⚙ Configuración).")
    if cfg.testnet:
        try:
            ex.set_sandbox_mode(True)
        except Exception:
            raise SystemExit(f"{ex.name} no tiene modo de pruebas (testnet). Usa el modo simulado.")
    return ex


def supports_exchange_stops(ex) -> bool:
    return ex.id.startswith("binance") or any(ex.has.get(m) for m in STOP_METHODS)


def exchange_info(exchange_id: str) -> dict:
    """Qué permite un exchange (sin conectarse a internet)."""
    ex = exchange_class(exchange_id)()
    required = [k for k, v in (ex.requiredCredentials or {}).items() if v]
    unsupported = [k for k in required if k not in CRED_LABELS]
    ohlcv = bool(ex.has.get("fetchOHLCV"))
    tfs = [tf for tf in ("1h", "4h", "1d") if not ex.timeframes or tf in ex.timeframes]
    reason = None
    if not ohlcv:
        reason = "No ofrece velas históricas: el bot no puede calcular la estrategia."
    elif unsupported:
        reason = f"Usa un tipo de clave no compatible ({', '.join(unsupported)})."
    elif not tfs:
        reason = "No ofrece velas de 1 h, 4 h ni 1 día."
    return {
        "id": exchange_id, "name": ex.name,
        "credentials": [{"key": k, "label": CRED_LABELS[k]} for k in required if k in CRED_LABELS],
        "testnet": bool((ex.urls or {}).get("test")),
        "exchange_stops": supports_exchange_stops(ex),
        "timeframes": tfs, "www": (ex.urls or {}).get("www"),
        "compatible": reason is None, "reason": reason,
    }


def all_exchange_ids() -> list:
    return sorted(getattr(ccxt, "exchanges", []) or [i for i, _ in FEATURED])


def to_df(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.drop_duplicates("ts").set_index("time")


def fetch_history(ex, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
    """Descarga `days` días de velas, paginando de 1000 en 1000."""
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    since = ex.milliseconds() - days * 86_400_000
    rows = []
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not batch:
            break
        rows += batch
        since = batch[-1][0] + tf_ms
        if since >= ex.milliseconds() or len(batch) < 1000:
            break
        time.sleep(ex.rateLimit / 1000)
    return to_df(rows)


def fetch_closed_candles(ex, symbol: str, timeframe: str, n: int) -> pd.DataFrame:
    """Últimas `n` velas CERRADAS (descarta la que está en curso)."""
    rows = ex.fetch_ohlcv(symbol, timeframe, limit=n + 1)
    df = to_df(rows)
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    if df["ts"].iloc[-1] + tf_ms > ex.milliseconds():
        df = df.iloc[:-1]
    return df


def timeframe_seconds(timeframe: str) -> int:
    """'15m' -> 900, '4h' -> 14400, '1d' -> 86400 (sin necesitar conexión)."""
    units = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    return int(timeframe[:-1]) * units[timeframe[-1]]
