"""Página pública de resultados: un enlace de solo lectura para enseñar cómo va el bot.

- Desactivada por defecto. Al activarla se crea un enlace con un código aleatorio (/p/<código>);
  quien lo tenga puede ver la página, sin iniciar sesión. Desactivarla invalida el enlace.
- Solo muestra porcentajes: la evolución del capital, las operaciones cerradas y la comparación
  con comprar y mantener BTC. Nunca muestra importes, saldos, claves ni datos personales.
- Indica siempre si los resultados son simulados, de testnet o de una cuenta real.
"""
import hmac
import secrets
import time

from dotenv import dotenv_values, set_key

import bot
import config as C
from strategy import describe

_cache = {}


def new_token() -> str:
    return secrets.token_urlsafe(18)


def stored_token() -> str:
    vals = dotenv_values(C.ENV_FILE) if C.ENV_FILE.exists() else {}
    return (vals.get("PUBLIC_TOKEN") or "").strip()


def set_token(token: str):
    if not C.ENV_FILE.exists():
        C.ENV_FILE.touch()
    set_key(str(C.ENV_FILE), "PUBLIC_TOKEN", token, quote_mode="never")


def matches(token: str, stored: str) -> bool:
    return bool(stored) and len(token) >= 16 and hmac.compare_digest(token.encode(), stored.encode())


def _benchmark(data_ex, quote: str, t0: int, t1: int):
    """Curva de comprar y mantener BTC entre t0 y t1 (segundos), en base 100."""
    sym = f"BTC/{quote}"
    if sym not in getattr(data_ex, "markets", {sym: 1}):
        return None
    tf = "1h" if t1 - t0 <= 20 * 86400 else "4h"
    rows = bot.retry(data_ex.fetch_ohlcv, sym, tf, since=t0 * 1000, limit=1000)
    pts = [[int(r[0] // 1000), float(r[4])] for r in rows if r[0] // 1000 <= t1 + 14400]
    if len(pts) < 2:
        return None
    return [[t, round(p / pts[0][1] * 100, 3)] for t, p in pts]


def data(engine, data_ex) -> dict:
    """Lo que enseña la página pública (con caché de 5 minutos)."""
    key = id(engine)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    cfg, s = engine.cfg, engine.state
    hist = s["equity_history"]
    start = s["start_equity"] or (hist[0][1] if hist else None)
    curve = [[t, round(v / start * 100, 3)] for t, v in hist] if start else []
    trades = bot.read_trades(engine.files.trades)
    wins = sum(1 for t in trades if float(t["pnl_pct"] or 0) > 0)
    peak, dd = 100.0, 0.0
    for _, v in curve:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    bench = None
    if len(curve) >= 2:
        try:
            bench = _benchmark(data_ex, cfg.quote, curve[0][0], curve[-1][0])
        except Exception:
            bench = None
    out = {
        "mode": "paper" if cfg.mode == "paper" else ("testnet" if cfg.testnet else "live"),
        "exchange": getattr(engine.ex, "name", None) or cfg.exchange,
        "symbols": list(cfg.symbols), "timeframe": cfg.timeframe, "strategy": describe(cfg),
        "since": hist[0][0] if hist else None, "updated": int(time.time()),
        "running": engine.is_running(),
        "return": curve[-1][1] / 100 - 1 if curve else None,
        "benchmark_return": bench[-1][1] / 100 - 1 if bench else None,
        "max_drawdown": dd, "trades_count": len(trades),
        "win_rate": wins / len(trades) if trades else None,
        "open_positions": len(s["positions"]),
        "curve": curve[-1500:], "benchmark": bench,
        "trades": [{"par": t["par"], "entrada": t["entrada"], "salida": t["salida"], "motivo": t["motivo"],
                    "pnl_pct": float(t["pnl_pct"] or 0)} for t in trades[-100:][::-1]],
    }
    _cache[key] = (time.time(), out)
    if len(_cache) > 200:
        _cache.clear()
    return out
