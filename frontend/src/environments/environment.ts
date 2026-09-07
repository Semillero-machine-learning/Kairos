/** Configuración de producción. La reemplaza `environment.development.ts` en `ng serve`. */
export const environment = {
  production: true,
  /** Origen del backend. Las rutas de negocio cuelgan de `/api/v1`; `/health` va en la raíz. */
  apiOrigin: 'https://api.kairospartners.uk',
};
