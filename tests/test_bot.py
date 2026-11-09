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
               telegram_token="", exchange_stops=True, market_filter="")


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
    id, name = "binance", "Binance"

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


def test_filtro_de_mercado_bloquea_altcoins_si_btc_baja(isolated):
    from strategy import market_reference
    cfg = replace(BASE, symbols=("BTC/USDT", "ETH/USDT"), market_filter="BTC", market_filter_ma=5)
    assert market_reference("ETH/USDT", cfg) == "BTC/USDT"
    assert market_reference("BTC/USDT", cfg) is None
    assert market_reference("ETH/BTC", cfg) is None
    assert market_reference("ETH/USDT", replace(cfg, market_filter="")) is None
    # BTC en caída continua (siempre bajo su media) y ETH con un cruce alcista: no compra ETH
    btc_down = [200 - i for i in range(len(UP_DOWN))]
    ex = FakeExchange({"BTC/USDT": rows_of(btc_down), "ETH/USDT": rows_of([x / 10 for x in UP_DOWN])})
    e = bot.Engine(cfg, ex)
    e.connect()
    run_engine(e, 20)
    assert e.state["positions"] == {}
    # con BTC subiendo, la misma señal de ETH sí compra
    btc_up = [100 + i for i in range(len(UP_DOWN))]
    ex2 = FakeExchange({"BTC/USDT": rows_of(btc_up), "ETH/USDT": rows_of([x / 10 for x in UP_DOWN])})
    e2 = bot.Engine(replace(cfg, symbols=("ETH/USDT",)), ex2)
    e2.state = bot.load_state(cfg) | {"positions": {}, "last_candle": {}, "paper_usdt": 1000, "start_equity": None}
    e2.connect()
    run_engine(e2, 20)
    assert "ETH/USDT" in e2.state["positions"]
    # el backtest aplica el mismo filtro
    bt_off = run_backtest(candles([x / 10 for x in UP_DOWN]), replace(cfg, symbols=("ETH/USDT",)),
                          market_df=candles(btc_down))
    bt_on = run_backtest(candles([x / 10 for x in UP_DOWN]), replace(cfg, symbols=("ETH/USDT",)),
                         market_df=candles(btc_up))
    assert bt_off["operaciones"] == 0 and bt_on["operaciones"] >= 1


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
    assert bot.read_trades()[-1]["motivo"] == "stop loss (exchange)"
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


# ---------- asistente de configuración (exchanges simulados) ----------
class AuthenticationError(Exception):
    pass


class FakeOkx:
    """Exchange simulado con passphrase, testnet y stops en el exchange."""
    id, name = "okx", "OKX"
    has = {"fetchOHLCV": True, "createStopLossOrder": True}
    requiredCredentials = {"apiKey": True, "secret": True, "password": True, "uid": False}
    urls = {"test": {"api": "https://test"}, "www": "https://www.okx.example"}
    timeframes = {"1h": "1H", "4h": "4H", "1d": "1D"}

    def __init__(self, params=None):
        self.params = params or {}
        for k in ("apiKey", "secret", "password", "uid"):
            setattr(self, k, self.params.get(k))
        self.sandbox = False

    def set_sandbox_mode(self, v):
        self.sandbox = v

    def load_markets(self):
        mk = lambda b, q: {"spot": True, "active": True, "base": b, "quote": q, "taker": 0.0015}
        return {"BTC/EUR": mk("BTC", "EUR"), "ETH/EUR": mk("ETH", "EUR"), "BTC/USDT": mk("BTC", "USDT"),
                "BTC/USDT:USDT": {"spot": False, "base": "BTC", "quote": "USDT"}}

    def fetch_balance(self):
        if self.apiKey != "buena":
            raise AuthenticationError("invalid key")
        return {"total": {"EUR": 500.0, "BTC": 0.0}}


class FakeBitflyer(FakeOkx):
    id, name = "bitflyer", "bitFlyer"
    has = {"fetchOHLCV": None}
    urls = {"www": "https://bitflyer.example"}


