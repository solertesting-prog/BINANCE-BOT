"""Optimizador con validación walk-forward.

El peligro de optimizar es encontrar parámetros que funcionan genial en el pasado por pura
casualidad (sobreajuste). Para detectarlo, este script imita lo que harías en la realidad:

  1. Toma la primera mitad del histórico, busca los mejores parámetros ahí ("entrenamiento").
  2. Los aplica SIN TOCARLOS al tramo siguiente, que no ha visto ("prueba").
  3. Avanza, añade ese tramo al entrenamiento y repite.

Lo que importa es el resultado en los tramos de prueba. Si es malo aunque el entrenamiento
sea espectacular, los parámetros "óptimos" no sirven.

Uso:
    python optimize.py                        # último año en velas de 1 h, rejilla normal
    python optimize.py --days 730 --folds 4
    python optimize.py --quick                # rejilla pequeña, para probar rápido
    python optimize.py --csv datos.csv
"""
import argparse
import itertools
import math
import os
from dataclasses import replace
from multiprocessing import Pool

import pandas as pd

from backtest import add_common_args, load_data, run_backtest
from config import CONFIG
from strategy import describe

# "stops" agrupa variantes de salida para no probar combinaciones sin sentido
STOPS = [
    {"stop_mode": "atr", "atr_stop_mult": 2.0, "atr_trail_mult": 3.0, "take_profit": 0},
    {"stop_mode": "atr", "atr_stop_mult": 2.5, "atr_trail_mult": 3.0, "take_profit": 0},
    {"stop_mode": "atr", "atr_stop_mult": 3.0, "atr_trail_mult": 4.0, "take_profit": 0},
    {"stop_mode": "atr", "atr_stop_mult": 2.5, "atr_trail_mult": 0, "take_profit": 0},
    {"stop_mode": "pct", "stop_loss": 0.03, "trailing_stop": 0, "take_profit": 0.08},
    {"stop_mode": "pct", "stop_loss": 0.05, "trailing_stop": 0.05, "take_profit": 0},
]
GRID = {
    "fast": [10, 20, 30],
    "slow": [50, 100],
    "ma_type": ["sma", "ema"],
    "trend_filter": [0, 200],
    "adx_min": [0, 20],
    "stops": STOPS,
}
QUICK_GRID = {
    "fast": [10, 20],
    "slow": [50],
    "ma_type": ["ema"],
    "trend_filter": [0, 200],
    "adx_min": [0, 20],
    "stops": STOPS[:2] + STOPS[4:5],
}
MIN_TRADES = 5          # con menos operaciones, el resultado es ruido estadístico

_DF = None


def _init(df):
    global _DF
    _DF = df


def _evaluate(job):
    params, start, end = job
    cfg = replace(CONFIG, **params)
    try:
        r = run_backtest(_DF, cfg, start=start, end=end)
    except ValueError:
        return params, None
    keys = ("rentabilidad", "buy_and_hold", "max_drawdown", "operaciones", "acierto", "profit_factor", "ret_dd")
    return params, {k: r[k] for k in keys}


def score(m) -> float:
    """Rentabilidad / drawdown, exigiendo un mínimo de operaciones."""
    if m is None or m["operaciones"] < MIN_TRADES:
        return -math.inf
    return m["ret_dd"]


def combos(grid):
    keys = list(grid)
    for values in itertools.product(*grid.values()):
        p = dict(zip(keys, values))
        p.update(p.pop("stops", {}))
        if p["fast"] < p["slow"]:
            yield p


def evaluate_all(pool, params_list, start=None, end=None):
    return pool.map(_evaluate, [(p, start, end) for p in params_list], chunksize=8)


