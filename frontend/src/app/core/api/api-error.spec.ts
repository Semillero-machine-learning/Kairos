import { HttpErrorResponse } from '@angular/common/http';
import { describe, expect, it } from 'vitest';

import { ApiError, CLIENT_ERROR_CODES, TimeoutError, toApiError } from './api-error';

describe('toApiError', () => {
  it('conserva el código y el mensaje del backend', () => {
    const error = toApiError(
      new HttpErrorResponse({
        status: 409,
        error: {
          error: {
            code: 'EMAIL_ALREADY_REGISTERED',
            message: 'Ese correo ya tiene una cuenta.',
            details: null,
          },
        },
      }),
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe('EMAIL_ALREADY_REGISTERED');
    // El mensaje del backend ya viene en español y se muestra tal cual.
    expect(error.message).toBe('Ese correo ya tiene una cuenta.');
    expect(error.status).toBe(409);
  });

  it('traduce el estado 0 a un fallo de red, no a un error del servidor', () => {
    const error = toApiError(new HttpErrorResponse({ status: 0, error: null }));

    expect(error.code).toBe(CLIENT_ERROR_CODES.NETWORK_ERROR);
    expect(error.status).toBe(0);
  });

  it('traduce el tiempo de espera agotado del interceptor de arranque en frío', () => {
    const error = toApiError(new TimeoutError());

    expect(error.code).toBe(CLIENT_ERROR_CODES.TIMEOUT);
    expect(error.message).toContain('tardó demasiado');
  });

  it('cae en un mensaje por estado cuando la respuesta no trae el formato de error', () => {
    const error = toApiError(new HttpErrorResponse({ status: 500, error: '<html>502</html>' }));

    expect(error.code).toBe(CLIENT_ERROR_CODES.UNKNOWN);
    expect(error.message).toContain('servidor');
  });

  it('no envuelve dos veces un ApiError que ya venía normalizado', () => {
    const original = new ApiError('LAST_ADMIN', 'No puedes dejar la plataforma sin administradores.', 409);

    expect(toApiError(original)).toBe(original);
  });

  it('reconoce varios códigos a la vez con `is`', () => {
    const error = new ApiError('INVITATION_EXPIRED', 'La invitación venció.', 409);

    expect(error.is('INVITATION_EXPIRED', 'INVITATION_ALREADY_USED')).toBe(true);
    expect(error.is('NOT_FOUND')).toBe(false);
  });
});
