# Sistema de diseño

## La dirección: terminal de inteligencia, no dashboard de SaaS

El jurado son oficiales de inteligencia de la FAC y expertos técnicos de empresas. No los impresiona un dashboard bonito de producto; los impresiona algo que **parezca una herramienta de trabajo real**.

La referencia correcta es el terminal financiero y el centro de operaciones: fondo oscuro, densidad alta de información, cifras de altísimo contraste, cero decoración que no cargue dato. La tendencia 2026 en productos de monitoreo de sesión larga es precisamente dark-mode-first con estética de terminal, porque son interfaces donde alguien pasa horas.

Lo que **no** queremos: tarjetas blancas con sombras suaves, ilustraciones, gradientes pastel, iconos redondeados. Eso lee a SaaS de startup y le resta seriedad al dominio.

---

## Color

Un solo acento saturado por pantalla. El color se gasta en lo que importa, no en decorar.

```css
--fondo:            #08090B   /* casi negro, no negro puro */
--superficie:       #101318   /* paneles */
--superficie-alta:  #171B22   /* hover, elementos elevados */
--borde:            #232830
--borde-sutil:      #1A1E25

--texto:            #E8EAED
--texto-medio:      #9BA3AF
--texto-tenue:      #626A77

--acento:           #22D3EE   /* cian frío: lo activo, lo seleccionado */
--alerta:           #F5A524   /* ámbar: atención, presupuesto al 70% */
--critico:          #F04438   /* rojo: solo para fallo real */
--anomalia:         #C084FC   /* magenta apagado: detección anómala */
--ok:               #34D399
```

### Reglas

- El rojo **solo** significa fallo o riesgo. Nunca lo uses para "grupo armado 3" en una leyenda. La charla del Día 4 fue explícita sobre esto: el color carga significado antes de que el usuario lea la leyenda.
- Las escalas de mapa van de un solo tono, de claro a oscuro. Nada de arcoíris.
- Verifica contraste antes de decidir una escala. Si dos categorías adyacentes no se distinguen, la visualización miente.
- Las leyendas van **fuera** del mapa, nunca encima.

---

## Tipografía

```css
--sans: "Geist", "Inter", system-ui, sans-serif;
--mono: "Geist Mono", "JetBrains Mono", ui-monospace, monospace;
```

- Interfaz y prosa en sans.
- **Todo número en mono, y con `tabular-nums`.** Las cifras que cambian sin ancho fijo bailan, y eso se ve amateur en una demo en vivo.
- Identificadores del corpus (`F3-ALERTAS-032`) siempre en mono. Refuerza que son datos reales y trazables.
- Escala corta: 12 / 14 / 16 / 20 / 28 / 40. Nada intermedio.
- Interlineado 1.5 en prosa, 1.2 en cifras grandes.

---

## Movimiento

Motion para todo. La animación sirve al dato o no existe.

- Entradas de elementos: 150 a 200 ms, `ease-out`. Nunca más de 250.
- Transiciones de estado en cifras: interpolar el número, no hacerlo aparecer de golpe.
- El stream de tokens del asistente es la animación principal de la aplicación. No le pongas nada encima que compita.
- La traza de agentes aparece como una escalera: cada span entra cuando llega su evento. **Eso es lo que hace visible la arquitectura multiagente**, y es lo que el jurado necesita ver para creer que hay tres agentes y no uno.
- Respeta `prefers-reduced-motion`.

**Nada bloquea la lectura.** Si una animación hace esperar para leer un dato, sobra.

---

## Visualización: la decisión que nos diferencia

Los tres fenómenos tienen geografías distintas, y eso debe reflejarse en la visualización:

| Fenómeno | Geografía real | Visualización |
|---|---|---|
| F1 — IA militar | Global: EE.UU., China, Rusia, UE | **Globo 3D** |
| F2 — Espacial | Órbita terrestre baja | **Globo 3D** con capa orbital |
| F3 — Territorial | América Latina, nivel municipal | **Coroplético 2D** |

