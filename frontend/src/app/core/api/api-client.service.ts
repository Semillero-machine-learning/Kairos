/**
 * Cliente HTTP de la aplicación.
 *
 * Ningún componente llama a `HttpClient` directamente (CLAUDE.md): todo pasa
 * por los servicios de `core/api/`, y esos servicios pasan por aquí. Resuelve
 * la URL base, limpia los parámetros vacíos y normaliza los errores a
 * `ApiError`.
 */
import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ApiError, toApiError } from './api-error';

/** Valores admitidos en la cadena de consulta. Los nulos se descartan. */
export type QueryParams = Record<string, string | number | boolean | null | undefined>;

@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiOrigin}/api/v1`;

  get<T>(path: string, params?: QueryParams): Observable<T> {
    return this.request(this.http.get<T>(this.url(path), { params: toHttpParams(params) }));
  }

  post<T>(path: string, body: unknown = {}): Observable<T> {
    return this.request(this.http.post<T>(this.url(path), body));
  }

  patch<T>(path: string, body: unknown = {}): Observable<T> {
    return this.request(this.http.patch<T>(this.url(path), body));
  }

  put<T>(path: string, body: unknown = {}): Observable<T> {
    return this.request(this.http.put<T>(this.url(path), body));
  }

  delete<T>(path: string): Observable<T> {
    return this.request(this.http.delete<T>(this.url(path)));
  }

  /** `/health` cuelga de la raíz, no de `/api/v1` (api-contract.md §9). */
  health(): Observable<{ status: string }> {
    return this.request(this.http.get<{ status: string }>(`${environment.apiOrigin}/health`));
  }

  private url(path: string): string {
    return `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  }

  private request<T>(source: Observable<T>): Observable<T> {
    return source.pipe(catchError((error) => throwError((): ApiError => toApiError(error))));
  }
}

function toHttpParams(params?: QueryParams): HttpParams {
  let httpParams = new HttpParams();
  if (!params) return httpParams;
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') continue;
    httpParams = httpParams.set(key, String(value));
  }
  return httpParams;
}
