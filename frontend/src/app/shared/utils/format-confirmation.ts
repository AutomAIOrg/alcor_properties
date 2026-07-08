import { Bill } from '../../models/bill.model';

/** Confirmación de pago ya registrada: quién (nombre congelado) y cuándo (ISO con hora). */
export interface PaidConfirmation {
  name: string;
  datetimeIso: string;
}

// Confirmaciones de pago registradas en la factura (administración y/o limpiadora, en ese
// orden). Única fuente de esta derivación para el listado de facturas y el recibo.
export function paidConfirmationsOf(bill: Bill): PaidConfirmation[] {
  const confirmations: PaidConfirmation[] = [];
  if (bill.paid_confirmed_by_admin && bill.paid_confirmed_by_admin_name) {
    confirmations.push({
      name: bill.paid_confirmed_by_admin_name,
      datetimeIso: bill.paid_confirmed_by_admin,
    });
  }
  if (bill.paid_confirmed_by_cleaner && bill.paid_confirmed_by_cleaner_name) {
    confirmations.push({
      name: bill.paid_confirmed_by_cleaner_name,
      datetimeIso: bill.paid_confirmed_by_cleaner,
    });
  }
  return confirmations;
}

// Formatea el instante de una confirmación de pago (ISO datetime del backend, p. ej.
// "2026-07-08T14:30:00") como "DD/MM/YYYY a las HH:MM". Se parsea a mano por componentes
// para no depender de la zona horaria del navegador. Si solo llega la fecha (dato
// histórico sin hora), se muestra únicamente la fecha.
export function formatConfirmationDateTime(iso: string): string {
  if (!iso) return '';

  const [datePart, timePart = ''] = iso.split('T');
  const [year, month, day] = datePart.split('-');
  if (!year || !month || !day) return '';

  const dateLabel = `${day}/${month}/${year}`;
  const [hour, minute] = timePart.split(':');
  return hour && minute ? `${dateLabel} a las ${hour}:${minute}` : dateLabel;
}

// Frase completa "Pago confirmado por <Nombre> el día <fecha> a las <hora>".
export function paidConfirmationSentence(name: string, iso: string): string {
  return `Pago confirmado por ${name} el día ${formatConfirmationDateTime(iso)}`;
}
