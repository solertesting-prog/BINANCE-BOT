"""Tests sin conexión a internet. Ejecuta:  python -m pytest tests -q"""
import json
import sys
import types
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.modules.setdefault("ccxt", types.SimpleNamespace(binance=object))   # sin red ni ccxt real

import bot                                                     # noqa: E402
import exchange                                                # noqa: E402
from backtest import run_backtest                              # noqa: E402
from config import CONFIG                                      # noqa: E402
from strategy import add_signals, exit_levels, position_spend  # noqa: E402

BASE = replace(CONFIG, symbols=("BTC/USDT",), fast=3, slow=6, ma_type="sma", trend_filter=0, adx_min=0,
               stop_mode="pct", stop_loss=0, trailing_stop=0, take_profit=0, fee=0, risk_per_trade=0,
               atr_period=3, max_open_positions=3, mode="paper", paper_balance=1000, max_drawdown=0.5,
               telegram_token="", exchange_stops=True)


def candles(closes, start=1_700_000_000_000):
    c = np.asarray(closes, dtype=float)
    o = np.r_[c[0], c[:-1]]
    ts = start + np.arange(len(c)) * 3_600_000
    df = pd.DataFrame({"ts": ts, "open": o, "high": np.maximum(o, c) * 1.001,
                       "low": np.minimum(o, c) * 0.999, "close": c, "volume": 1.0})
    df["time"] = pd.to_datetime(df.ts, unit="ms", utc=True)
    return df.set_index("time")


UP_DOWN = [100] * 8 + list(range(101, 121)) + list(range(119, 90, -1))


# ---------- estrategia ----------
def test_un_cruce_alcista_y_uno_bajista():
    s = add_signals(candles(UP_DOWN), BASE)["signal"]
    assert (s == 1).sum() == 1 and (s == -1).sum() == 1
    assert s[s == 1].index[0] < s[s == -1].index[0]


def test_sin_senales_durante_el_calentamiento():
    s = add_signals(candles(UP_DOWN), BASE)["signal"]
    assert (s.iloc[:BASE.slow] == 0).all()


def test_filtro_de_tendencia_bloquea_compras_bajo_la_media_larga():
    closes = list(range(200, 120, -2)) + list(range(121, 131))
    sin = add_signals(candles(closes), BASE)["signal"]
    con = add_signals(candles(closes), replace(BASE, trend_filter=30))["signal"]
    assert (sin == 1).sum() >= 1 and (con == 1).sum() == 0


def test_media_rapida_debe_ser_menor():
    with pytest.raises(ValueError):
        add_signals(candles(UP_DOWN), replace(BASE, fast=10, slow=5))


def test_stops_en_porcentaje_usan_el_mas_alto():
    cfg = replace(BASE, stop_loss=0.03, trailing_stop=0.05, take_profit=0.10)
    stop, tp, kind = exit_levels(100, 100, 0, cfg)
    assert stop == pytest.approx(97) and tp == pytest.approx(110) and kind == "stop loss"
    stop, _, kind = exit_levels(100, 120, 0, cfg)
    assert stop == pytest.approx(114) and kind == "trailing stop"


def test_stops_atr():
    cfg = replace(BASE, stop_mode="atr", atr_stop_mult=2, atr_trail_mult=3)
    stop, _, kind = exit_levels(100, 100, 2, cfg)          # ATR = 2
    assert stop == pytest.approx(96) and kind == "stop loss"
    stop, _, kind = exit_levels(100, 110, 2, cfg)          # máximo 110 -> 110 - 3×2 = 104
    assert stop == pytest.approx(104) and kind == "trailing stop"


def test_stop_atr_sin_atr_conocido_usa_porcentaje():
    cfg = replace(BASE, stop_mode="atr", stop_loss=0.03)
    stop, _, _ = exit_levels(100, 100, 0, cfg)
    assert stop == pytest.approx(97)


