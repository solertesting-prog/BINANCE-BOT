# 👥 Plataforma multiusuario (beta privada)

Además de tu bot, el servidor ofrece una **plataforma para otras personas**: cada una tiene su cuenta, su panel y su propio bot.

> **Fase 1: solo modo simulado.** Los usuarios operan con dinero ficticio y precios reales. No se piden ni se guardan claves de exchange. La testnet, los pagos y el dinero real llegarán en fases posteriores (el dinero real, solo con el visto bueno legal: ver más abajo).

## Dirección

`https://app.` + la dirección de tu panel. Por ejemplo, si tu panel es `https://35-158-194-107.sslip.io`, la plataforma es **`https://app.35-158-194-107.sslip.io`**.

## Primer acceso (administrador)

En la terminal del servidor (ver SERVIDOR.md → Administración):

```
sudo -u valorize /opt/valorize-bot/venv/bin/python /opt/valorize-bot/plataforma.py --invitar-admin
```

Abre el enlace que muestra, elige tu email y contraseña. Ya eres administrador.

## Invitar a usuarios

1. Entra en la plataforma y pulsa **👥 Usuarios**.
2. Escribe una nota (por ejemplo, el nombre de la persona) y pulsa **Crear enlace de invitación**.
3. Envíale el enlace. Sirve para una sola persona y caduca en 7 días.

Desde la misma página puedes **desactivar** a un usuario (su bot se para y no puede entrar) y crear un **enlace para restablecer su contraseña** (válido 24 horas; también le desactiva la verificación en dos pasos para que vuelva a configurarla).

## Qué tiene cada usuario

- Su panel, con el mismo asistente (exchange, monedas, velas y riesgo), gráfico, historial y descarga a Excel.
- Su bot simulado, que sigue funcionando aunque cierre la pestaña y se reanuda solo si el servidor se reinicia.
- Sus avisos por Telegram (🔔 Avisos) y su verificación en dos pasos (🔒).
- Los datos de cada usuario están en `/opt/valorize-bot/plataforma-datos/` (base de datos y una carpeta por usuario).

## Límites

- Como máximo **25 usuarios** (`PLATFORM_MAX_USERS` en `.env`). El servidor t3.micro tiene 1 GB de memoria: si se queda corto, pasa a t3.small.
- Todos los usuarios comparten la conexión pública con el exchange (los precios se piden una vez para todos).

## ⚖️ Antes de cobrar o de usar dinero real de otras personas

Operar en las cuentas de terceros puede requerir autorización como proveedor de servicios de criptoactivos (MiCA). Consulta con un abogado especializado antes de las fases de pagos y dinero real.
