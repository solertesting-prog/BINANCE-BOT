"""Estrategia de cruce de medias móviles con filtros y gestión de salidas.

ENTRADA (+1): la media rápida cruza por ENCIMA de la lenta y además, si están activados:
  - filtro de tendencia: el precio está por encima de la media larga (p. ej. 200 velas)
  - filtro ADX: hay tendencia suficiente (ADX >= adx_min), para evitar mercados laterales
SALIDA (-1): la media rápida cruza por DEBAJO de la lenta.
Además, salidas por stop loss, trailing stop y take profit (ver exit_levels).

Solo opera en largo (spot, sin apalancamiento ni cortos).
Este archivo lo usan TANTO el backtest COMO el bot, así ambos se comportan igual.
"""
import numpy as np
import pandas as pd


def moving_average(s: pd.Series, n: int, kind: str = "sma") -> pd.Series:
    if kind == "ema":
        return s.ewm(span=n, adjust=False, min_periods=n).mean()
    return s.rolling(n).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average Directional Index (Wilder). >20-25 suele indicar tendencia."""
    h, l, c = df["high"], df["low"], df["close"]
    up, down = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    a = 1 / n
    atr = tr.ewm(alpha=a, adjust=False, min_periods=n).mean()
    pdi = 100 * plus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr
    mdi = 100 * minus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=a, adjust=False, min_periods=n).mean()


def warmup_candles(cfg) -> int:
    """Velas de historial necesarias para que los indicadores sean fiables."""
    need = max(cfg.slow, cfg.trend_filter or 0, 3 * 14 if cfg.adx_min else 0)
    return min(999, need * 3 if cfg.ma_type == "ema" else need + 10)


def add_signals(df: pd.DataFrame, cfg) -> pd.DataFrame:
    if cfg.fast >= cfg.slow:
        raise ValueError("La media rápida debe ser menor que la lenta")
    df = df.copy()
    df["ma_fast"] = moving_average(df["close"], cfg.fast, cfg.ma_type)
    df["ma_slow"] = moving_average(df["close"], cfg.slow, cfg.ma_type)

    above = df["ma_fast"] > df["ma_slow"]
    prev_above = above.shift(1, fill_value=False)
    valid = df["ma_slow"].notna() & df["ma_slow"].shift(1).notna()
    cross_up = valid & above & ~prev_above
    cross_down = valid & ~above & prev_above

    allow = pd.Series(True, index=df.index)
    if cfg.trend_filter:
        df["ma_trend"] = moving_average(df["close"], cfg.trend_filter, cfg.ma_type)
        allow &= df["close"] > df["ma_trend"]          # NaN -> False: sin datos, no entra
    if cfg.adx_min:
        df["adx"] = adx(df)
        allow &= df["adx"] >= cfg.adx_min

    df["signal"] = 0
    df.loc[cross_up & allow, "signal"] = 1
    df.loc[cross_down, "signal"] = -1
    return df


def exit_levels(entry: float, peak: float, cfg) -> tuple:
    """Precio de stop (el más alto entre stop loss fijo y trailing) y de take profit.

    `peak` es el precio máximo alcanzado desde la entrada.
    Devuelve (stop, take_profit); cualquiera puede ser None si está desactivado.
    """
    stops = []
    if cfg.stop_loss:
        stops.append(entry * (1 - cfg.stop_loss))
    if cfg.trailing_stop:
        stops.append(peak * (1 - cfg.trailing_stop))
    stop = max(stops) if stops else None
    tp = entry * (1 + cfg.take_profit) if cfg.take_profit else None
    return stop, tp


def describe(cfg) -> str:
    parts = [f"{cfg.ma_type.upper()} {cfg.fast}/{cfg.slow}"]
    if cfg.trend_filter:
        parts.append(f"tendencia>{cfg.trend_filter}")
    if cfg.adx_min:
        parts.append(f"ADX≥{cfg.adx_min:g}")
    parts.append(f"SL {cfg.stop_loss:.1%}" if cfg.stop_loss else "sin SL")
    if cfg.trailing_stop:
        parts.append(f"trailing {cfg.trailing_stop:.1%}")
    parts.append(f"TP {cfg.take_profit:.1%}" if cfg.take_profit else "sin TP")
    return " | ".join(parts)
