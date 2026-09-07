import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';

import { ColdStartService } from './cold-start.service';

describe('ColdStartService', () => {
  let service: ColdStartService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ColdStartService);
  });

  it('no avisa mientras ninguna petición se ha pasado de lenta', () => {
    expect(service.waking()).toBe(false);
  });

  it('sigue avisando mientras quede al menos una petición lenta', () => {
    service.markSlow();
    service.markSlow();
    expect(service.waking()).toBe(true);

    // La primera termina: la otra sigue en vuelo, el aviso se queda.
    service.clearSlow();
    expect(service.waking()).toBe(true);

    service.clearSlow();
    expect(service.waking()).toBe(false);
  });

  it('no baja de cero si se libera de más', () => {
    service.clearSlow();
    service.clearSlow();
    expect(service.waking()).toBe(false);

    // Una petición lenta después de eso sí debe volver a encender el aviso.
    service.markSlow();
    expect(service.waking()).toBe(true);
  });
});
