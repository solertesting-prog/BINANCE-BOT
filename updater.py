"""Actualizar el bot desde el panel (en el servidor): descarga la última versión de GitHub,
instala las dependencias nuevas y se reinicia solo (systemd lo vuelve a arrancar).

Solo está disponible si el bot se instaló con git (instalación de servidor). Tus datos
(.env, ajustes, estado, operaciones) no se tocan. Los cambios del sistema (HTTPS, servicio)
siguen necesitando el instalador: bash /opt/valorize-bot/deploy/instalar-servidor.sh
"""
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

log = logging.getLogger("bot")
ROOT = Path(__file__).resolve().parent
BRANCH = "main"


class UpdateError(Exception):
    pass


def _git(*args, timeout=60) -> str:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise UpdateError(f"No se pudo ejecutar git: {e}")
    if r.returncode != 0:
        raise UpdateError((r.stderr or r.stdout).strip()[:400] or "git falló")
    return r.stdout.strip()


def available() -> bool:
    """Solo en instalaciones con git y un gestor que reinicie el proceso (servidor Linux)."""
    return (ROOT / ".git").exists() and sys.platform.startswith("linux") and bool(os.getenv("INVOCATION_ID"))


_cache = {"t": 0, "data": None}


def check(max_age: int = 600) -> dict:
    """Novedades en GitHub (consulta como mucho cada 10 minutos)."""
    import time
    if not available():
        return {"available": False}
    if _cache["data"] and time.time() - _cache["t"] < max_age:
        return _cache["data"]
    _git("fetch", "--quiet", "origin", BRANCH, timeout=90)
    current = _git("rev-parse", "--short", "HEAD")
    new = _git("log", "--format=%s", f"HEAD..origin/{BRANCH}")
    changes = [line for line in new.splitlines() if line.strip()]
    _cache.update(t=time.time(), data={"available": True, "current": current, "pending": len(changes),
                                       "changes": changes[:15]})
    return _cache["data"]


def apply(save_state=None) -> dict:
    if not available():
        raise UpdateError("La actualización desde el panel solo funciona en la instalación de servidor.")
    before = _git("rev-parse", "--short", "HEAD")
    _git("pull", "--ff-only", "--quiet", "origin", BRANCH, timeout=120)
    after = _git("rev-parse", "--short", "HEAD")
    if after == before:
        return {"updated": False, "current": after}
    pip = ROOT / "venv" / "bin" / "pip"
    if pip.exists():
        r = subprocess.run([str(pip), "install", "-q", "--no-cache-dir", "-r", str(ROOT / "requirements.txt")],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            log.warning(f"pip: {r.stderr.strip()[:400]}")
    log.info(f"Actualizado de {before} a {after}. Reiniciando…")
    if save_state:
        save_state()

    def restart():
        os._exit(3)                         # systemd (Restart=always) lo vuelve a arrancar
    threading.Timer(1.5, restart).start()
    return {"updated": True, "from": before, "current": after}
