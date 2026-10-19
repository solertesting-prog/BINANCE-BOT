"""Estrategia: cruce de medias móviles con filtros, stops por volatilidad y tamaño por riesgo.

ENTRADA (+1): la media rápida cruza por ENCIMA de la lenta y, si están activados:
  - filtro de tendencia: el precio está sobre la media larga (p. ej. 200 velas)
  - filtro ADX: hay tendencia suficiente (ADX >= adx_min), para evitar mercados laterales
SALIDA (-1): la media rápida cruza por DEBAJO de la lenta.
Además: stop inicial, stop dinámico (trailing) y take profit opcional (ver exit_levels).

TAMAÑO: se compra la cantidad con la que, si salta el stop, se pierde `risk_per_trade`
del capital (p. ej. 1 %), con un tope de `position_pct` del capital.

Este archivo lo usan TANTO el backtest COMO el bot, así ambos se comportan igual.
Solo opera en largo (spot, sin apalancamiento ni cortos).
"""
import numpy as np
import pandas as pd


# ---------- indicadores ----------
def moving_average(s: pd.Series, n: int, kind: str = "sma") -> pd.Series:
    if kind == "ema":
        return s.ewm(span=n, adjust=False, min_periods=n).mean()
    return s.rolling(n).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    return pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average True Range (Wilder): cuánto se mueve el precio por vela, de media."""
    return true_range(df).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average Directional Index (Wilder). >20-25 suele indicar tendencia."""
    h, l = df["high"], df["low"]
    up, down = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    a = 1 / n
    tr = true_range(df).ewm(alpha=a, adjust=False, min_periods=n).mean()
    pdi = 100 * plus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / tr
    mdi = 100 * minus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / tr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=a, adjust=False, min_periods=n).mean()


def warmup_candles(cfg) -> int:
    """Velas de historial necesarias para que los indicadores sean fiables."""
    need = max(cfg.slow, cfg.trend_filter or 0, 3 * 14 if cfg.adx_min else 0, cfg.atr_period * 3)
    return min(999, need * 3 if cfg.ma_type == "ema" else need + 10)


# ---------- señales ----------
def add_signals(df: pd.DataFrame, cfg) -> pd.DataFrame:
    if cfg.fast >= cfg.slow:
        raise ValueError("La media rápida debe ser menor que la lenta")
    df = df.copy()
    df["ma_fast"] = moving_average(df["close"], cfg.fast, cfg.ma_type)
    df["ma_slow"] = moving_average(df["close"], cfg.slow, cfg.ma_type)
    df["atr"] = atr(df, cfg.atr_period)

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
    if cfg.stop_mode == "atr":
        allow &= df["atr"].notna()

    df["signal"] = 0
    df.loc[cross_up & allow, "signal"] = 1
    df.loc[cross_down, "signal"] = -1
    return df


# ---------- stops y tamaño ----------
def initial_stop(entry: float, atr_value: float, cfg):
    """Stop inicial fijado en el momento de la compra (o None si no hay)."""
    if cfg.stop_mode == "atr" and atr_value:
        return entry - cfg.atr_stop_mult * atr_value if cfg.atr_stop_mult else None
    # modo "pct", o ATR desconocido (p. ej. posición heredada): stop en porcentaje
    return entry * (1 - cfg.stop_loss) if cfg.stop_loss else None


def exit_levels(entry: float, peak: float, atr_value: float, cfg) -> tuple:
    """Devuelve (stop, take_profit, tipo_de_stop).

    El stop es el MÁS ALTO entre el inicial y el dinámico (trailing), así solo puede subir.
    `peak` es el precio máximo alcanzado desde la entrada; `atr_value` el ATR al comprar.
    """
    first = initial_stop(entry, atr_value, cfg)
    trails = []
    if cfg.stop_mode == "atr" and cfg.atr_trail_mult and atr_value:
        trails.append(peak - cfg.atr_trail_mult * atr_value)
    if cfg.trailing_stop:
        trails.append(peak * (1 - cfg.trailing_stop))
    trail = max(trails) if trails else None

    candidates = [x for x in (first, trail) if x]
    stop = max(candidates) if candidates else None
    kind = "trailing stop" if trail and (first is None or trail > first) else "stop loss"
    tp = entry * (1 + cfg.take_profit) if cfg.take_profit else None
    return stop, tp, kind


def position_spend(equity: float, cash: float, price: float, stop, cfg) -> float:
    """USDT a gastar en una compra, según el riesgo por operación y los topes."""
    cap = min(cash, equity * cfg.position_pct)
    if cfg.risk_per_trade and stop and 0 < stop < price:
        risk_amount = equity * cfg.risk_per_trade
        qty = risk_amount / (price - stop)
        return max(0.0, min(cap, qty * price))
    return max(0.0, cap)


def describe(cfg) -> str:
    parts = [f"{cfg.ma_type.upper()} {cfg.fast}/{cfg.slow}"]
    if cfg.trend_filter:
        parts.append(f"tendencia>{cfg.trend_filter}")
    if cfg.adx_min:
        parts.append(f"ADX≥{cfg.adx_min:g}")
    if cfg.stop_mode == "atr":
        parts.append(f"stop {cfg.atr_stop_mult:g}×ATR" if cfg.atr_stop_mult else "sin stop")
        if cfg.atr_trail_mult:
            parts.append(f"trailing {cfg.atr_trail_mult:g}×ATR")
    else:
        parts.append(f"SL {cfg.stop_loss:.1%}" if cfg.stop_loss else "sin SL")
    if cfg.trailing_stop:
        parts.append(f"trailing {cfg.trailing_stop:.1%}")
    parts.append(f"TP {cfg.take_profit:.1%}" if cfg.take_profit else "sin TP")
    if cfg.risk_per_trade:
        parts.append(f"riesgo {cfg.risk_per_trade:.1%}")
    return " | ".join(parts)
