"""Plataforma multiusuario · base de datos (SQLite): usuarios, invitaciones, sesiones y enlaces
para restablecer la contraseña.

- Registro solo por invitación (beta privada): el administrador crea un enlace de un solo uso.
- Contraseñas con scrypt (como el panel). Sesiones y enlaces: solo se guarda su huella (SHA-256).
- Bloqueo tras 5 intentos fallidos (por IP y por cuenta) durante 15 minutos.
"""
import hashlib
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

import auth

SESSION_HOURS = 24 * 7
INVITE_DAYS = 7
RESET_HOURS = 24
MAX_FAILS = 5
LOCK_MINUTES = 15
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  pw_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',          -- 'user' o 'admin'
  status TEXT NOT NULL DEFAULT 'active',      -- 'active' o 'disabled'
  totp_secret TEXT NOT NULL DEFAULT '',
  telegram_token TEXT NOT NULL DEFAULT '',
  telegram_chat TEXT NOT NULL DEFAULT '',
  created REAL NOT NULL,
  last_login REAL
);
CREATE TABLE IF NOT EXISTS invites (
  token_hash TEXT PRIMARY KEY,
  role TEXT NOT NULL DEFAULT 'user',
  note TEXT NOT NULL DEFAULT '',
  created REAL NOT NULL,
  expires REAL NOT NULL,
  used_by INTEGER
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS resets (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  expires REAL NOT NULL
);
"""


class DBError(Exception):
    pass


class NeedCode(DBError):
    pass


def _h(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()


class DB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        try:                                   # columnas añadidas en versiones posteriores
            self.conn.execute("ALTER TABLE users ADD COLUMN public_token TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        self.lock = threading.Lock()
        self._fails = {}                       # clave (ip o email) -> [fallos, bloqueado hasta]
        self._totp_last = {}
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def q(self, sql, args=(), one=False):
        with self.lock:
            cur = self.conn.execute(sql, args)
            rows = cur.fetchall()
        return (dict(rows[0]) if rows else None) if one else [dict(r) for r in rows]

    def x(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).lastrowid

    # ---------- usuarios ----------
    def user(self, uid):
        return self.q("SELECT * FROM users WHERE id=?", (uid,), one=True)

    def by_email(self, email):
        return self.q("SELECT * FROM users WHERE email=?", ((email or "").strip().lower(),), one=True)

    def by_public_token(self, token):
        if not token or len(token) < 16:
            return None
        return self.q("SELECT * FROM users WHERE public_token=? AND status='active'", (token,), one=True)

    def users(self):
        return self.q("SELECT id,email,role,status,created,last_login,totp_secret!='' AS totp,"
                      "telegram_chat!='' AS telegram FROM users ORDER BY id")

    def count(self):
        return self.q("SELECT COUNT(*) AS n FROM users", one=True)["n"]

    def set_status(self, uid, status):
        if status not in ("active", "disabled"):
            raise DBError("Estado no válido.")
        self.x("UPDATE users SET status=? WHERE id=?", (status, uid))
        if status == "disabled":
            self.x("DELETE FROM sessions WHERE user_id=?", (uid,))

    def update(self, uid, **fields):
        allowed = {"totp_secret", "telegram_token", "telegram_chat", "public_token"}
        for k, v in fields.items():
            if k not in allowed:
                raise DBError(f"Campo no permitido: {k}")
            self.x(f"UPDATE users SET {k}=? WHERE id=?", (v, uid))

    # ---------- invitaciones y registro ----------
    def create_invite(self, role="user", note="") -> str:
        if role not in ("user", "admin"):
            raise DBError("Rol no válido.")
        token = secrets.token_urlsafe(24)
        now = time.time()
        self.x("INSERT INTO invites(token_hash,role,note,created,expires) VALUES(?,?,?,?,?)",
               (_h(token), role, note[:100], now, now + INVITE_DAYS * 86400))
        return token

    def invite(self, token):
        inv = self.q("SELECT * FROM invites WHERE token_hash=?", (_h(token),), one=True)
        if not inv or inv["used_by"] or inv["expires"] < time.time():
            return None
        return inv

    def invites(self):
        return self.q("SELECT i.role,i.note,i.created,i.expires,i.used_by,u.email FROM invites i "
                      "LEFT JOIN users u ON u.id=i.used_by ORDER BY i.created DESC LIMIT 50")

    def register(self, token, email, password) -> int:
        inv = self.invite(token)
        if not inv:
            raise DBError("La invitación no es válida o ha caducado. Pide otra al administrador.")
        email = (email or "").strip().lower()
        if not EMAIL_RE.match(email) or len(email) > 200:
            raise DBError("Escribe un email válido.")
        if len(password or "") < auth.MIN_LENGTH:
            raise DBError(f"La contraseña debe tener al menos {auth.MIN_LENGTH} caracteres.")
        if self.by_email(email):
            raise DBError("Ya existe una cuenta con ese email.")
        with self.lock:                        # marca la invitación y crea el usuario a la vez
            cur = self.conn.execute("UPDATE invites SET used_by=-1 WHERE token_hash=? AND used_by IS NULL",
                                    (_h(token),))
            if cur.rowcount != 1:
                raise DBError("La invitación ya se ha usado.")
            uid = self.conn.execute("INSERT INTO users(email,pw_hash,role,created) VALUES(?,?,?,?)",
                                    (email, auth.make_hash(password), inv["role"], time.time())).lastrowid
            self.conn.execute("UPDATE invites SET used_by=? WHERE token_hash=?", (uid, _h(token)))
        return uid

    # ---------- acceso ----------
    def _check_lock(self, *keys):
        now = time.time()
        for k in keys:
            fails, until = self._fails.get(k, [0, 0])
            if until > now:
                raise DBError(f"Demasiados intentos. Espera {int((until - now) // 60) + 1} min.")

    def _fail(self, *keys):
        now = time.time()
        for k in keys:
            fails = self._fails.get(k, [0, 0])[0] + 1
            self._fails[k] = [0, now + LOCK_MINUTES * 60] if fails >= MAX_FAILS else [fails, 0]

    def login(self, email, password, ip, code="") -> str:
        email = (email or "").strip().lower()
        keys = ("ip:" + ip, "email:" + email)
        self._check_lock(*keys)
        u = self.by_email(email)
        ok = bool(u) and auth.verify(password or "", u["pw_hash"])
        if not u:
            auth.verify(password or "", auth.make_hash("x" * 12))   # mismo tiempo exista o no
        if ok and u["totp_secret"]:
            if not (code or "").strip():
                raise NeedCode("Escribe el código de 6 cifras de tu app de autenticación.")
            ok = auth.totp_verify(u["totp_secret"], code)
        if not ok:
            self._fail(*keys)
            raise DBError("Email, contraseña o código incorrectos.")
        if u["status"] != "active":
            raise DBError("Tu cuenta está desactivada. Contacta con el administrador.")
        for k in keys:
            self._fails.pop(k, None)
        token = secrets.token_urlsafe(32)
        now = time.time()
        self.x("INSERT INTO sessions(token_hash,user_id,expires) VALUES(?,?,?)",
               (_h(token), u["id"], now + SESSION_HOURS * 3600))
        self.x("UPDATE users SET last_login=? WHERE id=?", (now, u["id"]))
        self.x("DELETE FROM sessions WHERE expires<?", (now,))
        return token

    def session_user(self, token):
        if not token:
            return None
        u = self.q("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
                   "WHERE s.token_hash=? AND s.expires>?", (_h(token), time.time()), one=True)
        return u if u and u["status"] == "active" else None

    def logout(self, token):
        self.x("DELETE FROM sessions WHERE token_hash=?", (_h(token),))

    # ---------- restablecer contraseña ----------
    def create_reset(self, uid) -> str:
        token = secrets.token_urlsafe(24)
        self.x("INSERT INTO resets(token_hash,user_id,expires) VALUES(?,?,?)",
               (_h(token), uid, time.time() + RESET_HOURS * 3600))
        return token

    def reset_password(self, token, password):
        r = self.q("SELECT * FROM resets WHERE token_hash=? AND expires>?", (_h(token), time.time()), one=True)
        if not r:
            raise DBError("El enlace no es válido o ha caducado. Pide otro al administrador.")
        if len(password or "") < auth.MIN_LENGTH:
            raise DBError(f"La contraseña debe tener al menos {auth.MIN_LENGTH} caracteres.")
        self.x("UPDATE users SET pw_hash=?, totp_secret='' WHERE id=?", (auth.make_hash(password), r["user_id"]))
        self.x("DELETE FROM resets WHERE user_id=?", (r["user_id"],))
        self.x("DELETE FROM sessions WHERE user_id=?", (r["user_id"],))   # cierra las sesiones abiertas
