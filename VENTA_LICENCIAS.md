# 💼 Vender Valorize Bot con licencias

> 🆓 **Ahora mismo Valorize Bot es gratuito:** en `licensing.py` está `REQUIRE_LICENSE = False`, así que no pide licencia y el indicador 🔑 no aparece en el panel. Cuando quieras empezar a cobrar, sigue esta guía y cambia esa línea a `REQUIRE_LICENSE = True`.

Guía para ti como vendedor. Tus clientes **no** necesitan leer esto: ellos usan `MANUAL_CLIENTE.md`.

## Cómo funciona

```
Cliente compra en tu tienda de Lemon Squeezy (pago mensual)
        │  recibe por email: clave de licencia + enlace de descarga del ZIP
        ▼
Instala Valorize Bot  →  pega la clave en el panel  →  "Activar"
        │  este PC queda registrado como una activación de su clave
        ▼
El bot comprueba la licencia al arrancar y cada 6 h
        │  si deja de pagar → la licencia pasa a "caducada" → el bot deja de operar en real
        ▼
Sin internet sigue funcionando 72 h (periodo de gracia)
```

- **Modo simulado gratis:** sin licencia, el cliente puede probar el bot en modo simulado. La licencia hace falta para testnet y dinero real. Sirve como **prueba gratuita** para convencer. Si no lo quieres, pon `FREE_PAPER_MODE = False` en `licensing.py`.
- **Lemon Squeezy** cobra, envía las claves y los archivos, y gestiona el IVA europeo (actúa como "merchant of record"). Cobra una comisión por venta: consulta sus tarifas actuales en su web.

## Paso 1 · Crear la tienda y el producto en Lemon Squeezy

1. Crea una cuenta en **https://www.lemonsqueezy.com** y una tienda (por ejemplo, "Valorize"). Completa los datos fiscales y de cobro que te pida.
2. Crea un **producto** "Valorize Bot":
   - **Precio:** suscripción (por ejemplo, mensual). Puedes crear variantes: mensual, anual…
   - Activa **generar claves de licencia** (license keys).
   - **Límite de activaciones:** cuántos PCs por licencia (recomendado: 1 o 2).
   - **Duración de la licencia:** que dure mientras la suscripción esté activa. Así, si el cliente deja de pagar, la clave pasa a "caducada" sola.
   - **Archivo descargable:** sube el ZIP compilado (Paso 3).
3. Apunta estos datos (aparecen en el panel de Lemon Squeezy):
   - El **ID de tu tienda** (store ID).
   - El **ID del producto** (product ID).
   - El **enlace de compra** del producto (botón para compartir o *checkout link*).

> 💡 Mientras pruebas, usa el **modo de pruebas** (test mode) de Lemon Squeezy: puedes "comprar" con tarjetas de prueba y obtener claves sin cobrar a nadie.

## Paso 2 · Poner tus datos en el bot

Abre `licensing.py` con el Bloc de notas y rellena las líneas del principio:

```python
STORE_ID = 123456                 # el ID de tu tienda
PRODUCT_IDS = [654321]            # el ID del producto (varios si tienes más: [654321, 654322])
PURCHASE_URL = "https://..."      # tu enlace de compra (aparece como "Comprar licencia" en el panel)
REQUIRE_LICENSE = True            # activa el cobro de licencias
FREE_PAPER_MODE = True            # False = sin prueba gratuita en simulado
```

`STORE_ID` y `PRODUCT_IDS` son importantes: impiden que alguien use una clave de otra tienda o de otro producto.

**Pruébalo antes de compilar:** abre el panel → botón **🔑** → pega una clave de prueba → **Activar**. Debe salir "Licencia activa". Después, en Lemon Squeezy, desactiva esa clave y pulsa **Comprobar ahora**: debe pasar a "no válida".

## Paso 3 · Compilar el programa para tus clientes

Si entregas el código Python, cualquiera con conocimientos puede borrar la comprobación de licencia. Por eso a los clientes se les entrega un **programa compilado** (`ValorizeBot.exe`), que no deja ver ni cambiar el código.

