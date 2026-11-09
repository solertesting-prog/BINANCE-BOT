"""Estrategia: cruce de medias móviles con filtros, stops por volatilidad y tamaño por riesgo.

ENTRADA (+1): la media rápida cruza por ENCIMA de la lenta y, si están activados:
  - filtro de tendencia: el precio está sobre la media larga (p. ej. 200 velas)
  - filtro ADX: hay tendencia suficiente (ADX >= adx_min), para evitar mercados laterales
  - filtro de mercado: para monedas distintas de BTC, BTC está sobre su media larga
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


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder). <30 suele indicar sobreventa; >70 sobrecompra."""
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    down = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / down.replace(0, np.nan))


REGIME_LOOKBACK = 20      # velas para medir si la media larga sube o baja


def regime(df: pd.DataFrame, cfg) -> pd.Series:
    """Tipo de mercado en cada vela: "alcista", "lateral" o "bajista" ("" si faltan datos).

    alcista: precio sobre la media larga y con fuerza (ADX alto).
    lateral: sin fuerza (ADX bajo) y la media larga no está cayendo.
    bajista: el resto (precio bajo la media larga, o media larga cayendo)."""
    n = cfg.trend_filter or 200
    ma = df["ma_trend"] if "ma_trend" in df else moving_average(df["close"], n, cfg.ma_type)
    a = df["adx"] if "adx" in df else adx(df)
    level = cfg.adx_min or 20
    up = (df["close"] > ma) & (a >= level)
    flat = (a < level) & (ma >= ma.shift(REGIME_LOOKBACK) * 0.98)
    out = pd.Series("bajista", index=df.index)
    out[flat] = "lateral"
    out[up] = "alcista"
    out[ma.isna() | a.isna()] = ""
    return out


def warmup_candles(cfg) -> int:
    """Velas de historial necesarias para que los indicadores sean fiables."""
    need = max(cfg.slow, cfg.trend_filter or 0, 3 * 14 if cfg.adx_min else 0, cfg.atr_period * 3)
    return min(999, need * 3 if cfg.ma_type == "ema" else need + 10)


# ---------- señales ----------
def market_reference(symbol: str, cfg):
    """Par de referencia del filtro de mercado (p. ej. BTC/USDT para ETH/USDT), o None si no aplica."""
    base, quote = symbol.split("/")[0], symbol.split("/")[1]
    ref = (cfg.market_filter or "").upper()
    if not ref or not cfg.market_filter_ma or base == ref or quote == ref:
        return None
    return f"{ref}/{quote}"


def market_ok(ref_df: pd.DataFrame, cfg) -> pd.Series:
    """True en las velas en que la moneda de referencia cierra sobre su media larga."""
    ma = moving_average(ref_df["close"], cfg.market_filter_ma, cfg.ma_type)
    return (ref_df["close"] > ma).rename("market_ok")


def add_signals(df: pd.DataFrame, cfg, market: pd.Series = None) -> pd.DataFrame:
    """`market`: resultado de market_ok() de la moneda de referencia (None = sin filtro de mercado)."""
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
    if market is not None:                             # sin dato de la referencia: no entra
        df["market_ok"] = market.reindex(df.index, method="ffill").fillna(False).astype(bool)
        allow &= df["market_ok"]

    df["cross_up"] = cross_up
    df["regime"] = regime(df, cfg)
    df["signal"] = 0
    df.loc[cross_up & allow, "signal"] = 1
    df.loc[cross_down, "signal"] = -1

    if cfg.strategy_mode == "adaptive":
        # Mercado lateral: compra caídas exageradas (señal 2) y vende al volver a la media.
        mid = df["close"].rolling(cfg.bb_period).mean()
        low = mid - cfg.bb_std * df["close"].rolling(cfg.bb_period).std(ddof=0)
        df["rsi"], df["bb_mid"], df["bb_low"] = rsi(df["close"]), mid, low
        dip = (df["regime"] == "lateral") & (df["close"] < low) & (df["rsi"] < cfg.rsi_buy) & df["atr"].notna()
        if market is not None:
            dip &= df["market_ok"]
        df.loc[dip & (df["signal"] == 0), "signal"] = 2
        df["range_exit"] = df["close"] >= mid
    return df


def entry_kind(signal: int):
    """Tipo de entrada de una señal: "trend" (1), "range" (2) o None."""
    return {1: "trend", 2: "range"}.get(int(signal))


