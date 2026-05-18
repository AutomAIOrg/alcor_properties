import { BookingColorPipe } from './booking-color.pipe';

describe('BookingColorPipe', () => {
  let pipe: BookingColorPipe;

  beforeEach(() => {
    pipe = new BookingColorPipe();
  });

  it('devuelve el mismo color para el mismo booking_id (determinismo)', () => {
    const a = pipe.transform('R180');
    const b = pipe.transform('R180');
    expect(a).toBe(b);
  });

  it('el resultado tiene formato hsl(N, 65%, 42%)', () => {
    const result = pipe.transform('R180');
    expect(result).toMatch(/^hsl\(\d+, 65%, 42%\)$/);
  });

  it('booking_id vacío no lanza excepción y devuelve un string válido', () => {
    expect(() => pipe.transform('')).not.toThrow();
    expect(pipe.transform('')).toMatch(/^hsl\(\d+, 65%, 42%\)$/);
  });
});