@pytest.fixture
def fake_setup(tmp_path, monkeypatch):
    import config as C
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(bot, "TRADES_FILE", tmp_path / "trades_log.csv")
    monkeypatch.setattr(C, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(C, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(exchange, "ccxt", types.SimpleNamespace(
        okx=FakeOkx, bitflyer=FakeBitflyer, exchanges=["bitflyer", "okx", "otro"]))
    import setup_api
    setup_api._cache.clear()
    return tmp_path


def _env_snapshot():
    import os
    return dict(os.environ)


def _env_restore(snap):
    import os
    os.environ.clear()
    os.environ.update(snap)


def test_catalogo_de_exchanges(fake_setup):
    import setup_api
    cat = setup_api.catalog()
    by = {x["id"]: x for x in cat["featured"]}
    okx, bf = by["okx"], by["bitflyer"]
    assert okx["compatible"] and okx["testnet"] and okx["exchange_stops"]
    assert [c["key"] for c in okx["credentials"]] == ["apiKey", "secret", "password"]
    assert not bf["compatible"] and "velas" in bf["reason"]
    assert "otro" in cat["others"] and "okx" not in cat["others"]


def test_mercados_solo_spot(fake_setup):
    import setup_api
    m = setup_api.markets("okx", False)
    assert {x["symbol"] for x in m["markets"]} == {"BTC/EUR", "ETH/EUR", "BTC/USDT"}
    assert m["quotes"][0]["quote"] == "USDT" and m["quotes"][1]["quote"] == "EUR"


def test_probar_conexion(fake_setup):
    import setup_api
    bad = setup_api.test_connection("okx", False, {"apiKey": "mala", "secret": "s", "password": "p"})
    assert not bad["ok"] and "claves no son correctas" in bad["error"]
    miss = setup_api.test_connection("okx", False, {"apiKey": "buena", "secret": "s"})
    assert not miss["ok"] and "Passphrase" in miss["error"]
    ok = setup_api.test_connection("okx", False, {"apiKey": "buena", "secret": "s", "password": "p"})
    assert ok["ok"] and ok["balances"][0] == {"asset": "EUR", "total": 500.0}


def test_guardar_configuracion_y_claves(fake_setup):
    import config as C
    import setup_api
    snap = _env_snapshot()
    try:
        e = bot.Engine(BASE, FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))
        body = {"exchange": "okx", "mode": "live", "testnet": False, "symbols": ["btc/eur", "ETH/EUR"],
                "timeframe": "4h", "risk_per_trade": 0.02, "credentials": {}}
        with pytest.raises(ValueError, match="Faltan claves"):
            setup_api.validate_and_save(e, body)
        with pytest.raises(ValueError, match="no tiene"):
            setup_api.validate_and_save(e, {**body, "symbols": ["DOGE/EUR"]})
        with pytest.raises(ValueError, match="mismo"):
            setup_api.validate_and_save(e, {**body, "symbols": ["BTC/EUR", "BTC/USDT"]})
        body["credentials"] = {"apiKey": "buena", "secret": "sec", "password": "frase-secreta"}
        assert setup_api.validate_and_save(e, body) is True          # cambia de exchange
        env = (fake_setup / ".env").read_text()
        assert "OKX_API_KEY=buena" in env and "OKX_API_PASSWORD=frase-secreta" in env and "MODE=live" in env
        assert "buena" not in (fake_setup / "settings.json").read_text()   # las claves NO van aquí
        cfg = C.load_config()
        assert (cfg.exchange, cfg.symbols, cfg.quote, cfg.api_password) == ("okx", ("BTC/EUR", "ETH/EUR"), "EUR", "frase-secreta")
        assert cfg.fee == 0.0015 and cfg.risk_per_trade == 0.02
        # al volver a abrir el asistente solo se ven los 4 últimos caracteres
        saved = setup_api.saved_for("okx", False)
        assert saved["password"] == "•••• reta"
        assert setup_api.saved_for("okx", False)["secret"] == "••••"            # las cortas, ocultas del todo
        # guardar de nuevo sin escribir las claves las mantiene
        body["credentials"] = {}
        setup_api.validate_and_save(e, body)
        assert C.load_config().api_key == "buena"
    finally:
        _env_restore(snap)


def test_no_cambia_de_exchange_con_posiciones_abiertas(fake_setup):
    import setup_api
    e = bot.Engine(BASE, FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))
    e.state["positions"]["BTC/USDT"] = {"qty": 1, "entry": 100, "peak": 100, "atr": 1, "spent": 100,
                                        "entry_time": None, "stop_order": None}
    body = {"exchange": "okx", "mode": "paper", "symbols": ["BTC/EUR"], "timeframe": "4h", "risk_per_trade": 0.01}
    with pytest.raises(ValueError, match="posiciones abiertas"):
        setup_api.validate_and_save(e, body)
    with pytest.raises(ValueError, match="no es compatible|velas"):
        setup_api.validate_and_save(e, {**body, "exchange": "bitflyer"})


def test_panel_aplica_la_configuracion_y_reinicia_el_motor(fake_setup):
    import panel
    snap = _env_snapshot()
    try:
        e = bot.Engine(BASE, FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))
        e.connect()
        e.state["start_equity"] = 1234
        app = panel.PanelApp(e)
        rows = {"BTC/EUR": rows_of(UP_DOWN)}
        r = app.apply_setup({"exchange": "okx", "mode": "paper", "symbols": ["BTC/EUR"], "timeframe": "1d",
                             "risk_per_trade": 0.01, "paper_balance": 5000},
                            engine_factory=lambda cfg: bot.Engine(cfg, FakeExchange(rows)),
                            data_ex_factory=lambda cfg: None)
        assert r["ok"] and r["venue_changed"]
        new = app.engine
        assert new is not e and new.cfg.exchange == "okx" and new.cfg.timeframe == "1d"
        assert new.state["start_equity"] is None and new.state["paper_usdt"] == 5000
        assert new.snapshot()["quote"] == "EUR"
    finally:
        _env_restore(snap)


# ---------- licencias (servidor de Lemon Squeezy simulado) ----------
class FakeLemon:
    """Imita la API de licencias de Lemon Squeezy."""
    def __init__(self, store_id=111, product_id=222, limit=1):
        self.keys = {"CLAVE-BUENA-1234": {"status": "inactive", "instances": {}}}
        self.store_id, self.product_id, self.limit = store_id, product_id, limit
        self.offline = False
        self.calls = []

    def meta(self):
        return {"store_id": self.store_id, "product_id": self.product_id, "product_name": "Valorize Bot",
                "variant_name": "Mensual", "customer_email": "albert@example.com", "customer_name": "Albert"}

    def lk(self, key):
        k = self.keys[key]
        return {"status": k["status"], "key": key, "activation_limit": self.limit,
                "activation_usage": len(k["instances"]), "expires_at": None}

    def __call__(self, endpoint, payload):
        import requests as rq
        self.calls.append(endpoint)
        if self.offline:
            raise rq.ConnectionError("sin red")
        key = payload["license_key"]
        if key not in self.keys:
            return {"activated": False, "valid": False, "error": "license_key not found."}
        k = self.keys[key]
        if endpoint == "activate":
            if k["status"] in ("expired", "disabled"):
                return {"activated": False, "error": f"This license key is {k['status']}.", "license_key": self.lk(key)}
            if len(k["instances"]) >= self.limit:
                return {"activated": False, "error": "This license key has reached the activation limit."}
            iid = f"inst-{len(k['instances']) + 1}"
            k["instances"][iid] = payload["instance_name"]
            k["status"] = "active"
            return {"activated": True, "error": None, "license_key": self.lk(key),
                    "instance": {"id": iid, "name": payload["instance_name"]}, "meta": self.meta()}
        if endpoint == "validate":
            name = k["instances"].get(payload.get("instance_id"))
            ok = name is not None and k["status"] == "active"
            return {"valid": ok, "error": None if ok else "invalid", "license_key": self.lk(key),
                    "instance": {"id": payload.get("instance_id"), "name": name} if name else None, "meta": self.meta()}
        if endpoint == "deactivate":
            k["instances"].pop(payload["instance_id"], None)
            if not k["instances"]:
                k["status"] = "inactive"
            return {"deactivated": True, "error": None, "license_key": self.lk(key), "meta": self.meta()}