1. Haz doble clic en **`compilar.bat`**.
2. La primera vez descarga un compilador y tarda **entre 20 y 60 minutos**. No cierres la ventana.
3. Al terminar tendrás:
   - `dist\Valorize Bot\`: la carpeta del programa.
   - `dist\ValorizeBot-1.0.zip`: **esto es lo que subes a Lemon Squeezy** como archivo del producto.
4. **Pruébalo tú primero:** descomprime el ZIP en otra carpeta, ejecuta "Instalar Valorize Bot.bat", activa una clave de prueba y comprueba que todo funciona.

> ⚠️ El script de compilación está preparado pero **todavía no se ha probado en tu PC**. Si falla, copia el mensaje de error y pásamelo.

### Si la compilación falla con "Una directiva de Control de aplicaciones bloqueó este archivo"

Windows 11 tiene el **Control inteligente de aplicaciones** (Smart App Control), que bloquea el compilador gratuito MinGW porque no está firmado. La solución es usar el compilador de Microsoft, que sí está firmado:

1. Descarga **Build Tools para Visual Studio** desde https://visualstudio.microsoft.com/es/downloads/ (al final de la página, en "Herramientas para Visual Studio").
2. En el instalador, marca **"Desarrollo para el escritorio con C++"** y pulsa **Instalar** (ocupa varios GB y tarda un rato).
3. Vuelve a ejecutar `compilar.bat`: detecta solo el compilador de Microsoft y lo usa.

> No es recomendable desactivar el Control inteligente de aplicaciones: en Windows 11 no se puede volver a activar sin reinstalar Windows.

### Firma digital del .exe (importante para vender)

Ese mismo Control inteligente de aplicaciones puede **bloquear tu `ValorizeBot.exe` en los PCs de tus clientes**, porque es un programa nuevo y sin firma digital. Además, Windows mostrará avisos de "editor desconocido". Para distribuirlo de forma profesional necesitarás un **certificado de firma de código** (code signing) de una autoridad reconocida, que tiene un coste anual, o un servicio de firma en la nube como Azure Trusted Signing. Es un paso a resolver antes de vender.

Cada vez que publiques una versión nueva, sube el número de versión en `compilar.bat` (`1.0.0.0` y el nombre del ZIP), compila y sustituye el archivo en Lemon Squeezy.

## Paso 4 · Proteger el código fuente

- **Haz privado tu repositorio de GitHub:** *Settings → General → Danger Zone → Change visibility → Private*. Si es público, cualquiera puede descargar el código y usarlo sin licencia.
- No compartas la carpeta de desarrollo (la que tiene los `.py`). A los clientes, solo el ZIP compilado.

## Gestión del día a día

| Situación | Qué hacer |
|---|---|
| Un cliente cambia de PC | Que pulse **🔑 → Desactivar en este PC** en el viejo y active en el nuevo. Si ya no tiene el viejo, borra la activación desde Lemon Squeezy (en la clave de licencia). |
| Un cliente deja de pagar | No hagas nada: al caducar la suscripción la clave pasa a "caducada" y el bot deja de operar en real (en un máximo de 6 h). |
| Quieres cortar una licencia ya | Desactiva la clave en Lemon Squeezy. |
| Quieres regalar una licencia | Crea un descuento del 100 % o genera la clave a mano desde Lemon Squeezy. |
| Volver a hacerlo gratis | Pon `REQUIRE_LICENSE = False` y vuelve a compilar. |

## Qué ve el cliente

- Arriba en el panel, un indicador: **🔑 Prueba gratuita**, **🔑 Licencia activa** o **🔑 Licencia no válida**.
- Al pulsarlo: pantalla para pegar la clave y botón **Comprar licencia** (tu enlace).
- Si intenta arrancar en real sin licencia, se abre esa pantalla automáticamente.
- Si la licencia caduca con el bot en marcha, el bot se para y avisa (también por Telegram si lo tiene configurado). Las posiciones abiertas mantienen su stop en el exchange.

## ⚖️ Antes de vender: aspectos legales

No soy abogado; consulta con un asesor antes de lanzarlo. Puntos a revisar:

- **Software, no asesoramiento.** Vende el bot como herramienta que el cliente configura y usa en **su propia cuenta**, con sus claves. Prestar asesoramiento de inversión o gestionar dinero de terceros está regulado en España y la UE (CNMV, MiFID II, MiCA para criptoactivos).
- **Publicidad.** No prometas rentabilidades. Los resultados pasados no garantizan los futuros.
- **Términos de uso y aviso de riesgo** que el cliente acepte al comprar, con limitación de responsabilidad.
- **Facturación e impuestos.** Lemon Squeezy gestiona el IVA de las ventas, pero tú declaras tus ingresos como autónomo o empresa.
