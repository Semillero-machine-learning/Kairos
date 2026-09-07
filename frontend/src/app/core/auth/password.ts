/**
 * Regla de contraseña, la misma que aplica el backend
 * (`UsersService.validate_password_strength`).
 *
 * Se repite aquí para poder avisar antes de enviar el formulario, no para
 * sustituir la validación del servidor: el backend la vuelve a comprobar
 * siempre.
 */
export const PASSWORD_MIN_LENGTH = 10;

export const PASSWORD_HINT = `Mínimo ${PASSWORD_MIN_LENGTH} caracteres.`;

export const PASSWORD_TOO_SHORT = `La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`;