@pytest.fixture
def lemon(tmp_path, monkeypatch):
    import licensing
    fake = FakeLemon()
    monkeypatch.setattr(licensing, "LICENSE_FILE", tmp_path / "license.json")
    monkeypatch.setattr(licensing, "_post", fake)
    monkeypatch.setattr(licensing, "STORE_ID", 111)
    monkeypatch.setattr(licensing, "PRODUCT_IDS", [222])
    monkeypatch.setattr(licensing, "REQUIRE_LICENSE", True)
    monkeypatch.setattr(licensing, "FREE_PAPER_MODE", True)
    return fake


def test_licencia_activar_y_validar(lemon):
    import licensing
    assert not licensing.status()["licensed"]
    with pytest.raises(licensing.LicenseError, match="no existe"):
        licensing.activate("CLAVE-FALSA-0000")
    st = licensing.activate("CLAVE-BUENA-1234")
    assert st["licensed"] and st["state"] == "active" and st["customer"] == "al••••@example.com"
    assert licensing.validate(force=True)["licensed"]
    # segundo PC: límite de activaciones
    lemon.keys["CLAVE-BUENA-1234"]["instances"]["otro"] = "OTRO-PC · 00000000"
    lemon.keys["CLAVE-BUENA-1234"]["instances"].pop("inst-1")
    assert not licensing.validate(force=True)["licensed"]          # este PC ya no está activado


def test_licencia_de_otra_tienda_no_vale(lemon):
    import licensing
    lemon.store_id = 999
    with pytest.raises(licensing.LicenseError, match="no es de Valorize"):
        licensing.activate("CLAVE-BUENA-1234")
    assert lemon.calls[-1] == "deactivate"                           # libera la activación
    assert not licensing.status()["licensed"]


def test_licencia_caducada_y_periodo_de_gracia(lemon, monkeypatch):
    import licensing
    licensing.activate("CLAVE-BUENA-1234")
    # sin internet: sigue funcionando durante el periodo de gracia
    lemon.offline = True
    st = licensing.validate(force=True)
    assert st["licensed"] and st["state"] == "grace"
    real_now = licensing._now
    monkeypatch.setattr(licensing, "_now", lambda: real_now() + (licensing.GRACE_HOURS + 1) * 3600)
    assert not licensing.status()["licensed"]                       # pasado el plazo, se bloquea
    monkeypatch.setattr(licensing, "_now", real_now)
    # la suscripción caduca
    lemon.offline = False
    lemon.keys["CLAVE-BUENA-1234"]["status"] = "expired"
    st = licensing.validate(force=True)
    assert not st["licensed"] and st["state"] == "expired" and "caducado" in st["message"]


def test_licencia_manipulada_o_copiada_no_vale(lemon):
    import licensing
    licensing.activate("CLAVE-BUENA-1234")
    blob = json.loads(licensing.LICENSE_FILE.read_text())
    blob["data"]["status"] = "active"
    blob["data"]["expires_at"] = "2099-01-01"                       # editado a mano
    licensing.LICENSE_FILE.write_text(json.dumps(blob))
    assert not licensing.status()["licensed"]


def test_licencia_desactivar(lemon):
    import licensing
    licensing.activate("CLAVE-BUENA-1234")
    licensing.deactivate()
    assert not licensing.LICENSE_FILE.exists() and lemon.keys["CLAVE-BUENA-1234"]["instances"] == {}


def test_bot_exige_licencia_para_dinero_real(isolated, lemon):
    import licensing
    e = bot.Engine(replace(BASE, mode="live"), FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))
    with pytest.raises(licensing.LicenseError, match="dinero real"):
        e.start()
    e2 = bot.Engine(BASE, FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))   # simulado: gratis
    licensing.require("paper")
    licensing.activate("CLAVE-BUENA-1234")
    licensing.require("live")                                            # con licencia, sí
    assert e2.snapshot()["license"]["licensed"]


