"""Genera el texto de "cloud-init" para crear el servidor de Valorize Bot.

Pide la contraseña del panel en ESTE ordenador y solo guarda su hash: la contraseña
no se escribe en ningún sitio ni viaja al proveedor del servidor.

Uso (en Windows, mejor con doble clic en preparar-servidor.bat):
    python deploy/generar_cloud_init.py
"""
import getpass
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import auth  # noqa: E402

REPO = "https://github.com/solertesting-prog/BINANCE-BOT.git"
OUT = ROOT / "cloud-init-servidor.txt"

TEMPLATE = """#cloud-config
# Valorize Bot: instalación automática del servidor (ver SERVIDOR.md)
runcmd:
  - [bash, -c, "git clone --depth 1 {repo} /opt/valorize-bot && PANEL_PASSWORD_HASH='{hash}' bash /opt/valorize-bot/deploy/instalar-servidor.sh > /var/log/valorize-install.log 2>&1"]
"""


def main():
    print("Contraseña para entrar al panel del servidor.")
    print(f"Usa una contraseña LARGA y única (mínimo {auth.MIN_LENGTH} caracteres): protege tu bot en internet.\n")
    pw = getpass.getpass("Contraseña: ")
    if len(pw) < auth.MIN_LENGTH:
        raise SystemExit(f"Demasiado corta: mínimo {auth.MIN_LENGTH} caracteres.")
    if pw != getpass.getpass("Repítela: "):
        raise SystemExit("Las contraseñas no coinciden.")
    text = TEMPLATE.format(repo=REPO, hash=auth.make_hash(pw))
    OUT.write_text(text, encoding="utf-8")
    copied = False
    if sys.platform.startswith("win"):
        try:
            subprocess.run("clip", input=text.encode("utf-16"), check=True, shell=True)
            copied = True
        except Exception:
            pass
    print("\nListo. El texto para pegar al crear el servidor está en:")
    print(f"  {OUT}")
    if copied:
        print("y ya está COPIADO en el portapapeles: solo tienes que pegarlo (Ctrl + V).")
    print("\nGuarda bien tu contraseña: la necesitarás para entrar al panel.")


if __name__ == "__main__":
    main()