def main():
    p = argparse.ArgumentParser(description="Optimización walk-forward")
    add_common_args(p)
    p.add_argument("--folds", type=int, default=3, help="nº de tramos de prueba")
    p.add_argument("--quick", action="store_true", help="rejilla reducida")
    p.add_argument("--out", default="optim_resultados.csv", help="CSV con todas las combinaciones")
    a = p.parse_args()

    a.symbol = a.symbol.split(",")[0].strip().upper()     # optimiza una moneda cada vez
    df = load_data(a.symbol, a.timeframe, a.days, a.csv)
    _init(df)                     # también en este proceso, no solo en los trabajadores
    grid = QUICK_GRID if a.quick else GRID
    params_list = list(combos(grid))
    idx = df.index
    half = len(idx) // 2
    bounds = [half + round(i * (len(idx) - half) / a.folds) for i in range(a.folds + 1)]

    print(f"\n{len(params_list)} combinaciones × {a.folds} tramos | {len(df)} velas "
          f"{a.symbol} {a.timeframe} ({idx[0]:%Y-%m-%d} → {idx[-1]:%Y-%m-%d})")

    oos_strategy, oos_current, oos_bh, chosen = 1.0, 1.0, 1.0, []
    with Pool(os.cpu_count(), initializer=_init, initargs=(df,)) as pool:
        for f in range(a.folds):
            train_end = idx[bounds[f] - 1]
            test_start, test_end = idx[bounds[f]], idx[bounds[f + 1] - 1]

            train = evaluate_all(pool, params_list, end=train_end)
            best_params, best_m = max(train, key=lambda x: score(x[1]))
            if score(best_m) == -math.inf:
                print(f"\nTramo {f + 1}: ninguna combinación con ≥{MIN_TRADES} operaciones en entrenamiento")
                continue
            chosen.append(best_params)
            _, test_m = _evaluate((best_params, test_start, test_end))
            _, cur_m = _evaluate(({}, test_start, test_end))   # la config actual de config.py

            oos_strategy *= 1 + test_m["rentabilidad"]
            oos_current *= 1 + cur_m["rentabilidad"]
            oos_bh *= 1 + test_m["buy_and_hold"]
            print(f"\n--- Tramo {f + 1}: entrena hasta {train_end:%Y-%m-%d}, prueba "
                  f"{test_start:%Y-%m-%d} → {test_end:%Y-%m-%d}")
            print(f"  Elegido:       {describe(replace(CONFIG, **best_params))}")
            print(f"  Entrenamiento: {best_m['rentabilidad']:+.1%} (DD {best_m['max_drawdown']:.1%}, "
                  f"{best_m['operaciones']} ops)")
            print(f"  PRUEBA:        {test_m['rentabilidad']:+.1%} (DD {test_m['max_drawdown']:.1%}, "
                  f"{test_m['operaciones']} ops) | config actual {cur_m['rentabilidad']:+.1%} "
                  f"| comprar y mantener {test_m['buy_and_hold']:+.1%}")

        print("\n=== Resultado fuera de muestra (lo que habría pasado de verdad) ===")
        print(f"  Optimizando en cada tramo: {oos_strategy - 1:+.1%}")
        print(f"  Config actual (config.py): {oos_current - 1:+.1%}")
        print(f"  Comprar y mantener:        {oos_bh - 1:+.1%}")
        if len(chosen) > 1:
            stable = {k: len({c[k] for c in chosen}) == 1 for k in chosen[0]}
            fixed = [k for k, v in stable.items() if v]
            print(f"  Parámetros que se repiten en todos los tramos: {', '.join(fixed) or 'ninguno'}")
            if len(fixed) < len(chosen[0]) / 2:
                print("  ⚠️  Los parámetros elegidos cambian mucho entre tramos: señal de sobreajuste.")

        # Ranking final con todo el histórico (para orientarte, no para fiarte ciegamente)
        full = evaluate_all(pool, params_list)

    rows = [{"configuracion": describe(replace(CONFIG, **p)), **p, **m, "score": score(m)}
            for p, m in full if m]
    res = pd.DataFrame(rows).sort_values("score", ascending=False)
    res.to_csv(a.out, index=False)
    print(f"\nTop 5 en todo el histórico (guardado completo en {a.out}):")
    for x in res.head(5).itertuples():
        print(f"  {x.rentabilidad:+7.1%}  DD {x.max_drawdown:6.1%}  {x.operaciones:3d} ops  "
              f"acierto {x.acierto:4.0%}  | {x.configuracion}")
    print("\nConsejo: solo cambia config.py si la PRUEBA fuera de muestra es convincente, "
          "no por el top del histórico completo.")


if __name__ == "__main__":
    main()