def test_tamano_por_riesgo():
    cfg = replace(BASE, risk_per_trade=0.01, position_pct=0.95)
    # capital 1000, riesgo 1 % = 10 USDT; stop 5 % por debajo -> 200 USDT de compra
    assert position_spend(1000, 1000, 100, 95, cfg) == pytest.approx(200)
    # stop muy cercano -> la compra queda limitada al tope (95 % del capital)
    assert position_spend(1000, 1000, 100, 99.9, cfg) == pytest.approx(950)
    # nunca gasta más de lo disponible
    assert position_spend(1000, 100, 100, 95, cfg) == pytest.approx(100)


# ---------- backtest ----------
def test_backtest_ganancia_con_cruce_y_sin_comisiones():
    r = run_backtest(candles(UP_DOWN), BASE)
    assert r["operaciones"] == 1
    t = r["trades"].iloc[0]
    assert t.motivo == "cruce bajista"
    assert r["capital_final"] == pytest.approx(1000 * (1 - BASE.position_pct)
                                               + 1000 * BASE.position_pct * t.salida_precio / t.entrada_precio)


def test_backtest_trailing_stop_protege_beneficio():
    closes = [100] * 8 + list(range(101, 121)) + [110, 109, 108, 107, 106, 105]
    r = run_backtest(candles(closes), replace(BASE, trailing_stop=0.05))
    t = r["trades"].iloc[0]
    assert t.motivo == "trailing stop" and t.pnl_pct > 0
    assert t.salida_precio == pytest.approx(120 * 1.001 * 0.95, rel=1e-3)


def test_backtest_stop_loss_sale_a_la_apertura_si_hay_hueco():
    closes = [100] * 8 + [101, 102, 103, 104, 105, 80, 79]
    r = run_backtest(candles(closes), replace(BASE, stop_loss=0.03))
    t = r["trades"].iloc[0]
    assert t.motivo == "stop loss" and t.salida_precio <= t.entrada_precio * 0.97


def test_backtest_riesgo_limita_la_perdida():
    closes = [100] * 8 + [101, 102, 103, 104, 105, 80, 79]
    r = run_backtest(candles(closes), replace(BASE, stop_loss=0.03, risk_per_trade=0.01))
    # con un hueco del 20 % se pierde más del 1 % previsto, pero mucho menos que sin control de riesgo
    assert -0.10 < r["rentabilidad"] < 0
    sin = run_backtest(candles(closes), replace(BASE, stop_loss=0.03))
    assert sin["rentabilidad"] < r["rentabilidad"]


# ---------- motor del bot (con un Binance simulado) ----------
class FakeExchange:
    """Imita lo justo de ccxt para probar el bot sin conexión."""
    has = {"createMarketBuyOrderWithCost": True}

    def __init__(self, rows_by_symbol):
        self.rows = rows_by_symbol
        self.i = 0
        self.markets = {s: {"limits": {"cost": {"min": 5}}} for s in rows_by_symbol}
        self.balance = {"USDT": 1000.0}
        self.orders, self.open_stops, self.cancelled = [], {}, []

    def load_markets(self):
        return self.markets

    def parse_timeframe(self, tf):
        return exchange.timeframe_seconds(tf)

    def milliseconds(self):
        return int(next(iter(self.rows.values()))[self.i][0]) + 3_599_000

    def fetch_ticker(self, s):
        return {"last": self.rows[s][self.i][4]}

    def fetch_ohlcv(self, s, tf, limit):
        return self.rows[s][max(0, self.i - limit + 1): self.i + 1]

    # --- privado ---
    def fetch_balance(self):
        return {"free": dict(self.balance), "total": dict(self.balance)}

    def amount_to_precision(self, s, a):
        return f"{a:.6f}"

    def price_to_precision(self, s, p):
        return f"{p:.2f}"

    def create_market_buy_order_with_cost(self, s, cost):
        price = self.fetch_ticker(s)["last"]
        base = s.split("/")[0]
        self.balance["USDT"] -= cost
        self.balance[base] = self.balance.get(base, 0) + cost / price
        self.orders.append(("buy", s, cost))
        return {"average": price, "filled": cost / price}

    def create_market_sell_order(self, s, amount):
        price = self.fetch_ticker(s)["last"]
        base = s.split("/")[0]
        self.balance[base] -= amount
        self.balance["USDT"] += amount * price
        self.orders.append(("sell", s, amount))
        return {"average": price}

    def create_order(self, s, type_, side, amount, price, params):
        oid = f"stop{len(self.orders)}"
        self.open_stops[oid] = {"symbol": s, "stop": params["stopPrice"], "amount": amount, "status": "open"}
        self.orders.append(("stop", s, params["stopPrice"]))
        return {"id": oid}

    def cancel_order(self, oid, s):
        self.open_stops[oid]["status"] = "canceled"
        self.cancelled.append(oid)

    def fetch_order(self, oid, s):
        o = self.open_stops[oid]
        return {"status": o["status"], "average": o.get("fill")}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(bot, "TRADES_FILE", tmp_path / "trades_log.csv")
    monkeypatch.setattr(bot.xch, "fetch_closed_candles",
                        lambda e, s, tf, n: exchange.to_df(e.rows[s][max(0, e.i - n + 1): e.i + 1]))
    return tmp_path


