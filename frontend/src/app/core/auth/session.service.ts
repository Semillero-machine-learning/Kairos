/**
 * Sesión del usuario: quién es, qué tokens tiene y cómo se renuevan.
 *
 * Los permisos NO viven aquí ni en el token (RN-22): el rol global sirve para
 * decidir qué mostrar, pero cada operación la autoriza el backend en su propia
 * petición. Ocultar un botón es comodidad, nunca la barrera.
 */
import { HttpClient, HttpContext, HttpContextToken } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, catchError, map, of, shareReplay, tap, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { toApiError } from '../api/api-error';
import { Me, TokenResponse, User } from '../api/models';
import { tokenStorage } from './token-storage';

/** Marca las peticiones que el interceptor no debe intentar reintentar tras un
 * 401: el propio refresco, y el ingreso. Reintentarlas sería un bucle. */
export const SKIP_AUTH_REFRESH = new HttpContextToken<boolean>(() => false);

export function skipAuthRefresh(): HttpContext {
  return new HttpContext().set(SKIP_AUTH_REFRESH, true);
}

@Injectable({ providedIn: 'root' })
export class SessionService {
  private readonly http = inject(HttpClient);

  private readonly accessTokenSignal = signal<string | null>(null);
  private readonly refreshTokenSignal = signal<string | null>(null);
  private readonly userSignal = signal<User | Me | null>(null);

  /** `true` hasta que se resuelve el primer intento de restaurar la sesión. */
  private readonly restoringSignal = signal(true);

  /** Refresco en vuelo. Las peticiones concurrentes que reciban 401 se
   * enganchan a este mismo observable en vez de disparar un refresco cada una
   * (architecture.md §5). */
  private refreshInFlight: Observable<string> | null = null;

  readonly user = this.userSignal.asReadonly();
  readonly restoring = this.restoringSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.userSignal() !== null);
  readonly isAdmin = computed(() => this.userSignal()?.global_role === 'ADMIN');

  accessToken(): string | null {
    return this.accessTokenSignal();
  }

  hasStoredSession(): boolean {
    return this.refreshTokenSignal() !== null;
  }

  /**
   * Restaura la sesión al arrancar la aplicación. Lee los tokens guardados y
   * pide el perfil; si el token de acceso ya venció, el interceptor lo renueva
   * de forma transparente. Nunca lanza: sin sesión válida devuelve `false`.
   */
  restore(): Observable<boolean> {
    const stored = tokenStorage.load();
    if (!stored) {
      this.restoringSignal.set(false);
      return of(false);
    }

    this.accessTokenSignal.set(stored.accessToken);
    this.refreshTokenSignal.set(stored.refreshToken);

    return this.http.get<Me>(`${environment.apiOrigin}/api/v1/auth/me`).pipe(
      tap((me) => this.userSignal.set(me)),
      map(() => true),
      catchError(() => {
        this.clear();
        return of(false);
      }),
      tap(() => this.restoringSignal.set(false)),
    );
  }

  /** Guarda la sesión que devuelve un ingreso o una aceptación de invitación. */
  adopt(tokens: TokenResponse): void {
    this.accessTokenSignal.set(tokens.access_token);
    this.refreshTokenSignal.set(tokens.refresh_token);
    this.userSignal.set(tokens.user);
    this.restoringSignal.set(false);
    tokenStorage.save({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    });
  }

  /** Actualiza el perfil en memoria tras editar el nombre. */
  patchUser(user: Partial<User & Me>): void {
    const current = this.userSignal();
    if (current) this.userSignal.set({ ...current, ...user });
  }

  clear(): void {
    this.accessTokenSignal.set(null);
    this.refreshTokenSignal.set(null);
    this.userSignal.set(null);
    this.restoringSignal.set(false);
    this.refreshInFlight = null;
    tokenStorage.clear();
  }

  /**
   * Renueva el token de acceso. Varias llamadas concurrentes comparten el
   * mismo refresco: el backend rota el token de refresco en cada uso (RN-43),
   * así que disparar dos invalidaría uno de los dos.
   */
  refresh(): Observable<string> {
    if (this.refreshInFlight) return this.refreshInFlight;

    const refreshToken = this.refreshTokenSignal();
    if (!refreshToken) {
      return throwError(() =>
        toApiError({ status: 401, error: null }),
      );
    }

    this.refreshInFlight = this.http
      .post<TokenResponse>(
        `${environment.apiOrigin}/api/v1/auth/refresh`,
        { refresh_token: refreshToken },
        { context: skipAuthRefresh() },
      )
      .pipe(
        tap({
          next: (tokens) => {
            this.adopt(tokens);
            this.refreshInFlight = null;
          },
          error: () => {
            this.refreshInFlight = null;
          },
        }),
        map((tokens) => tokens.access_token),
        // Un solo refresco compartido por todas las peticiones en espera.
        shareReplay({ bufferSize: 1, refCount: false }),
      );

    return this.refreshInFlight;
  }

  /** Cierra la sesión revocando el token de refresco en el servidor. Si la
   * llamada falla, la sesión local se cierra igual: el usuario pidió salir. */
  logout(): Observable<void> {
    const refreshToken = this.refreshTokenSignal();
    if (!refreshToken) {
      this.clear();
      return of(void 0);
    }
    return this.http
      .post<void>(
        `${environment.apiOrigin}/api/v1/auth/logout`,
        { refresh_token: refreshToken },
        { context: skipAuthRefresh() },
      )
      .pipe(
        catchError(() => of(void 0)),
        tap(() => this.clear()),
      );
  }
}
