"""Conexión con Binance mediante ccxt y descarga de velas."""
import time

import ccxt
import pandas as pd

from config import Config


def make_exchange(cfg: Config, private: bool = False) -> ccxt.binance:
    # adjustForTimeDifference: corrige solo si el reloj del ordenador va adelantado o atrasado
    params = {"enableRateLimit": True,
              "options": {"defaultType": "spot", "adjustForTimeDifference": True}}
    if private:
        if not cfg.api_key or not cfg.api_secret:
            raise SystemExit("Faltan BINANCE_API_KEY / BINANCE_API_SECRET en el archivo .env")
        params["apiKey"] = cfg.api_key
        params["secret"] = cfg.api_secret
    ex = ccxt.binance(params)
    if cfg.testnet:
        ex.set_sandbox_mode(True)
    return ex


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
