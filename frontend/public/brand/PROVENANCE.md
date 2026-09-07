# Procedencia de los assets de marca

No son imágenes generadas. Se derivan del logo original que entregó el
propietario del proyecto, conservado sin modificar en `frontend/logo/kairos_logo.jpeg`.

## Origen

`kairos_logo.jpeg` — logo de KAIROS provisto por el usuario el 2026-09-06.
Monograma "K" de trazo continuo sobre logotipo "KAIROS", con un degradado
horizontal de azul violeta a magenta. Llegó como JPEG con el fondo blanco
horneado y un margen amplio.

## Derivación

El JPEG trae la tinta ya compuesta sobre blanco. Como la aplicación se apoya en
un blanco entintado de violeta, pegarlo tal cual dejaba un rectángulo blanco
alrededor de la marca. Se invirtió esa composición:

    P = C·a + 255·(1−a)      →      C = (P − 255·(1−a)) / a
    con a = 1 − min(R,G,B)/255

El blanco puro da alfa 0 y la tinta saturada, alfa ≈ 1. Los píxeles con
min(R,G,B) ≥ 246 se fuerzan a transparente, para descartar el ruido de
compresión del JPEG sin comerse el antialiasing del trazo. Después se recorta al
contenido real y se escala al tamaño de uso.

**No se redibujó ni se aproximó nada.** Los archivos contienen exactamente los
mismos píxeles del original, con el fondo retirado.

## Archivos

| Archivo | Tamaño | Dónde se usa |
|---|---|---|
| `kairos-lockup.png` | 400 × 327 | Pantallas sin sesión, a 132 px de ancho; "no encontrado", a 96 px |
| `kairos-mark.png` | 93 × 96 | Barra lateral y barra superior, a 24 px de alto |
| `../favicon.png` | 96 × 96 | Icono de pestaña y de escritorio |

Los tres se guardan a unas tres o cuatro veces su tamaño de presentación, que es
el margen que necesitan las pantallas densas y ni un byte más: la primera carga
de esta aplicación ya es lenta por el arranque en frío del plan gratuito
(RNF-02).

## Si llega el original vectorial

Reemplazar los PNG por el SVG y ajustar `shared/ui/brand.component.ts`. El resto
de la aplicación no se entera: nada fuera de ese componente referencia estos
archivos.