def test_panel_activa_licencia(isolated, lemon):
    import threading
    import urllib.request

    import panel
    e = bot.Engine(BASE, FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))
    server = panel.make_server(e, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"X-Panel": "1", "Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as err:
            return json.loads(err.read())
    try:
        bad = post("/api/license/activate", {"key": "CLAVE-FALSA-0000"})
        assert not bad["ok"] and bad["code"] == "license"
        ok = post("/api/license/activate", {"key": "CLAVE-BUENA-1234"})
        assert ok["ok"] and ok["licensed"]
        st = json.loads(urllib.request.urlopen(base + "/api/status").read())
        assert st["license"]["state"] == "active" and "CLAVE-BUENA" not in json.dumps(st)   # nunca la clave completa
    finally:
        server.shutdown()


# ---------- acceso con contraseña (panel en un servidor) ----------
@pytest.fixture
def with_password(tmp_path, monkeypatch):
    import auth
    import config as C
    monkeypatch.setattr(C, "ENV_FILE", tmp_path / ".env")
    auth._sessions.clear()
    auth._fails.clear()
    auth.set_password("contraseña-segura-123")
    (tmp_path / ".env").write_text((tmp_path / ".env").read_text() + "PANEL_HOSTS=bot.example.com\n")
    return tmp_path


def _panel(engine):
    import threading
    import panel
    server = panel.make_server(engine, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _req(base, path, method="GET", body=None, headers=None):
    import urllib.error
    import urllib.request
    h = {"X-Panel": "1", "Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=h)

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        r = opener.open(req)
        return r.status, r.headers, r.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


def test_contraseña_hash_y_verificacion(with_password):
    import auth
    stored = auth.password_hash()
    assert stored.startswith("scrypt:") and "contraseña-segura-123" not in (with_password / ".env").read_text()
    assert auth.verify("contraseña-segura-123", stored) and not auth.verify("otra", stored)
    with pytest.raises(auth.AuthError, match="al menos"):
        auth.set_password("corta")


def test_panel_exige_login(isolated, with_password):
    import auth
    e = bot.Engine(BASE, FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))
    server, base = _panel(e)
    try:
        code, hdr, _ = _req(base, "/")
        assert code == 302 and hdr["Location"] == "/login"
        assert _req(base, "/api/status")[0] == 401
        assert _req(base, "/api/start", "POST", {})[0] == 401
        assert _req(base, "/login")[0] == 200
        code, _, body = _req(base, "/api/login", "POST", {"password": "mala"})
        assert code == 401 and "incorrecta" in json.loads(body)["error"]
        code, hdr, _ = _req(base, "/api/login", "POST", {"password": "contraseña-segura-123"})
        assert code == 200
        cookie = hdr["Set-Cookie"].split(";")[0]
        assert "HttpOnly" in hdr["Set-Cookie"] and "SameSite=Strict" in hdr["Set-Cookie"]
        code, _, body = _req(base, "/api/status", headers={"Cookie": cookie})
        assert code == 200 and json.loads(body)["remote"] is True
        # en el servidor no se puede apagar el panel desde la web
        assert _req(base, "/api/shutdown", "POST", {}, {"Cookie": cookie})[0] == 400
        # el dominio del servidor está permitido; otros no
        assert _req(base, "/login", headers={"Host": "bot.example.com"})[0] == 200
        assert _req(base, "/login", headers={"Host": "evil.com"})[0] == 403
        # cerrar sesión invalida la cookie
        _req(base, "/api/logout", "POST", {}, {"Cookie": cookie})
        assert _req(base, "/api/status", headers={"Cookie": cookie})[0] == 401
    finally:
        server.shutdown()


def test_bloqueo_por_intentos(with_password):
    import auth
    for _ in range(auth.MAX_FAILS - 1):
        with pytest.raises(auth.AuthError, match="incorrecta"):
            auth.login("mala", "1.2.3.4")
    with pytest.raises(auth.AuthError, match="bloqueado"):
        auth.login("mala", "1.2.3.4")
    with pytest.raises(auth.AuthError, match="Demasiados intentos"):
        auth.login("contraseña-segura-123", "1.2.3.4")        # ni con la buena, durante el bloqueo
    assert auth.login("contraseña-segura-123", "5.6.7.8")      # otra IP no está bloqueada


def test_no_arranca_abierto_a_internet_sin_contraseña(tmp_path, monkeypatch):
    import auth
    import config as C
    monkeypatch.setattr(C, "ENV_FILE", tmp_path / ".env")
    (tmp_path / ".env").write_text("PANEL_HOSTS=bot.example.com\n")
    assert auth.unsafe_config()


# ---------- avisos por Telegram ----------
class _FakeTelegram:
    def __init__(self, updates=None):
        self.updates, self.sent = updates or [], []

    def post(self, url, data=None, timeout=None):
        token, method = url.split("/bot", 1)[1].split("/")
        class R:
            def __init__(s, j): s._j = j
            def json(s): return s._j
        if not token.startswith("123456789:"):
            return R({"ok": False, "error_code": 401, "description": "Unauthorized"})
        if method == "getMe":
            return R({"ok": True, "result": {"username": "mivalorize_bot"}})
        if method == "getUpdates":
            return R({"ok": True, "result": self.updates})
        if method == "sendMessage":
            self.sent.append((data["chat_id"], data["text"]))
            return R({"ok": True, "result": {}})


def test_telegram_conectar_desde_el_panel(tmp_path, monkeypatch):
    import config as C
    import telegram_setup as tg
    monkeypatch.setattr(C, "ENV_FILE", tmp_path / ".env")
    fake = _FakeTelegram()
    monkeypatch.setattr(tg, "requests", type("M", (), {"post": fake.post, "RequestException": Exception}))
    good = "123456789:" + "A" * 35
    try:
        tg.connect("999:" + "x" * 35)
        assert False, "token inválido aceptado"
    except tg.TelegramError as e:
        assert "token" in str(e)
    r = tg.connect(good)                                  # aún no le ha escrito nadie
    assert r["need_message"] and r["link"] == "https://t.me/mivalorize_bot"
    assert not tg.status()["configured"]
    fake.updates = [{"message": {"chat": {"id": 555, "type": "private", "first_name": "Albert"}}}]
    r = tg.connect("")                                    # reutiliza el token pendiente
    assert r["configured"] and r["chat_id"] == "555" and r["name"] == "Albert"
    assert fake.sent and fake.sent[0][0] == "555"
    assert tg.saved() == (good, "555")
    assert "TELEGRAM_PENDING_TOKEN" not in (tmp_path / ".env").read_text()
    assert good not in str(tg.status())                   # nunca se devuelve completo
    tg.test()
    assert len(fake.sent) == 2
    tg.remove()
    assert not tg.status()["configured"]


def test_sesion_sobrevive_a_un_reinicio(with_password):
    import auth
    token = auth.login("contraseña-segura-123", "1.2.3.4")
    assert auth.check(token)
    saved = (with_password / "sessions.json").read_text()
    assert token not in saved                            # solo se guarda la huella
    auth._sessions.clear(); auth._loaded_for = None      # simula reiniciar el servidor
    assert auth.check(token)
    auth.logout(token)
    auth._sessions.clear(); auth._loaded_for = None
    assert not auth.check(token)
    token = auth.login("contraseña-segura-123", "1.2.3.4")
    auth.set_password("otra-contraseña-456")             # cambiar la contraseña las cierra todas
    auth._sessions.clear(); auth._loaded_for = None
    assert not auth.check(token)


# ---------- copias y latido ----------
def test_copias_de_seguridad_diarias_con_rotacion(tmp_path):
    import maintenance as m
    assert m.backup("2026-01-01", tmp_path) is None            # nada que copiar
    (tmp_path / "state.json").write_text("{}")
    (tmp_path / "trades_log.csv").write_text("a,b\n")
    (tmp_path / ".env").write_text("SECRETO=1\n")
    d = m.backup("2026-01-01", tmp_path)
    assert sorted(p.name for p in d.iterdir()) == ["state.json", "trades_log.csv"]   # sin .env
    assert m.backup("2026-01-01", tmp_path) is None            # una al día
    for i in range(2, 20):
        m.backup(f"2026-01-{i:02d}", tmp_path)
    kept = m.list_backups(tmp_path)
    assert len(kept) == m.KEEP_DAYS and kept[0] == "2026-01-19" and "2026-01-01" not in kept


def test_latido_y_salud_del_motor(tmp_path, monkeypatch):
    import config as C
    import maintenance as m
    monkeypatch.setattr(C, "ENV_FILE", tmp_path / ".env")
    calls = []

    class R:
        def __init__(s, code): s.status_code = code
    monkeypatch.setattr(m.requests, "post", lambda url, data=None, timeout=None: calls.append(url) or R(200))
    try:
        m.set_healthcheck("http://inseguro.example")
        assert False
    except m.HealthError:
        pass
    st = m.set_healthcheck("https://hc-ping.com/abc")
    assert st["configured"] and st["host"] == "hc-ping.com" and calls == ["https://hc-ping.com/abc"]

    class E:
        state, last_error = {"halted": False}, "x"
        def __init__(s, running, last=None, started=0): s._r, s.last_cycle_ts, s.started_ts = running, last, started
        def is_running(s): return s._r
    now = 10_000
    assert m.engine_healthy(E(False), now)[0]                  # parado a propósito: sano
    assert m.engine_healthy(E(True, last=now - 60), now)[0]
    assert not m.engine_healthy(E(True, last=now - 2000), now)[0]
    assert m.engine_healthy(E(True, started=now - 30), now)[0]  # recién arrancado
    assert not m.set_healthcheck("")["configured"]


def test_actualizar_desde_git(tmp_path, monkeypatch):
    import subprocess
    import updater
    run = lambda *a, cwd: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)
    origin, clone = tmp_path / "origin", tmp_path / "clone"
    origin.mkdir()
    run("init", "-q", "-b", "main", cwd=origin)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        run("config", k, v, cwd=origin)
    (origin / "a.txt").write_text("1")
    run("add", ".", cwd=origin); run("commit", "-qm", "primera", cwd=origin)
    run("clone", "-q", "--depth", "1", f"file://{origin}", str(clone), cwd=tmp_path)
    monkeypatch.setattr(updater, "ROOT", clone)
    monkeypatch.setattr(updater, "available", lambda: True)
    assert updater.check(max_age=0)["pending"] == 0
    (origin / "a.txt").write_text("2")
    run("commit", "-qam", "Mejora nueva", cwd=origin)
    st = updater.check(max_age=0)
    assert st["pending"] == 1 and st["changes"] == ["Mejora nueva"]
    restarts = []
    monkeypatch.setattr(updater.threading, "Timer", lambda t, f: type("T", (), {"start": lambda s: restarts.append(f)})())
    saved = []
    r = updater.apply(lambda: saved.append(1))
    assert r["updated"] and (clone / "a.txt").read_text() == "2" and saved and restarts
    assert updater.check(max_age=0)["pending"] == 0


def test_comandos_de_telegram(isolated):
    import telegram_bot as tb
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    e = bot.Engine(BASE, ex)
    e.connect()
    run_engine(e, 20)                                     # con una posición abierta
    app = type("App", (), {"engine": e})()
    assert "/parar" in tb.handle(app, "/ayuda")
    st = tb.handle(app, "/estado")
    assert "parado" in st and "BTC/USDT" in st and "Capital" in st
    assert "Entrada" in tb.handle(app, "/posiciones@mi_bot")
    assert "ya estaba parado" in tb.handle(app, "/parar")
    started = []
    e.start = lambda: started.append(1)
    assert tb.handle(app, "/arrancar") == "" and started
    assert "No conozco" in tb.handle(app, "hola")


def test_verificacion_en_dos_pasos(with_password, monkeypatch):
    import base64
    import auth
    rfc = base64.b32encode(b"12345678901234567890").decode()  # vector de prueba del RFC 6238
    assert auth.totp_code(rfc, 59) == "287082"
    assert auth.totp_code(rfc, 1111111109) == "081804"
    clock = [1_800_000_000.0]
    monkeypatch.setattr(auth.time, "time", lambda: clock[0])
    setup = auth.totp_begin()
    assert setup["uri"].startswith("otpauth://totp/") and setup["secret"] in setup["uri"]
    assert not auth.totp_enabled()
    with pytest.raises(auth.AuthError):
        auth.totp_confirm("000000")
    auth.totp_confirm(auth.totp_code(setup["secret"]))
    assert auth.totp_enabled()
    with pytest.raises(auth.NeedCode):
        auth.login("contraseña-segura-123", "9.9.9.9")
    with pytest.raises(auth.AuthError, match="Código incorrecto"):
        auth.login("contraseña-segura-123", "9.9.9.9", "123456")
    clock[0] += 30
    code = auth.totp_code(setup["secret"])
    assert auth.login("contraseña-segura-123", "9.9.9.9", code)
    with pytest.raises(auth.AuthError):                     # el mismo código no sirve dos veces
        auth.login("contraseña-segura-123", "9.9.9.9", code)
    clock[0] += 30
    auth.totp_disable(auth.totp_code(setup["secret"]))
    assert not auth.totp_enabled()
    assert auth.login("contraseña-segura-123", "9.9.9.9")


def test_exportar_historial_para_excel(isolated):
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    e = bot.Engine(BASE, ex)
    e.connect()
    run_engine(e, len(UP_DOWN))
    data = bot.export_trades_csv().decode("utf-8")
    assert data.startswith("﻿Entrada (UTC);Salida (UTC);Par;")
    lines = data.strip().split("\r\n")
    assert len(lines) == 1 + len(bot.read_trades()) >= 2
    row = lines[1].split(";")
    assert row[2] == "BTC/USDT" and "," in row[3] and "." not in row[3]


# ---------- plataforma multiusuario ----------
def _plat(tmp_path, monkeypatch):
    import threading
    import plataforma as pf
    import plataforma_db as pdb
    monkeypatch.setattr(pf, "DATA", tmp_path / "datos")
    fake = FakeExchange({"BTC/USDT": rows_of(UP_DOWN), "ETH/USDT": rows_of([x / 10 for x in UP_DOWN])})
    fake.i = 20
    shared = pf.SharedMarket(fake)
    monkeypatch.setattr(pf, "market", lambda ex_id: shared)
    monkeypatch.setattr(bot.xch, "fetch_closed_candles",
                        lambda e, s, tf, n: exchange.to_df(fake.rows[s][max(0, fake.i - n + 1): fake.i + 1]))
    db = pdb.DB(tmp_path / "datos" / "valorize.db")
    server = pf.make_server(0, db)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, db, f"http://127.0.0.1:{server.server_address[1]}"


def _cookie(headers, name="vp_session"):
    c = headers.get("Set-Cookie") or ""
    return c.split(";")[0] if c.startswith(name + "=") else ""


def test_plataforma_registro_aislamiento_y_admin(tmp_path, monkeypatch):
    srv, db, base = _plat(tmp_path, monkeypatch)
    try:
        # sin sesión: al login
        assert _req(base, "/")[0] == 302
        assert _req(base, "/api/status")[0] == 401
        # registro de admin por invitación (un solo uso)
        inv = db.create_invite("admin")
        code, h, _ = _req(base, "/api/register", "POST", {"invite": inv, "email": "Admin@Ej.com", "password": "clave-segura-1"})
        admin = {"Cookie": _cookie(h)}
        assert code == 200 and admin["Cookie"]
        assert _req(base, "/api/register", "POST", {"invite": inv, "email": "otro@ej.com", "password": "clave-segura-2"})[0] == 400
        # el admin invita a un usuario
        code, _, b = _req(base, "/api/admin/invite", "POST", {"role": "user", "note": "Ana"}, admin)
        link = json.loads(b)["link"]
        token = link.split("invitacion=")[1]
        code, h, _ = _req(base, "/api/register", "POST", {"invite": token, "email": "ana@ej.com", "password": "clave-de-ana-1"})
        ana = {"Cookie": _cookie(h)}
        # cada uno tiene su propio bot (simulado, sin claves del servidor)
        st = json.loads(_req(base, "/api/status", headers=ana)[2])
        assert st["platform"] and st["mode"] == "paper" and not st["admin"] and st["email"] == "ana@ej.com"
        assert _req(base, "/api/start", "POST", {}, ana)[0] == 200
        assert json.loads(_req(base, "/api/status", headers=ana)[2])["running"]
        assert not json.loads(_req(base, "/api/status", headers=admin)[2])["running"]
        assert srv.bots.apps[2].engine.files.state != srv.bots.apps[1].engine.files.state
        assert (tmp_path / "datos" / "usuarios" / "2" / "state.json").exists()
        # página pública y laboratorio: cada usuario los suyos
        path = json.loads(_req(base, "/api/public/enable", "POST", {}, ana)[2])["path"]
        assert _req(base, path)[0] == 200 and json.loads(_req(base, path + "/data")[2])["mode"] == "paper"
        assert json.loads(_req(base, "/api/public", headers=admin)[2])["enabled"] is False
        assert json.loads(_req(base, "/api/lab", headers=ana)[2])["variants"] == []
        lab = srv.bots.lab(db.user(2))
        lab.sync(srv.bots.apps[2].engine.cfg, srv.bots.apps[2].data_ex)
        lab.step()
        assert len(json.loads(_req(base, "/api/lab", headers=ana)[2])["variants"]) >= 5
        assert (tmp_path / "datos" / "usuarios" / "2" / "lab" / "actual").exists()
        assert _req(base, "/api/lab/apply", "POST", {"id": "riesgo2"}, ana)[0] == 200
        assert srv.bots.apps[2].engine.cfg.risk_per_trade == 0.02 and srv.bots.apps[2].engine.is_running()
        assert srv.bots.apps[1].engine.cfg.risk_per_trade == 0.01
        # un usuario normal no puede administrar ni usar modos reales
        assert _req(base, "/api/admin/users", headers=ana)[0] == 403
        assert _req(base, "/admin", headers=ana)[0] == 302
        bad = {"exchange": "binance", "mode": "live", "symbols": ["BTC/USDT"]}
        assert _req(base, "/api/setup/save", "POST", bad, ana)[0] == 400
        assert _req(base, "/api/shutdown", "POST", {}, ana)[0] == 404
        # el admin ve a los usuarios y puede desactivar a Ana (se le para el bot y pierde la sesión)
        users = json.loads(_req(base, "/api/admin/users", headers=admin)[2])["users"]
        assert [u["email"] for u in users] == ["admin@ej.com", "ana@ej.com"] and users[1]["running"]
        assert _req(base, "/api/admin/status", "POST", {"user_id": 2, "status": "disabled"}, admin)[0] == 200
        assert _req(base, "/api/status", headers=ana)[0] == 401
        assert 2 not in srv.bots.apps
        code, _, b = _req(base, "/api/login", "POST", {"email": "ana@ej.com", "password": "clave-de-ana-1"})
        assert code == 400 and "desactivada" in json.loads(b)["error"]
        assert _req(base, "/api/admin/status", "POST", {"user_id": 1, "status": "disabled"}, admin)[0] == 400
        # restablecer contraseña con enlace del admin
        db.set_status(2, "active")
        link = json.loads(_req(base, "/api/admin/reset", "POST", {"user_id": 2}, admin)[2])["link"]
        rtoken = link.split("codigo=")[1]
        assert _req(base, "/api/reset", "POST", {"token": rtoken, "password": "nueva-clave-ana"})[0] == 200
        assert _req(base, "/api/reset", "POST", {"token": rtoken, "password": "otra-clave-ana"})[0] == 400
        assert _req(base, "/api/login", "POST", {"email": "ana@ej.com", "password": "nueva-clave-ana"})[0] == 200
        # contraseña incorrecta: bloqueo tras 5 intentos
        for _ in range(5):
            _req(base, "/api/login", "POST", {"email": "ana@ej.com", "password": "mala-clave-xx"})
        code, _, b = _req(base, "/api/login", "POST", {"email": "ana@ej.com", "password": "nueva-clave-ana"})
        assert code == 400 and "Demasiados" in json.loads(b)["error"]
    finally:
        for a in list(srv.bots.apps.values()):
            a.engine.stop(notify_user=False)
        srv.shutdown()


def test_plataforma_doble_factor_por_usuario(tmp_path, monkeypatch):
    import auth
    srv, db, base = _plat(tmp_path, monkeypatch)
    try:
        inv = db.create_invite("user")
        code, h, _ = _req(base, "/api/register", "POST", {"invite": inv, "email": "b@ej.com", "password": "clave-segura-b"})
        me = {"Cookie": _cookie(h)}
        secret = json.loads(_req(base, "/api/security/totp/begin", "POST", {}, me)[2])["secret"]
        assert _req(base, "/api/security/totp/confirm", "POST", {"code": "000000"}, me)[0] == 400
        clock = [__import__("time").time()]
        assert _req(base, "/api/security/totp/confirm", "POST", {"code": auth.totp_code(secret, clock[0])}, me)[0] == 200
        assert json.loads(_req(base, "/api/security", headers=me)[2])["totp"]
        code, _, b = _req(base, "/api/login", "POST", {"email": "b@ej.com", "password": "clave-segura-b"})
        assert code == 401 and json.loads(b)["need_code"]
        nxt = auth.totp_code(secret, clock[0] + 30)
        monkeypatch.setattr(auth.time, "time", lambda: clock[0] + 30)
        assert _req(base, "/api/login", "POST", {"email": "b@ej.com", "password": "clave-segura-b", "code": nxt})[0] == 200
    finally:
        srv.shutdown()


# ---------- estrategia adaptativa y explicaciones ----------
RANGE = [100 + 3 * np.sin(i / 3) for i in range(120)] + [88, 86] + [100 + 3 * np.sin(i / 3) for i in range(30)]


def test_estrategia_adaptativa_compra_caidas_en_mercado_lateral(isolated):
    from strategy import add_signals, entry_kind, regime
    cfg = replace(BASE, strategy_mode="adaptive", trend_filter=50, adx_min=40, stop_mode="atr",
                  atr_stop_mult=6, atr_trail_mult=0, fast=20, slow=50, ma_type="ema")
    df = add_signals(candles(RANGE), cfg)
    assert set(df["regime"].unique()) <= {"", "alcista", "lateral", "bajista"}
    assert (df["signal"] == 2).any() and entry_kind(2) == "range" and entry_kind(-1) is None
    # en modo tendencia no hay entradas de rango
    assert not (add_signals(candles(RANGE), replace(cfg, strategy_mode="trend"))["signal"] == 2).any()
    bt = run_backtest(candles(RANGE), cfg)
    assert bt["operaciones"] >= 1 and "vuelta a la media" in set(bt["trades"].motivo)
    # el bot hace lo mismo que el backtest
    ex = FakeExchange({"BTC/USDT": rows_of(RANGE)})
    e = bot.Engine(cfg, ex)
    e.connect()
    run_engine(e, len(RANGE))
    log = bot.read_trades()
    assert len(log) == bt["operaciones"]
    assert [t["motivo"] for t in log] == list(bt["trades"].motivo)


def test_el_bot_explica_lo_que_piensa(isolated):
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    e = bot.Engine(BASE, ex)
    e.connect()
    run_engine(e, 3)
    assert "suficientes velas" in e.explain["BTC/USDT"]
    run_engine(e, 20)
    assert "Mantengo la compra" in e.explain["BTC/USDT"] and "cruza por debajo" in e.explain["BTC/USDT"]
    run_engine(e, len(UP_DOWN))
    txt = e.snapshot()["explain"]["BTC/USDT"]
    assert txt.startswith("No compro") and "por debajo de la de 6" in txt
    # con filtros: dice cuál falta
    e2 = bot.Engine(replace(BASE, trend_filter=30), FakeExchange({"BTC/USDT": rows_of(UP_DOWN)}))
    e2.state = bot.new_state(BASE)
    e2.connect()
    run_engine(e2, len(UP_DOWN))
    assert "media de 30 velas" in e2.explain["BTC/USDT"]
    # tras un reinicio explica sin volver a operar
    e3 = bot.Engine(BASE, e.ex)
    e3.connect()
    n = len(bot.read_trades())
    e3.step()
    assert e3.explain["BTC/USDT"] and len(bot.read_trades()) == n


# ---------- laboratorio en la sombra ----------
def test_laboratorio_compara_variantes_y_aplica_la_elegida(isolated, monkeypatch):
    import config as C
    import lab as L
    import panel
    monkeypatch.setattr(C, "SETTINGS_FILE", isolated / "settings.json")
    monkeypatch.setattr(C, "ENV_FILE", isolated / ".env")
    cfg = replace(BASE, risk_per_trade=0.01, stop_loss=0.05)
    ids = [v[0] for v in L.variants(cfg)]
    assert ids[0] == "actual" and {"riesgo2", "rapida", "filtro_btc", "adaptativa"} <= set(ids)
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    raw = ex
    ex = exchange.SharedMarket(raw)
    ex.TICKER_TTL = ex.OHLCV_TTL = 0                 # sin caché: en el test el tiempo avanza vela a vela
    lab = L.Lab(isolated / "lab")
    lab.sync(cfg, ex)
    for raw.i in range(len(UP_DOWN)):
        lab.step()
    assert lab.error is None
    r = lab.ranking()
    rows = {v["id"]: v for v in r["variants"]}
    assert r["ready"] and r["since"] and rows["actual"]["trades"] >= 1
    assert [v["return"] for v in r["variants"]] == sorted((v["return"] for v in r["variants"]), reverse=True)
    assert rows["riesgo2"]["return"] != rows["actual"]["return"]          # arriesgar el doble cambia el resultado
    assert not bot.read_trades()                                          # no toca el historial del bot real
    assert (isolated / "lab" / "actual" / "state.json").exists()
    # sobrevive a un reinicio y se reinicia si cambia la configuración
    lab2 = L.Lab(isolated / "lab")
    lab2.sync(cfg, ex)
    assert lab2.ranking()["since"] == r["since"]
    assert {v["id"]: v for v in lab2.ranking()["variants"]}["actual"]["trades"] == rows["actual"]["trades"]
    lab2.sync(replace(cfg, timeframe="1h"), ex)
    assert all(v["trades"] == 0 for v in lab2.ranking()["variants"])
    # aplicar una variante cambia la estrategia del bot
    app = panel.PanelApp(bot.Engine(cfg, ex), ex)
    app.lab = lab
    with pytest.raises(ValueError):
        app.apply_variant("actual")
    seen = {}
    app.apply_variant("riesgo2", engine_factory=lambda c: seen.setdefault("cfg", c) and bot.Engine(c, ex),
                      data_ex_factory=lambda c: ex)
    assert seen["cfg"].risk_per_trade == 0.02 and C.read_settings()["risk_per_trade"] == 0.02


# ---------- página pública de resultados ----------
def test_pagina_publica_solo_con_enlace_y_sin_importes(isolated, monkeypatch):
    import config as C
    import telegram_bot as tb
    monkeypatch.setattr(C, "ENV_FILE", isolated / ".env")
    ex = FakeExchange({"BTC/USDT": rows_of(UP_DOWN)})
    e = bot.Engine(replace(BASE, paper_balance=4321.0), ex)
    e.state = bot.new_state(e.cfg)
    e.connect()
    run_engine(e, len(UP_DOWN))
    e.state["equity_history"] = [[1_700_000_000 + i * 3600, 4321.0 * (1 + i / 1000)] for i in range(30)]
    assert "No compro" in tb.handle(type("A", (), {"engine": e})(), "/porque")
    srv, base = _panel(e)
    try:
        assert _req(base, "/p/" + "x" * 24)[0] == 404                      # desactivada por defecto
        assert json.loads(_req(base, "/api/public")[2]) == {"enabled": False, "path": ""}
        path = json.loads(_req(base, "/api/public/enable", "POST", {})[2])["path"]
        assert path.startswith("/p/") and len(path) > 20
        code, _, html = _req(base, path)
        assert code == 200 and b"Resultados" in html
        code, _, raw = _req(base, path + "/data")
        d = json.loads(raw)
        assert code == 200 and d["mode"] == "paper" and d["trades_count"] == len(bot.read_trades()) >= 1
        assert d["curve"][0][1] == 100 and abs(d["return"] - 0.029) < 1e-6
        assert "4321" not in raw.decode() and "qty" not in raw.decode() and "cantidad" not in raw.decode()
        assert _req(base, path[:-1] + ("a" if path[-1] != "a" else "b"))[0] == 404
        assert _req(base, path + "/otra")[0] == 404
        _req(base, "/api/public/disable", "POST", {})
        assert _req(base, path)[0] == 404 and _req(base, path + "/data")[0] == 404
    finally:
        srv.shutdown()
