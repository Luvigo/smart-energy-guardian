# FASE 1 — Estado y cierre (exterior modular)

Gemelo digital web en Three.js (`web3d/`). Esta fase cubre **solo el molde exterior modular** y la preparación del volumen interior (divisor corto). No hay integración IoT, dashboard ni firmware en este paquete.

## Alcance terminado

- Casa exterior modular: estructura fija, fachada removible, techo removible, jardín (césped, cerca con hueco a la puerta, camino, seis arbustos).
- Modos de visor: **Vista exterior** (cerrado) y **Mostrar piezas removibles** (techo elevado + fachada desplazada hacia el jardín).
- Ranuras de base y pestañas de fachada (visibles solo en desmontaje).
- Fachada con vanos reales (puerta y ventana); marco y vidrio desplazados en Z respecto al muro para evitar z-fighting (corrección del panel izquierdo del vano).
- Jardín anclado a los límites del terreno (`grassW` / `grassD` / `grassCy`): cerca, camino y **seis arbustos** alineados al volumen de la casa (sin desfase flotante respecto al césped).
- Divisor interior placeholder en mitad posterior (preparación FASE 2).
- Controles: arrastre para orbitar, scroll para zoom, **Restablecer vista**.

## Geometría y dimensiones (1 u = 1 cm)

| Parámetro | Valor |
|-----------|--------|
| Ancho interior `W` | 35 |
| Fondo interior `D` | 25 |
| Altura muros `WALL_H` | 13 |
| Cumbrera `Y_RIDGE` | 18 |
| Desmontaje techo `EXPLODED_ROOF_LIFT` | 14 (Y) |
| Desmontaje fachada | `(0, 0.45, -11.8)` — salida hacia **Z−** (jardín) |

## Orientación aprobada

- **Frente / jardín:** Z− (fachada removible).
- **Fondo:** Z+ (pared trasera).
- **Sala:** X+ (puerta) → izquierda en vista frontal desde el jardín.
- **Habitación:** X− (ventana) → derecha en pantalla.

## Divisor sala / habitación (placeholder)

- Longitud en Z: **~12,22 cm** (50 % de `D - 2·WALL_T`, antes ~24,44 cm).
- Ubicación: mitad **posterior** (de la pared trasera hacia el centro; borde frontal del muro ~Z = 0).
- Franja frontal libre (Z− hasta el divisor): **~12,5 cm** a todo el ancho, para electrónica en FASE 2.

## Limitaciones actuales

- `interiorGroup` existe pero está **vacío** (sin muebles, protoboards, Arduino ni sensores modelados).
- No hay botón «Vista interior» separado: el interior se observa con **Mostrar piezas removibles**.
- `interiorLegacy.js` no está conectado al visor actual (`main.js` usa solo `house.js`).
- Sin datos simulados ni protocolo serial.

## Evidencias finales (capturas)

Ruta: `web3d/docs/phase-1/final/`

| Archivo | Contenido |
|---------|-----------|
| `exterior-cerrado-frontal.png` | Exterior cerrado, frontal |
| `exterior-cerrado-tres-cuartos.png` | Exterior cerrado, tres cuartos |
| `exterior-cerrado-lateral.png` | Exterior cerrado, lateral derecho |
| `exterior-desmontado-frontal.png` | Piezas removibles, frontal |
| `exterior-desmontado-tres-cuartos.png` | Piezas removibles, tres cuartos |
| `interior-divisor-franja-libre.png` | Desmontaje real (techo/fachada visibles, desplazados); divisor y franja frontal |

## Referencias de diseño (no generadas por el visor)

- `web3d/references/01-estructura-modular.jpg`
- `web3d/references/02-casa-exterior-interior.jpg`

## Comandos

```bash
cd web3d
npm install
npm run dev      # desarrollo (Vite)
npm run build    # producción → dist/
npm run preview  # servir dist/
```

Regenerar capturas finales (opcional, requiere Playwright):

```bash
npm run build && npm run preview
# en otra terminal:
PREVIEW_URL=http://127.0.0.1:4173 node scripts/capture-phase-1.mjs
```

## Pendiente FASE 2 (no implementado)

- Modelado interior: suelos por estancia, muros interiores definitivos, zona electrónica en franja frontal.
- Poblar `interiorGroup` o equivalente sin romper el exterior aprobado.
- Componentes (Arduino, protoboards, sensores, actuadores) como geometría estática o anclada.
- Vista o flujo de usuario dedicado al interior, si se define en producto.
- Integración con dashboard / Arduino (fuera de `web3d/`).
