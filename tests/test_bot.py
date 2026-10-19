"""Tests sin conexión a internet. Ejecuta:  python -m pytest tests -q"""
import sys
import types
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.modules.setdefault("ccxt", types.SimpleNamespace(binance=object))   # sin red ni ccxt real

from backtest import run_backtest          # noqa: E402
from config import CONFIG                  # noqa: E402
from strategy import add_signals, exit_levels   # noqa: E402

BASE = replace(CONFIG, fast=3, slow=6, ma_type="sma", trend_filter=0, adx_min=0,
               stop_loss=0, trailing_stop=0, take_profit=0, fee=0)


def candles(closes, start=1_700_000_000_000):
    c = np.asarray(closes, dtype=float)
    o = np.r_[c[0], c[:-1]]
    ts = start + np.arange(len(c)) * 3_600_000
    df = pd.DataFrame({"ts": ts, "open": o, "high": np.maximum(o, c) * 1.001,
                       "low": np.minimum(o, c) * 0.999, "close": c, "volume": 1.0})
    df["time"] = pd.to_datetime(df.ts, unit="ms", utc=True)
    return df.set_index("time")


UP_DOWN = [100] * 8 + list(range(101, 121)) + list(range(119, 90, -1))


def test_un_cruce_alcista_y_uno_bajista():
    s = add_signals(candles(UP_DOWN), BASE)["signal"]
    assert (s == 1).sum() == 1 and (s == -1).sum() == 1
    assert s[s == 1].index[0] < s[s == -1].index[0]


def test_sin_senales_durante_el_calentamiento():
    s = add_signals(candles(UP_DOWN), BASE)["signal"]
    assert (s.iloc[:BASE.slow] == 0).all()


def test_filtro_de_tendencia_bloquea_compras_bajo_la_media_larga():
    # caída larga y rebote corto: cruce alcista, pero el precio sigue bajo la media de 30
    closes = list(range(200, 120, -2)) + list(range(121, 131))
    sin = add_signals(candles(closes), BASE)["signal"]
    con = add_signals(candles(closes), replace(BASE, trend_filter=30))["signal"]
    assert (sin == 1).sum() >= 1 and (con == 1).sum() == 0


def test_media_rapida_debe_ser_menor():
    with pytest.raises(ValueError):
        add_signals(candles(UP_DOWN), replace(BASE, fast=10, slow=5))


def test_exit_levels_usa_el_stop_mas_alto():
    cfg = replace(BASE, stop_loss=0.03, trailing_stop=0.05, take_profit=0.10)
    stop, tp = exit_levels(100, 100, cfg)
    assert stop == pytest.approx(97) and tp == pytest.approx(110)
    stop, _ = exit_levels(100, 120, cfg)          # tras subir a 120, manda el trailing
    assert stop == pytest.approx(114)


def test_backtest_ganancia_con_cruce_y_sin_comisiones():
    r = run_backtest(candles(UP_DOWN), BASE)
    assert r["operaciones"] == 1
    t = r["trades"].iloc[0]
    assert t.motivo == "cruce bajista"
    assert r["capital_final"] == pytest.approx(1000 * (1 - BASE.position_pct)
                                               + 1000 * BASE.position_pct * t.salida_precio / t.entrada_precio)


def test_backtest_trailing_stop_protege_beneficio():
    closes = [100] * 8 + list(range(101, 121)) + [110, 109, 108, 107, 106, 105]   # caída brusca desde 120
    r = run_backtest(candles(closes), replace(BASE, trailing_stop=0.05))
    t = r["trades"].iloc[0]
    assert t.motivo == "trailing stop" and t.pnl_pct > 0
    assert t.salida_precio == pytest.approx(120 * 1.001 * 0.95, rel=1e-3)   # 5 % bajo el máximo


def test_backtest_stop_loss_sale_a_la_apertura_si_hay_hueco():
    closes = [100] * 8 + [101, 102, 103, 104, 105, 80, 79]   # desplome con hueco
    cfg = replace(BASE, stop_loss=0.03)
    r = run_backtest(candles(closes), cfg)
    t = r["trades"].iloc[0]
    assert t.motivo == "stop loss" and t.salida_precio <= t.entrada_precio * 0.97


def test_bot_en_modo_simulado(tmp_path, monkeypatch):
    """Recorre el bucle del bot con un exchange falso y comprueba que coincide con el backtest."""
    monkeypatch.chdir(tmp_path)
    import bot
    monkeypatch.setattr(bot, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(bot, "TRADES_FILE", tmp_path / "trades_log.csv")
    cfg = replace(BASE, mode="paper", paper_balance=1000, max_drawdown=0.5, telegram_token="")
    monkeypatch.setattr(bot, "cfg", cfg)
    import exchange
    rows = candles(UP_DOWN * 2).reset_index()[["ts", "open", "high", "low", "close", "volume"]].values.tolist()

    class FakeEx:
        i = 0
        def market(self, s): return {"limits": {"cost": {"min": 5}}}
        def parse_timeframe(self, t): return 3600
        def milliseconds(self): return int(rows[self.i][0]) + 3_599_000
        def fetch_ticker(self, s): return {"last": rows[self.i][4]}
        def fetch_ohlcv(self, s, tf, limit): return rows[max(0, self.i - limit + 1): self.i + 1]

    ex = FakeEx()
    monkeypatch.setattr(exchange, "fetch_closed_candles",
                        lambda e, s, tf, n: exchange.to_df(rows[max(0, e.i - n + 1): e.i + 1]))
    s = bot.load_state()
    broker = bot.Broker(ex, s)
    for ex.i in range(len(rows)):
        bot.step(ex, broker, s)
        bot.save_state(s)

    log = pd.read_csv(tmp_path / "trades_log.csv")
    bt = run_backtest(candles(UP_DOWN * 2), cfg)
    assert len(log) == bt["operaciones"] >= 2
    assert list(log.precio_salida) == pytest.approx(list(bt["trades"].salida_precio))
    assert not s["in_position"]
    assert s["paper_usdt"] == pytest.approx(bt["capital_final"])      # bot y backtest, idénticos
    assert bot.load_state()["paper_usdt"] == pytest.approx(s["paper_usdt"])   # el estado se guarda
