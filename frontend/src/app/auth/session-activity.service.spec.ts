import { TestBed } from '@angular/core/testing';

import { SessionActivityService } from './session-activity.service';

describe('SessionActivityService', () => {
  let service: SessionActivityService;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-01-01T00:00:00Z'));
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [SessionActivityService],
    });

    service = TestBed.inject(SessionActivityService);
  });

  afterEach(() => {
    service.stop();
    localStorage.clear();
    jest.useRealTimers();
  });

  it('registra actividad inicial al iniciar la sesión', () => {
    service.start(jest.fn());

    expect(service.getLastActivityAt()).toBe(Date.now());
    expect(service.isIdleExpired()).toBe(false);
  });

  it('actualiza la actividad cuando el usuario interactúa', () => {
    service.start(jest.fn());

    jest.setSystemTime(new Date('2026-01-01T00:10:00Z'));
    window.dispatchEvent(new Event('click'));

    expect(service.getLastActivityAt()).toBe(Date.now());
  });

  it('ejecuta el callback cuando se cumple 1h de inactividad', () => {
    const onExpired = jest.fn();
    service.start(onExpired);

    jest.advanceTimersByTime(service.timeoutMs);

    expect(onExpired).toHaveBeenCalledTimes(1);
  });

  it('detecta sesión expirada si no existe actividad registrada', () => {
    expect(service.isIdleExpired()).toBe(true);
  });
});
