# SMART ENERGY HOME — visor 3D (FASE 1: exterior)

Gemelo digital web en Three.js. Esta fase no conecta Arduino ni muestra datos de sensores.

Estado detallado y capturas finales: [docs/PHASE_1_STATUS.md](docs/PHASE_1_STATUS.md).

## Ejecutar en desarrollo

```bash
cd web3d
npm install
npm run dev
```

Abre la URL que muestre Vite (por ejemplo `http://localhost:5173`).

## Build de producción

```bash
npm run build
npm run preview
```

## Controles en el visor

- **Vista exterior** — molde cerrado.
- **Mostrar piezas removibles** — techo elevado y fachada hacia el jardín (Z−).
- **Restablecer vista** — cierra el desmontaje y restaura cámara exterior.
