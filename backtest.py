"""Backtest de la estrategia con datos históricos de Binance.

Uso:
    python backtest.py                                   # parámetros de config.py, último año
    python backtest.py --days 730 --timeframe 4h
    python backtest.py --ma ema --trend 200 --adx 20 --trailing 0.05
    python backtest.py --html informe.html               # informe visual con gráficos
    python backtest.py --csv datos.csv                   # CSV propio (ts,open,high,low,close,volume)

Los datos descargados se guardan en data/ para no volver a bajarlos en el mismo día.
"""
import argparse
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd

from config import CONFIG, Config
from strategy import add_signals, describe, exit_levels

DATA_DIR = Path("data")


# ---------- datos ----------
def read_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path)[["ts", "open", "high", "low", "close", "volume"]]
    df["time"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.drop_duplicates("ts").set_index("time")


def load_data(symbol: str, timeframe: str, days: int, csv: str | None = None) -> pd.DataFrame:
    if csv:
        return read_csv(csv)
    DATA_DIR.mkdir(exist_ok=True)
    cache = DATA_DIR / f"{symbol.replace('/', '')}_{timeframe}_{days}d_{date.today()}.csv"
    if cache.exists():
        return read_csv(cache)
    from exchange import fetch_history, make_exchange
    print(f"Descargando {days} días de {symbol} {timeframe} desde Binance...")
    df = fetch_history(make_exchange(CONFIG), symbol, timeframe, days)
    df.to_csv(cache, index=False)
    return df


# ---------- simulación ----------
def run_backtest(df: pd.DataFrame, cfg: Config, initial: float = 1000.0,
                 start=None, end=None) -> dict:
    """Simula la estrategia. `start`/`end` (fechas) recortan el periodo operado,
    pero los indicadores se calculan con todo el historial (sin "calentamiento" perdido)."""
    df = add_signals(df, cfg)
    df = df.loc[start:end]
    if len(df) < 2:
        raise ValueError("No hay suficientes velas en el periodo")

    cash, qty, entry, peak, entry_time = initial, 0.0, 0.0, 0.0, None
    trades, equity = [], []
    in_market = 0

    for row in df.itertuples():
        t = row.Index
        if qty > 0:
            in_market += 1
            stop, tp = exit_levels(entry, peak, cfg)   # niveles con el máximo de velas ANTERIORES
            exit_price, reason = None, None
            if stop and row.low <= stop:
                exit_price = min(stop, row.open)       # si abre por debajo, sale a la apertura
                fixed = entry * (1 - cfg.stop_loss) if cfg.stop_loss else 0
                reason = "trailing stop" if stop > fixed else "stop loss"
            elif tp and row.high >= tp:
                exit_price, reason = max(tp, row.open), "take profit"
            elif row.signal == -1:
                exit_price, reason = row.close, "cruce bajista"

            if exit_price:
                cash += qty * exit_price * (1 - cfg.fee)
                trades.append({
                    "entrada": entry_time, "salida": t,
                    "entrada_precio": round(entry, 2), "salida_precio": round(exit_price, 2),
                    "motivo": reason,
                    "pnl_pct": (exit_price / entry) * (1 - cfg.fee) ** 2 - 1,
                })
                qty = 0.0
            else:
                peak = max(peak, row.high)
        elif row.signal == 1:
            spend = cash * cfg.position_pct
            qty = spend * (1 - cfg.fee) / row.close
            cash -= spend
            entry = peak = row.close
            entry_time = t
        equity.append(cash + qty * row.close)

    eq = pd.Series(equity, index=df.index)
    tr = pd.DataFrame(trades)
    return {
        "cfg": cfg,
        "periodo": f"{df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}",
        "initial": initial,
        "capital_final": eq.iloc[-1],
        "abierta": qty > 0,
        "equity": eq,
        "buy_hold": initial * df.close / df.close.iloc[0],
        "trades": tr,
        **metrics(eq, tr, df, in_market, initial),
    }


def metrics(eq: pd.Series, tr: pd.DataFrame, df: pd.DataFrame, in_market: int, initial: float) -> dict:
    n = len(tr)
    wins = tr[tr.pnl_pct > 0] if n else tr
    losses = tr[tr.pnl_pct <= 0] if n else tr
    gw = wins.pnl_pct.sum() if n else 0.0
    gl = -losses.pnl_pct.sum() if n else 0.0
    dd = (eq / eq.cummax() - 1).min()
    ret = eq.iloc[-1] / initial - 1
    return {
        "rentabilidad": ret,
        "buy_and_hold": df.close.iloc[-1] / df.close.iloc[0] - 1,
        "operaciones": n,
        "acierto": len(wins) / n if n else 0.0,
        "profit_factor": gw / gl if gl else (float("inf") if gw else 0.0),
        "media_operacion": tr.pnl_pct.mean() if n else 0.0,
        "max_drawdown": dd,
        "ret_dd": ret / abs(dd) if dd else 0.0,      # rentabilidad / drawdown: más alto = mejor
        "exposicion": in_market / len(df),           # % del tiempo con posición abierta
    }


def print_report(r: dict):
    cfg = r["cfg"]
    print(f"\n=== Backtest {cfg.symbol} {cfg.timeframe} | {describe(cfg)} ===")
    print(f"Periodo:            {r['periodo']}")
    print(f"Capital final:      {r['capital_final']:.2f} USDT{'  (con posición abierta)' if r['abierta'] else ''}")
    print(f"Rentabilidad:       {r['rentabilidad']:+.2%}")
    print(f"Comprar y mantener: {r['buy_and_hold']:+.2%}")
    print(f"Máx. drawdown:      {r['max_drawdown']:.2%}")
    print(f"Operaciones:        {r['operaciones']}  (acierto {r['acierto']:.1%}, media {r['media_operacion']:+.2%})")
    print(f"Profit factor:      {r['profit_factor']:.2f}")
    print(f"Tiempo invertido:   {r['exposicion']:.0%}")
    if r["operaciones"]:
        print("\nMotivos de salida:")
        print(r["trades"].motivo.value_counts().rename_axis(None).to_string(header=False))


# ---------- línea de comandos ----------
def add_common_args(p: argparse.ArgumentParser):
    p.add_argument("--symbol", default=CONFIG.symbol)
    p.add_argument("--timeframe", default=CONFIG.timeframe)
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--csv", help="CSV con columnas ts,open,high,low,close,volume")


def main():
    p = argparse.ArgumentParser(description="Backtest del bot de cruce de medias")
    add_common_args(p)
    p.add_argument("--fast", type=int, default=CONFIG.fast)
    p.add_argument("--slow", type=int, default=CONFIG.slow)
    p.add_argument("--ma", choices=["sma", "ema"], default=CONFIG.ma_type)
    p.add_argument("--trend", type=int, default=CONFIG.trend_filter, help="filtro de tendencia (0 = no)")
    p.add_argument("--adx", type=float, default=CONFIG.adx_min, help="ADX mínimo (0 = no)")
    p.add_argument("--sl", type=float, default=CONFIG.stop_loss)
    p.add_argument("--trailing", type=float, default=CONFIG.trailing_stop)
    p.add_argument("--tp", type=float, default=CONFIG.take_profit)
    p.add_argument("--export", help="guarda las operaciones en este CSV")
    p.add_argument("--html", help="genera un informe visual en este archivo HTML")
    a = p.parse_args()

    cfg = replace(CONFIG, symbol=a.symbol, timeframe=a.timeframe, fast=a.fast, slow=a.slow,
                  ma_type=a.ma, trend_filter=a.trend, adx_min=a.adx,
                  stop_loss=a.sl, trailing_stop=a.trailing, take_profit=a.tp)
    df = load_data(cfg.symbol, cfg.timeframe, a.days, a.csv)
    r = run_backtest(df, cfg)
    print_report(r)
    if a.export and r["operaciones"]:
        r["trades"].to_csv(a.export, index=False)
        print(f"\nOperaciones guardadas en {a.export}")
    if a.html:
        from report import write_html
        write_html(r, a.html)
        print(f"\nInforme guardado en {a.html} (ábrelo con el navegador)")


if __name__ == "__main__":
    main()
