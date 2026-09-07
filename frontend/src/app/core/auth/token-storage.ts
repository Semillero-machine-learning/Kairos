/**
 * Persistencia de los tokens entre recargas.
 *
 * `localStorage` puede lanzar (modo privado, almacenamiento bloqueado por el
 * navegador), así que todo acceso va envuelto: sin tokens la aplicación
 * simplemente pide ingresar de nuevo, que es un estado válido, no un error.
 */
const ACCESS_KEY = 'kairos.access_token';
const REFRESH_KEY = 'kairos.refresh_token';

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Sin persistencia la sesión dura lo que dure la pestaña. Es aceptable.
  }
}

function remove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Nada que hacer: si no se pudo escribir, tampoco hay nada que borrar.
  }
}

export const tokenStorage = {
  load(): StoredTokens | null {
    const accessToken = read(ACCESS_KEY);
    const refreshToken = read(REFRESH_KEY);
    if (!accessToken || !refreshToken) return null;
    return { accessToken, refreshToken };
  },

  save(tokens: StoredTokens): void {
    write(ACCESS_KEY, tokens.accessToken);
    write(REFRESH_KEY, tokens.refreshToken);
  },

  clear(): void {
    remove(ACCESS_KEY);
    remove(REFRESH_KEY);
  },
};
