import { formatConfirmationDateTime, paidConfirmationSentence } from './format-confirmation';

describe('formatConfirmationDateTime', () => {
  it('formatea un datetime ISO como "DD/MM/YYYY a las HH:MM"', () => {
    expect(formatConfirmationDateTime('2026-07-08T14:30:00')).toBe('08/07/2026 a las 14:30');
  });

  it('muestra solo la fecha si no llega la hora (dato histórico)', () => {
    expect(formatConfirmationDateTime('2026-07-08')).toBe('08/07/2026');
  });

  it('devuelve cadena vacía si la entrada está vacía', () => {
    expect(formatConfirmationDateTime('')).toBe('');
  });
});

describe('paidConfirmationSentence', () => {
  it('construye la frase completa con nombre, fecha y hora', () => {
    expect(paidConfirmationSentence('Daniel Jones', '2026-07-08T09:05:00')).toBe(
      'Pago confirmado por Daniel Jones el día 08/07/2026 a las 09:05'
    );
  });
});
