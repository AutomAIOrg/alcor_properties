// Conversión de un importe en euros a su expresión en letra (español),
// para reproducir la línea "el importe asciende a la cantidad de ..." del recibo.

const UNITS = [
  'cero',
  'uno',
  'dos',
  'tres',
  'cuatro',
  'cinco',
  'seis',
  'siete',
  'ocho',
  'nueve',
  'diez',
  'once',
  'doce',
  'trece',
  'catorce',
  'quince',
  'dieciséis',
  'diecisiete',
  'dieciocho',
  'diecinueve',
  'veinte',
  'veintiuno',
  'veintidós',
  'veintitrés',
  'veinticuatro',
  'veinticinco',
  'veintiséis',
  'veintisiete',
  'veintiocho',
  'veintinueve',
];

const TENS = [
  '',
  '',
  'veinte',
  'treinta',
  'cuarenta',
  'cincuenta',
  'sesenta',
  'setenta',
  'ochenta',
  'noventa',
];

const HUNDREDS = [
  '',
  'ciento',
  'doscientos',
  'trescientos',
  'cuatrocientos',
  'quinientos',
  'seiscientos',
  'setecientos',
  'ochocientos',
  'novecientos',
];

// Apócope de "uno" -> "un" y "veintiuno" -> "veintiún" cuando precede a un
// sustantivo masculino ("un euro") o a "mil" ("veintiún mil").
function apocopate(words: string): string {
  return words.replace(/veintiuno$/, 'veintiún').replace(/(^|\s)uno$/, '$1un');
}

function belowThousand(n: number): string {
  if (n === 0) return '';
  if (n === 100) return 'cien';

  const hundreds = Math.floor(n / 100);
  const rest = n % 100;
  const parts: string[] = [];

  if (hundreds > 0) parts.push(HUNDREDS[hundreds]);

  if (rest > 0) {
    if (rest < 30) {
      parts.push(UNITS[rest]);
    } else {
      const tens = Math.floor(rest / 10);
      const units = rest % 10;
      parts.push(units > 0 ? `${TENS[tens]} y ${UNITS[units]}` : TENS[tens]);
    }
  }

  return parts.join(' ');
}

// Convierte un entero (0..999999) a letra, aplicando la apócope propia de
// contar con sustantivo masculino ("un", "veintiún", "treinta y un mil").
function integerToWords(n: number): string {
  if (n === 0) return 'cero';

  const thousands = Math.floor(n / 1000);
  const rest = n % 1000;
  const parts: string[] = [];

  if (thousands === 1) {
    parts.push('mil');
  } else if (thousands > 1) {
    parts.push(`${apocopate(belowThousand(thousands))} mil`);
  }

  if (rest > 0) parts.push(belowThousand(rest));

  return apocopate(parts.join(' '));
}

/**
 * Expresa un importe en euros en letra, p. ej. 30 -> "treinta euros",
 * 37.5 -> "treinta y siete euros con cincuenta céntimos".
 */
export function amountToSpanishWords(amount: number): string {
  const totalCents = Math.round(Math.abs(amount) * 100);
  const euros = Math.floor(totalCents / 100);
  const cents = totalCents % 100;

  const eurosWords = `${integerToWords(euros)} ${euros === 1 ? 'euro' : 'euros'}`;

  if (cents === 0) return eurosWords;

  const centsWords = `${integerToWords(cents)} ${cents === 1 ? 'céntimo' : 'céntimos'}`;
  return `${eurosWords} con ${centsWords}`;
}
