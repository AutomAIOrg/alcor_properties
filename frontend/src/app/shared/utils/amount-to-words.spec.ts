import { amountToSpanishWords } from './amount-to-words';

describe('amountToSpanishWords', () => {
  it('convierte importes redondos', () => {
    expect(amountToSpanishWords(0)).toBe('cero euros');
    expect(amountToSpanishWords(1)).toBe('un euro');
    expect(amountToSpanishWords(30)).toBe('treinta euros');
    expect(amountToSpanishWords(21)).toBe('veintiún euros');
    expect(amountToSpanishWords(31)).toBe('treinta y un euros');
    expect(amountToSpanishWords(100)).toBe('cien euros');
    expect(amountToSpanishWords(101)).toBe('ciento un euros');
    expect(amountToSpanishWords(200)).toBe('doscientos euros');
    expect(amountToSpanishWords(500)).toBe('quinientos euros');
  });

  it('convierte miles con apócope correcta', () => {
    expect(amountToSpanishWords(1000)).toBe('mil euros');
    expect(amountToSpanishWords(2000)).toBe('dos mil euros');
    expect(amountToSpanishWords(21000)).toBe('veintiún mil euros');
    expect(amountToSpanishWords(31000)).toBe('treinta y un mil euros');
  });

  it('incluye los céntimos cuando existen', () => {
    expect(amountToSpanishWords(37.5)).toBe('treinta y siete euros con cincuenta céntimos');
    expect(amountToSpanishWords(0.01)).toBe('cero euros con un céntimo');
    expect(amountToSpanishWords(1.21)).toBe('un euro con veintiún céntimos');
  });

  it('redondea a dos decimales', () => {
    expect(amountToSpanishWords(30.004)).toBe('treinta euros');
    expect(amountToSpanishWords(30.005)).toBe('treinta euros con un céntimo');
  });
});
