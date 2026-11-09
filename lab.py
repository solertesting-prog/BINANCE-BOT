"""Laboratorio en la sombra: variantes de la estrategia compitiendo con dinero ficticio.

Mientras tu bot opera con su configuración, el laboratorio ejecuta en paralelo varias variantes
(más riesgo, medias más rápidas, sin filtro de fuerza, con filtro de BTC, adaptativa...) con los
mismos precios en vivo y 1.000 de saldo ficticio cada una. El panel muestra la clasificación.

- "Tu estrategia actual" también corre en el laboratorio, para comparar en igualdad de condiciones.
- No envía órdenes ni avisos: son simulaciones. Comparten los datos de mercado (con caché).
- Si cambias de exchange, monedas, velas o estrategia, la clasificación empieza de cero.
- Pocos días no significan nada: una variante necesita semanas y decenas de operaciones.
"""
import json
import logging
import shutil
import threading
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import bot
import exchange as xch

START = 1000.0
SIG_FIELDS = ("exchange", "symbols", "timeframe", "fast", "slow", "ma_type", "trend_filter", "adx_min",
              "market_filter", "market_filter_ma", "strategy_mode", "stop_mode", "atr_stop_mult",
              "atr_trail_mult", "stop_loss", "trailing_stop", "take_profit", "risk_per_trade",
              "position_pct", "max_open_positions", "max_drawdown", "fee")
quiet = logging.getLogger("valorize.lab")
quiet.addHandler(logging.NullHandler())
quiet.propagate = False
log = logging.getLogger("bot")


def variants(cfg) -> list:
    """(id, nombre, descripción, cambios) de cada variante. Las que no cambian nada se omiten."""
    fast = (10, 30) if (cfg.fast, cfg.slow) != (10, 30) else (20, 50)
    out = [
        ("actual", "Tu estrategia actual", "Tal como la tienes configurada", {}),
        ("riesgo2", "Doble de riesgo", "Arriesga el doble en cada operación: gana y pierde más",
         {"risk_per_trade": min(0.05, round(cfg.risk_per_trade * 2, 4))}),
        ("rapida", f"Medias {fast[0]}/{fast[1]}", "Reacciona antes o después a los cambios de tendencia",
         {"fast": fast[0], "slow": fast[1]}),
        ("sin_fuerza", "Sin filtro de fuerza" if cfg.adx_min else "Con filtro de fuerza",
         "Opera más a menudo, también en mercados sin tendencia clara" if cfg.adx_min
         else "Solo compra si el mercado tiene fuerza (ADX ≥ 20)", {"adx_min": 0 if cfg.adx_min else 20}),
        ("filtro_btc", "Sin filtro de BTC" if cfg.market_filter else "Con filtro de BTC",
         "No compra otras monedas mientras BTC esté en tendencia bajista" if not cfg.market_filter
         else "Compra aunque BTC esté en tendencia bajista", {"market_filter": "" if cfg.market_filter else "BTC"}),
        ("adaptativa", "Solo tendencia" if cfg.strategy_mode == "adaptive" else "Adaptativa al mercado",
         "Solo sigue tendencias" if cfg.strategy_mode == "adaptive"
         else "En mercado lateral compra caídas exageradas; en bajista se queda fuera (experimental)",
         {"strategy_mode": "trend" if cfg.strategy_mode == "adaptive" else "adaptive"}),
    ]
    return [v for v in out if v[0] == "actual" or any(getattr(cfg, k) != val for k, val in v[3].items())]


def signature(cfg) -> str:
    return json.dumps([list(getattr(cfg, f)) if f == "symbols" else getattr(cfg, f) for f in SIG_FIELDS])


class Lab:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.lock = threading.Lock()
        self.engines, self.info, self.sig, self.src, self.error = {}, {}, None, None, None

    # --- preparación ---
    def _meta(self) -> dict:
        try:
            return json.loads((self.folder / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def sync(self, cfg, ex):
        """Crea (o recrea) las variantes si es la primera vez o ha cambiado la configuración."""
        sig = signature(cfg)
        with self.lock:
            if sig == self.sig and ex is self.src and self.engines:
                return
            if self._meta().get("sig") != sig:                 # otra configuración: empieza de cero
                shutil.rmtree(self.folder, ignore_errors=True)
            self.folder.mkdir(parents=True, exist_ok=True)
            if not (self.folder / "meta.json").exists():
                (self.folder / "meta.json").write_text(json.dumps(
                    {"sig": sig, "since": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
            shared = ex if isinstance(ex, xch.SharedMarket) else xch.SharedMarket(ex)
            self.engines, self.info = {}, {}
            for vid, name, desc, changes in variants(cfg):
                vcfg = replace(cfg, **changes, mode="paper", testnet=False, paper_balance=START,
                               telegram_token="", telegram_chat_id="", api_key="", api_secret="",
                               api_password="", api_uid="")
                d = self.folder / vid
                d.mkdir(exist_ok=True)
                self.engines[vid] = bot.Engine(vcfg, shared, bot.Files(d, quiet))
                self.info[vid] = {"name": name, "desc": desc, "changes": changes}
            self.sig, self.src = sig, ex

    def reset(self):
        with self.lock:
            shutil.rmtree(self.folder, ignore_errors=True)
            self.engines, self.sig = {}, None

    # --- ejecución ---
    def step(self):
        with self.lock:
            self.error = None
            for vid, e in self.engines.items():
                if e.state.get("halted"):
                    continue
                try:
                    if e.broker is None:
                        e.connect()
                    e.step()
                    bot.save_state(e.state, e.files.state)
                except (Exception, SystemExit) as ex:           # una variante nunca afecta al bot real
                    self.error = f"{type(ex).__name__}: {ex}"

    # --- resultados ---
    def changes(self, vid) -> dict:
        if vid not in self.info or vid == "actual":
            raise ValueError("Variante desconocida.")
        return dict(self.info[vid]["changes"])

    def ranking(self) -> dict:
        rows = []
        with self.lock:
            for vid, e in self.engines.items():
                s = e.state
                eq = e.last_equity if e.last_equity is not None else (
                    s["equity_history"][-1][1] if s["equity_history"] else START)
                curve = [h[1] for h in s["equity_history"]] + [eq]
                peak, dd = curve[0], 0.0
                for v in curve:
                    peak = max(peak, v)
                    dd = min(dd, v / peak - 1)
                trades = bot.read_trades(e.files.trades)
                wins = sum(1 for t in trades if float(t["pnl_pct"] or 0) > 0)
                rows.append({"id": vid, **{k: self.info[vid][k] for k in ("name", "desc")},
                             "return": eq / START - 1, "max_drawdown": dd, "trades": len(trades),
                             "win_rate": wins / len(trades) if trades else None,
                             "positions": len(s["positions"]), "halted": bool(s.get("halted")),
                             "ready": e.last_cycle is not None or bool(s["equity_history"])})
        rows.sort(key=lambda r: -r["return"])
        return {"since": self._meta().get("since"), "variants": rows, "start": START, "error": self.error,
                "ready": bool(rows) and all(r["ready"] for r in rows)}


def watcher(app, stop_event, folder: Path = None, every: int = 300):
    """Hilo del panel: ejecuta el laboratorio cada 5 minutos."""
    app.lab = Lab(folder or Path("lab"))
    wait = 20
    while not stop_event.wait(wait):
        wait = every
        try:
            app.lab.sync(app.engine.cfg, app.data_ex)
            app.lab.step()
        except (Exception, SystemExit) as e:
            log.warning(f"Laboratorio: {e}")
