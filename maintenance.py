"""Mantenimiento automático: copias de seguridad diarias y "latido" para saber si el bot sigue vivo.

- Copia de seguridad: una vez al día copia el estado, el historial de operaciones y los ajustes a
  backups/AAAA-MM-DD/ y conserva las últimas KEEP_DAYS. (Las claves de .env no se copian.)
- Latido (healthchecks.io u otro servicio similar): cada 5 minutos avisa a una dirección de que
  el bot funciona. Si el servidor se apaga, se cuelga o el bot lleva un rato con errores, deja de
  avisar y ese servicio te manda un email/Telegram. Se configura en el panel (🔔 Avisos).
"""
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import dotenv_values, set_key

import config as C

log = logging.getLogger("bot")
BACKUP_DIR = Path("backups")
BACKUP_FILES = ("state.json", "trades_log.csv", "settings.json")
KEEP_DAYS = 14
PING_EVERY = 300                 # segundos entre latidos
STALE_AFTER = 900                # sin un ciclo correcto en 15 min = algo va mal


# ---------- copias de seguridad ----------
def backup(today: str = None, root: Path = None) -> Path | None:
    """Copia los archivos importantes si hoy aún no se ha hecho. Devuelve la carpeta creada."""
    root = root or Path(".")
    today = today or datetime.now(timezone.utc).date().isoformat()
    dest = root / BACKUP_DIR / today
    if dest.exists():
        return None
    files = [root / f for f in BACKUP_FILES if (root / f).exists()]
    if not files:
        return None
    tmp = dest.with_name(today + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for f in files:
        shutil.copy2(f, tmp / f.name)
    tmp.rename(dest)
    days = sorted(p for p in (root / BACKUP_DIR).iterdir() if p.is_dir() and not p.name.endswith(".tmp"))
    for old in days[:-KEEP_DAYS]:
        shutil.rmtree(old, ignore_errors=True)
    log.info(f"Copia de seguridad guardada en {dest}")
    return dest


def list_backups(root: Path = None) -> list:
    d = (root or Path(".")) / BACKUP_DIR
    return sorted((p.name for p in d.iterdir() if p.is_dir() and not p.name.endswith(".tmp")),
                  reverse=True) if d.exists() else []


# ---------- latido ----------
class HealthError(Exception):
    pass


def healthcheck_url() -> str:
    vals = dotenv_values(C.ENV_FILE) if C.ENV_FILE.exists() else {}
    return (vals.get("HEALTHCHECK_URL") or "").strip()


def _valid(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == "https" and bool(u.netloc) and " " not in url


def ping(url: str, fail: bool = False, msg: str = "") -> bool:
    if not url:
        return False
    try:
        r = requests.post(url.rstrip("/") + ("/fail" if fail else ""), data=msg.encode()[:9000], timeout=10)
        return r.status_code < 400
    except requests.RequestException:
        return False


def set_healthcheck(url: str) -> dict:
    url = (url or "").strip()
    if url and not _valid(url):
        raise HealthError("La dirección debe empezar por https:// (cópiala tal cual de healthchecks.io).")
    if url and not ping(url, msg="Valorize Bot: prueba de conexión"):
        raise HealthError("No se pudo avisar a esa dirección. Revisa que esté completa.")
    if not C.ENV_FILE.exists():
        C.ENV_FILE.touch()
    set_key(str(C.ENV_FILE), "HEALTHCHECK_URL", url, quote_mode="never")
    return health_status()


def health_status() -> dict:
    url = healthcheck_url()
    host = urlparse(url).netloc if url else ""
    return {"configured": bool(url), "host": host, "backups": list_backups()[:KEEP_DAYS]}


def engine_healthy(engine, now: float = None) -> tuple:
    """(sano, motivo). Parado a propósito cuenta como sano: el servidor y el panel funcionan."""
    now = now or time.time()
    if engine.state.get("halted"):
        return False, "Interruptor de seguridad activado"
    if not engine.is_running():
        return True, "bot parado (panel en marcha)"
    last = getattr(engine, "last_cycle_ts", None)
    started = getattr(engine, "started_ts", None) or now
    if last is None and now - started > STALE_AFTER or last is not None and now - last > STALE_AFTER:
        return False, f"Sin ciclos correctos desde hace más de {STALE_AFTER // 60} min. Último error: {engine.last_error}"
    return True, "en marcha"


def watcher(app, stop_event):
    """Hilo del panel: copia diaria y latido cada 5 minutos."""
    while True:
        try:
            backup()
        except Exception as e:
            log.warning(f"No se pudo hacer la copia de seguridad: {e}")
        url = healthcheck_url()
        if url:
            ok, why = engine_healthy(app.engine)
            ping(url, fail=not ok, msg=f"Valorize Bot: {why}")
        if stop_event.wait(PING_EVERY):
            return