def should_exit(kind: str, row) -> str:
    """Motivo de salida por señal para una posición de ese tipo, o "" si no toca salir.
    `row`: última vela con señales (fila de add_signals)."""
    if kind == "range":
        return "vuelta a la media" if bool(getattr(row, "range_exit", False)) else ""
    return "cruce bajista" if int(row.signal) == -1 else ""


# ---------- explicación en lenguaje llano ----------
def _n(v, d=0):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def explain(df: pd.DataFrame, cfg, position: dict = None, stop: float = None) -> str:
    """Qué piensa el bot de esta moneda tras la última vela cerrada, en una frase."""
    r = df.iloc[-1]
    kind, f, sl = cfg.ma_type.upper(), cfg.fast, cfg.slow
    reg = r.get("regime", "")
    if position:
        k = position.get("kind", "trend")
        pnl = r["close"] / position["entry"] - 1
        out = (f"Mantengo la compra ({'+' if pnl > 0 else ''}{_n(pnl * 100, 1)} %). Vendería si "
               + ("el precio vuelve a su media de 20 velas" if k == "range"
                  else f"la media de {f} velas cruza por debajo de la de {sl}"))
        return out + (f" o si el precio baja a {_n(stop, 2 if stop >= 10 else 4)} (stop)." if stop else ".")
    sig = int(r["signal"])
    if sig == 1:
        return f"Señal de compra: la media de {f} velas acaba de cruzar por encima de la de {sl} y se cumplen los filtros."
    if sig == 2:
        return "Señal de compra en rango: mercado lateral y caída exagerada (precio bajo la banda inferior y RSI bajo)."
    blocks, needs = [], []
    if cfg.trend_filter and "ma_trend" in df and not r["close"] > r["ma_trend"]:
        blocks.append(f"el precio está por debajo de su media de {cfg.trend_filter} velas (tendencia de fondo bajista)")
        needs.append(f"el precio sube por encima de su media de {cfg.trend_filter} velas")
    if cfg.adx_min and "adx" in df and not r["adx"] >= cfg.adx_min:
        blocks.append(f"el mercado no tiene fuerza (ADX {_n(r['adx'])}, hace falta {_n(cfg.adx_min)})")
        needs.append(f"el mercado gana fuerza (ADX {_n(r['adx'])}, hace falta {_n(cfg.adx_min)})")
    if "market_ok" in df and not bool(r["market_ok"]):
        blocks.append(f"{cfg.market_filter.upper()} está en tendencia bajista (filtro de mercado)")
        needs.append(f"{cfg.market_filter.upper()} vuelve a tendencia alcista")
    if bool(r.get("cross_up", False)) and blocks:
        return "Hubo cruce alcista, pero no compro porque " + " y ".join(blocks) + "."
    extra = ""
    if cfg.strategy_mode == "adaptive":
        if reg == "lateral" and r.get("rsi") == r.get("rsi"):
            extra = (f" Mercado lateral: compraría en una caída exagerada (RSI por debajo de {_n(cfg.rsi_buy)}; "
                     f"ahora {_n(r['rsi'])}).")
        elif reg == "bajista":
            extra = " Mercado bajista: me quedo fuera."
    if pd.isna(r["ma_slow"]) or pd.isna(r["ma_fast"]):
        return "Aún no tengo suficientes velas para decidir."
    if r["ma_fast"] > r["ma_slow"]:
        below = (~(df["ma_fast"] > df["ma_slow"]))[::-1].to_numpy()
        ago = int(below.argmax()) if below.any() else len(df)
        txt = (f"La tendencia corta ya es alcista (la media de {f} velas cruzó sobre la de {sl} hace {ago} velas). "
               f"Solo compro justo en el cruce, así que espero al siguiente.")
        if blocks:
            txt += " Ahora mismo, además, " + " y ".join(blocks) + "."
        return txt + extra
    gap = (r["ma_slow"] / r["ma_fast"] - 1) * 100
    txt = (f"No compro: la media de {f} velas está un {_n(gap, 1)} % por debajo de la de {sl}. "
           f"Compraré cuando la cruce hacia arriba")
    txt += (", si además " + " y ".join(needs) + "." if needs else ".")
    return txt + extra


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
    if cfg.strategy_mode == "adaptive":
        parts.append("adaptativa")
    if cfg.trend_filter:
        parts.append(f"tendencia>{cfg.trend_filter}")
    if cfg.adx_min:
        parts.append(f"ADX≥{cfg.adx_min:g}")
    if cfg.market_filter and cfg.market_filter_ma:
        parts.append(f"filtro {cfg.market_filter.upper()}>{cfg.market_filter_ma}")
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
