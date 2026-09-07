/**
 * Error normalizado de la API.
 *
 * El backend responde siempre con el formato de `architecture.md` §7:
 * `{ "error": { "code": "...", "message": "...", "details": null } }`.
 * Los códigos van en inglés porque los consume el frontend; el mensaje ya
 * viene en español y se puede mostrar tal cual.
 */

/** Cuerpo de error tal como lo emite el backend. */
export interface ApiErrorBody {
  error: { code: string; message: string; details: unknown };
}

/** Códigos que no vienen del backend: fallos de red o del propio navegador. */
export const CLIENT_ERROR_CODES = {
  /** No hubo respuesta: sin conexión, CORS o servidor caído. */
  NETWORK_ERROR: 'NETWORK_ERROR',
  /** La petición superó el tiempo máximo de espera (arranque en frío, RNF-02). */
  TIMEOUT: 'TIMEOUT',
  /** Respuesta con un formato que no reconocemos. */
  UNKNOWN: 'UNKNOWN',
} as const;

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details: unknown = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** `true` si el código coincide con alguno de los indicados. */
  is(...codes: string[]): boolean {
    return codes.includes(this.code);
  }
}

/**
 * El mensaje más específico que trae un error, para mostrárselo a quien acaba
 * de escribir el formulario.
 *
 * Un `VALIDATION_ERROR` llega con un mensaje genérico y el detalle por campo en
 * `details`, que es donde está lo útil: «El enlace debe apuntar a GitHub…» en
 * vez de «Los datos enviados no son válidos». Pydantic antepone «Value error, »
 * a lo que levanta un validador propio; ese prefijo es ruido en inglés y se
 * recorta.
 */
export function fieldMessage(error: ApiError): string {
  if (error.code !== 'VALIDATION_ERROR' || !Array.isArray(error.details)) {
    return error.message;
  }
  const first = error.details.find(
    (detail): detail is { msg: string } =>
      typeof detail === 'object' &&
      detail !== null &&
      typeof (detail as { msg?: unknown }).msg === 'string',
  );
  return first ? first.msg.replace(/^Value error,\s*/, '') : error.message;
}

const FALLBACK_MESSAGES: Record<number, string> = {
  401: 'Tu sesión no es válida. Vuelve a ingresar.',
  403: 'No tienes permiso para hacer esto.',
  404: 'No encontramos lo que buscas.',
  409: 'La operación entra en conflicto con el estado actual.',
  422: 'Revisa los datos: hay algo que no es válido.',
  500: 'El servidor tuvo un problema. Intenta de nuevo en un momento.',
};

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false;
  const inner = (value as { error: unknown }).error;
  return (
    typeof inner === 'object' &&
    inner !== null &&
    typeof (inner as { code?: unknown }).code === 'string' &&
    typeof (inner as { message?: unknown }).message === 'string'
  );
}

/** Convierte cualquier fallo de `HttpClient` en un `ApiError`. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (error instanceof TimeoutError) {
    return new ApiError(
      CLIENT_ERROR_CODES.TIMEOUT,
      'El servidor tardó demasiado en responder. Intenta de nuevo.',
      0,
    );
  }

  if (isHttpErrorResponse(error)) {
    // status 0 significa que la petición nunca llegó a destino.
    if (error.status === 0) {
      return new ApiError(
        CLIENT_ERROR_CODES.NETWORK_ERROR,
        'No pudimos conectar con el servidor. Revisa tu conexión.',
        0,
      );
    }
    if (isApiErrorBody(error.error)) {
      const { code, message, details } = error.error.error;
      return new ApiError(code, message, error.status, details ?? null);
    }
    return new ApiError(
      CLIENT_ERROR_CODES.UNKNOWN,
      FALLBACK_MESSAGES[error.status] ?? 'Ocurrió un error inesperado.',
      error.status,
    );
  }

  return new ApiError(CLIENT_ERROR_CODES.UNKNOWN, 'Ocurrió un error inesperado.', 0);
}

/** Error propio del interceptor cuando se agota el tiempo de espera. */
export class TimeoutError extends Error {
  constructor() {
    super('La petición superó el tiempo máximo de espera.');
    this.name = 'TimeoutError';
  }
}

function isHttpErrorResponse(error: unknown): error is {
  status: number;
  error: unknown;
} {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    typeof (error as { status: unknown }).status === 'number' &&
    'error' in error
  );
}