def rows_of(closes):
    return candles(closes).reset_index()[["ts", "open", "high", "low", "close", "volume"]].values.tolist()


def run_engine(engine, n):
    for engine.ex.i in range(n):
        engine.step()
        bot.save_state(engine.state)


def test_bot_simulado_coincide_con_el_backtest(isolated):
    closes = UP_DOWN * 2
    ex = FakeExchange({"BTC/USDT": rows_of(closes)})
    e = bot.Engine(BASE, ex)
    e.connect()
    run_engine(e, len(closes))
    log = bot.read_trades()
    bt = run_backtest(candles(closes), BASE)
    assert len(log) == bt["operaciones"] >= 2
    assert [float(t["precio_salida"]) for t in log] == pytest.approx(list(bt["trades"].salida_precio))
    assert e.state["paper_usdt"] == pytest.approx(bt["capital_final"])
    assert bot.load_state(BASE)["paper_usdt"] == pytest.approx(e.state["paper_usdt"])


def test_bot_varias_monedas_y_limite_de_posiciones(isolated):
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN), "ETH/USDT": rows_of([x / 10 for x in UP_DOWN]),
                       "SOL/USDT": rows_of([x / 100 for x in UP_DOWN])})
    cfg = replace(BASE, symbols=("BTC/USDT", "ETH/USDT", "SOL/USDT"), max_open_positions=2, position_pct=0.3)
    e = bot.Engine(cfg, ex)
    e.connect()
    run_engine(e, 20)                      # tras el cruce alcista
    assert len(e.state["positions"]) == 2  # la tercera señal se ignora por el límite
    assert e.snapshot()["positions"][0]["symbol"] == "BTC/USDT"


def test_bot_real_coloca_stop_en_binance_y_lo_sube(isolated):
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    cfg = replace(BASE, mode="live", stop_loss=0.03, trailing_stop=0.05)
    e = bot.Engine(cfg, ex)
    e.connect()
    run_engine(e, 15)
    pos = e.state["positions"]["BTC/USDT"]
    assert pos["stop_order"] is not None                       # stop puesto en Binance
    first = pos["stop_order"]["stop"]
    run_engine_from(e, 15, 27)                                 # el precio sigue subiendo
    assert e.state["positions"]["BTC/USDT"]["stop_order"]["stop"] > first   # y el stop sube con él
    assert ex.cancelled                                        # cancelando el anterior


def run_engine_from(engine, a, b):
    for engine.ex.i in range(a, b):
        engine.step()


