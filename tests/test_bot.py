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
