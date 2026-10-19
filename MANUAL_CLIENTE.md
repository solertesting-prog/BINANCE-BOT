# 📘 Valorize Bot · Guía de inicio

Valorize Bot compra y vende criptomonedas automáticamente en tu exchange (Binance, Kraken, Coinbase, OKX, Bybit, KuCoin y muchos más), con gestión del riesgo y stop loss en cada operación.

> ⚠️ Operar con criptomonedas tiene riesgo. Ningún bot garantiza ganancias. Usa solo dinero que puedas permitirte perder.

## 1. Instalar (2 minutos)

1. Descomprime el ZIP que descargaste (clic derecho → **Extraer todo**) en una carpeta fija, por ejemplo **Documentos**.
2. Entra en la carpeta **Valorize Bot** y haz doble clic en **"Instalar Valorize Bot"**.
   - Si Windows muestra "Windows protegió su PC", pulsa **Más información → Ejecutar de todas formas**.
3. Te pregunta si quieres que se abra solo al encender el PC (recomendado: **S**).
4. Se crea el icono **Valorize Bot** en el escritorio y se abre el panel en tu navegador.

## 2. Activar tu licencia

1. Arriba en el panel, pulsa **🔑**.
2. Pega la **clave de licencia** que recibiste por email al comprar y pulsa **Activar**.
3. Verás "✓ Licencia activa".

Sin licencia puedes usar el **modo simulado** gratis (dinero ficticio) para probar el bot.

## 3. Conectar tu exchange

La primera vez se abre el asistente (luego lo tienes en **⚙ Configuración**):

1. **Exchange:** elige el tuyo.
2. **Modo:** **Simulado** (dinero ficticio, recomendado para empezar), **Testnet** (pruebas) o **Dinero real**.
3. **Claves:** crea una clave de API en tu exchange (sección **API** de los ajustes de tu cuenta) con estos permisos: ✅ **Lectura**, ✅ **Trading spot**, ❌ **Retiros: nunca**. Pégala y pulsa **Probar conexión**.
4. **Monedas:** elige con qué compras (USDT, EUR…), qué monedas operar, el tamaño de las velas y el riesgo por operación (1 % recomendado).
5. **Guardar y aplicar.**

Tus claves se guardan solo en tu ordenador.

## 4. Usar el panel

- **▶ Arrancar** / **■ Parar**: pone el bot en marcha o lo detiene.
- **Gráfico:** precio con las compras ▲ y ventas ▼ del bot y la línea de stop.
- **Posiciones abiertas:** cada compra con su resultado y su stop. **Cerrar posición** vende al momento.
- **Puedes cerrar la pestaña del navegador:** el bot sigue funcionando. Para volver, usa el icono del escritorio.
- **⏻** apaga el bot por completo.
- El bot puede pasar **días sin operar**: espera a que se cumplan todas las condiciones.

**Importante:** el PC no debe suspenderse mientras quieras que opere (*Configuración → Sistema → Inicio/apagado y suspensión → Nunca*).

## 5. Cómo protege tu dinero

- Cada operación arriesga como máximo el % que elegiste (por defecto, el 1 % del capital).
- Stop loss que se adapta a la volatilidad y sube con el precio para proteger lo ganado.
- En dinero real, el stop queda **puesto en el exchange** (si lo permite), así protege aunque tu PC se apague.
- Si el capital cae un 20 %, el bot vende todo y se detiene.
- Solo vende lo que compró él: no toca el resto de tus monedas.

## 6. Cambiar de ordenador

En el PC viejo: **🔑 → Desactivar en este PC**. Después instala y activa en el nuevo.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| El icono no abre nada | Espera unos segundos o abre en el navegador **http://127.0.0.1:8765** |
| "No se pudo conectar con el exchange" | ⚙ Configuración → Probar conexión: te dice qué falla |
| "Licencia no válida" o "caducada" | Revisa tu suscripción o contacta con el vendedor |
| "Licencia activada en el máximo de ordenadores" | Desactívala en el otro PC (🔑 → Desactivar) |
| Reloj desajustado (recvWindow, timestamp) | Configuración de Windows → Hora → **Sincronizar ahora** |