def test_bot_real_detecta_stop_ejecutado_en_binance(isolated):
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    cfg = replace(BASE, mode="live", stop_loss=0.03)
    e = bot.Engine(cfg, ex)
    e.connect()
    run_engine(e, 15)
    so = e.state["positions"]["BTC/USDT"]["stop_order"]
    ex.open_stops[so["id"]].update(status="closed", fill=so["stop"])     # Binance ejecuta el stop
    ex.balance["BTC"] = 0
    run_engine_from(e, 15, 16)
    assert "BTC/USDT" not in e.state["positions"]
    assert bot.read_trades()[-1]["motivo"] == "stop loss (Binance)"
    assert not any(o[0] == "sell" for o in ex.orders)                     # no vende dos veces


def test_reconciliacion_posicion_vendida_fuera_del_bot(isolated):
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    cfg = replace(BASE, mode="live", exchange_stops=False)
    bot.save_state({**bot.new_state(cfg), "positions": {"BTC/USDT": {
        "qty": 1.0, "entry": 100.0, "peak": 100.0, "atr": 1.0, "entry_time": "x", "spent": 100.0,
        "stop_order": None}}})
    e = bot.Engine(cfg, ex)
    e.connect()
    e.reconcile()                                   # la cuenta no tiene BTC
    assert e.state["positions"] == {}
    assert bot.read_trades()[-1]["motivo"] == "cerrada fuera del bot"


def test_interruptor_de_seguridad(isolated):
    closes = [100] * 8 + list(range(101, 111)) + [50] * 5
    ex = FakeExchange({"BTC/USDT": rows_of(closes)})
    cfg = replace(BASE, max_drawdown=0.2)
    e = bot.Engine(cfg, ex)
    e.connect()
    run_engine(e, len(closes))
    assert e.state["halted"] and e.state["positions"] == {}
    with pytest.raises(RuntimeError):
        e.start()
    e.resume_after_halt()
    assert not e.state["halted"]


def test_migra_estado_de_la_version_anterior(isolated):
    (isolated / "state.json").write_text(json.dumps(
        {"in_position": True, "qty": 0.5, "entry": 100, "peak": 110, "entry_time": "t",
         "last_candle": 123, "paper_usdt": 50, "start_equity": 1000, "halted": False}))
    s = bot.load_state(BASE)
    assert s["positions"]["BTC/USDT"]["qty"] == 0.5 and s["paper_usdt"] == 50
    assert s["last_candle"]["BTC/USDT"] == 123


# ---------- panel ----------
def test_panel_api(isolated, monkeypatch):
    import threading
    import urllib.error
    import urllib.request
    from datetime import datetime, timezone

    import panel
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    # el "reloj" del bot sigue a las velas simuladas, para que las marcas caigan en el gráfico
    monkeypatch.setattr(bot, "now_iso", lambda: datetime.fromtimestamp(
        ex.milliseconds() / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    e = bot.Engine(BASE, ex)
    e.connect()
    run_engine(e, 15)
    server = panel.make_server(e, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        st = json.loads(urllib.request.urlopen(base + "/api/status").read())
        assert st["mode"] == "paper" and len(st["positions"]) == 1
        ch = json.loads(urllib.request.urlopen(base + "/api/candles?symbol=BTC/USDT").read())
        assert ch["candles"] and ch["markers"]
        assert b"<html" in urllib.request.urlopen(base + "/").read().lower()
        # sin la cabecera de seguridad, las acciones se rechazan
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(urllib.request.Request(base + "/api/close?symbol=BTC/USDT", method="POST"))
        req = urllib.request.Request(base + "/api/close?symbol=BTC/USDT", method="POST", headers={"X-Panel": "1"})
        assert json.loads(urllib.request.urlopen(req).read())["ok"]
        assert e.state["positions"] == {}
        assert bot.read_trades()[-1]["motivo"] == "cierre manual"
        # desde otro "dominio" (ataque DNS rebinding) no se puede ni leer
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(urllib.request.Request(base + "/api/status", headers={"Host": "evil.com"}))
    finally:
        server.shutdown()