El globo no es adorno: **F2 es literalmente órbita terrestre baja**, y representarla en un mapa plano es representarla mal. Ese argumento va en el pitch.

Para el globo: `react-globe.gl` o `r3f-globe` de vasturiano, que son maduros, soportan GeoJSON y arcos, y cargan con `dynamic(..., { ssr: false })` en Next.js. No escribir un globo desde cero con Three.js puro; no hay tiempo y no aporta.

Para el coroplético: los PCODEs de Amazon Underworld (`b_ADM1_PCODE`, `b_ADM2_PCODE`) son códigos HDX estándar que se unen directo a GeoJSON público. No hay que geocodificar nada.

---

## Estructura de pantallas

### Asistente (Reto 1)

Tres zonas, proporción aproximada 20 / 55 / 25:

- **Izquierda**: hilo de conversación e historial. Colapsable.
- **Centro**: la conversación. El mensaje del asistente con citas inline `[F3-ALERTAS-032]` que al pasar el cursor muestran el fragmento y al hacer clic abren el panel derecho.
- **Derecha**: panel de evidencia y traza, en dos pestañas. Evidencia lista los fragmentos citados con su observatorio y fenómeno. Traza muestra la escalera de agentes con tiempo, tokens y costo por span.

En móvil, las tres zonas se apilan y el panel derecho se vuelve una hoja inferior.

### Tablero (Reto 2)

Maestro-detalle, que es el patrón que recomendó la charla del Día 4: mapa grande al centro y lista de detalle al lado, como las páginas de reserva.

- Barra superior de **filtros globales**: fenómeno, rango de años, país, grupo armado
- Bento grid con KPIs arriba
- Visualización principal: globo o coroplético según el fenómeno activo
- Panel lateral de detalle de lo seleccionado
- **Brushing and linking**: seleccionar en cualquier vista filtra todas las demás
- Caja de pregunta anclada abajo que **hereda los filtros activos** y los manda al asistente

Ese último punto es lo que conecta los dos retos y lo que eleva el mínimo a tres agentes. No es un detalle de interfaz: es el requisito.

---

## Componentes

De shadcn/ui la base: `card`, `tabs`, `sheet`, `tooltip`, `command`, `scroll-area`, `badge`, `skeleton`.

De 21st.dev, con criterio: bento grid para la portada del tablero, y primitivas de Motion para transiciones de texto y entradas. El catálogo tiene mucho efecto llamativo tipo aurora y sparkles que **no encaja** con esta dirección. Tomar el layout y la animación, no el brillo.

Todo componente debe existir en tres estados: **cargando**, **vacío** y **error**. El estado vacío es el que más se ve en una demo y el que más equipos descuidan.

---

## Lo que el backend debe mostrar y casi nadie muestra

- **Progreso de arranque real.** Mientras el Retriever carga, `/health` devuelve texto tipo `"cargando índice bge_m3 · 38 s"`. Mostrarlo. Una pantalla congelada durante 55 segundos ya te calificó.
- **Costo por turno**, visible y pequeño al pie de cada respuesta. Es criterio de rúbrica y demuestra que lo controlamos.
- **La ruta de agentes** de cada respuesta, como cadena de chips: `guardia → planner → investigador → redactor`.

---

## Responsive

Se prueba en 390 px de ancho, no solo en el portátil. El jurado puede abrirlo en un teléfono.

- Gutter lateral mínimo de 16 px en todo ancho
- Tablas y el globo dentro de contenedores con scroll horizontal propio
- El cuerpo de la página nunca hace scroll horizontal
- Objetivos táctiles de 44 px mínimo

---

## Criterio para decidir rápido a las 04:00

Si dudas entre dos opciones, gana la que hace que **el dato se lea más rápido**. Ese es el único criterio que importa en una herramienta de análisis, y es el que el jurado va a aplicar sin decirlo.
