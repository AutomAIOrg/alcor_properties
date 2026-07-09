import { Component, computed, input } from '@angular/core';
import { Bill } from '../../../models/bill.model';
import { amountToSpanishWords } from '../../utils/amount-to-words';
import {
  PaidConfirmation,
  paidConfirmationSentence,
  paidConfirmationsOf,
} from '../../utils/format-confirmation';

/**
 * Datos necesarios para maquetar el recibo de una limpieza, tanto en la
 * previsualización previa al guardado como al consultar una factura ya creada.
 */
export interface BillReceiptData {
  /** Fecha de emisión del recibo (ISO). */
  emissionIso: string;
  /** Fecha de la limpieza facturada (ISO). */
  cleaningDateIso: string;
  apartmentId: string;
  address: string | null;
  hours: number;
  /** Tarifa €/hora; null si la factura no la tiene registrada. */
  hourlyRate: number | null;
  /** Nombre del tipo de limpieza; null si la factura no lo tiene registrado. */
  cleaningTypeName: string | null;
  cost: number;
  /** True si la factura está pagada (muestra el sello PAGADA). */
  paid: boolean;
  /** Fecha del pago (ISO); null si no está pagada o no consta. */
  paidAtIso: string | null;
  /**
   * Confirmaciones de pago ya registradas (administración y/o limpiadora), en orden.
   * Se muestran aunque la factura aún no esté Pagada (solo una de las dos partes
   * confirmó) y se conservan una vez pagada, como registro de quién confirmó y cuándo.
   */
  paidConfirmations: PaidConfirmation[];
}

/**
 * Construye los datos del recibo a partir de una factura ya creada.
 * Devuelve null para facturas sin datos suficientes (p. ej. virtuales 'Pendiente').
 *
 * La fecha de emisión usa `bill.created_at` (congelada al generar la factura); si una
 * factura anterior a esta funcionalidad no la tiene, se recurre a `cleaning_date` (fecha
 * estable de la propia factura) en vez de al día en que se está consultando el recibo,
 * para que la FECHA no cambie según cuándo se mire.
 */
export function billToReceiptData(bill: Bill): BillReceiptData | null {
  if (bill.bill_id === null || !bill.cleaning_date || bill.cost === null) return null;

  return {
    emissionIso: bill.created_at ?? bill.cleaning_date,
    cleaningDateIso: bill.cleaning_date,
    apartmentId: bill.apartment_id,
    address: bill.address,
    hours: bill.clean_hours,
    hourlyRate: bill.hourly_rate,
    cleaningTypeName: bill.cleaning_type_name,
    cost: bill.cost,
    paid: bill.state === 'Pagada',
    paidAtIso: bill.state === 'Pagada' ? bill.paid_at : null,
    paidConfirmations: paidConfirmationsOf(bill),
  };
}

@Component({
  selector: 'app-bill-receipt',
  standalone: true,
  templateUrl: './bill-receipt.component.html',
  styleUrl: './bill-receipt.component.scss',
})
export class BillReceiptComponent {
  data = input.required<BillReceiptData>();

  emissionLabel = computed(() => this.formatDate(this.data().emissionIso));
  cleaningDateLabel = computed(() => this.formatDate(this.data().cleaningDateIso));

  // Fecha del pago formateada; cadena vacía si no consta.
  paidAtLabel = computed(() => {
    const iso = this.data().paidAtIso;
    return iso ? this.formatDate(iso) : '';
  });

  // Rango de la semana natural (lunes a domingo) que contiene la fecha de limpieza,
  // reproduciendo la anotación "semana del X al Y" del recibo original.
  weekLabel = computed(() => {
    const iso = this.data().cleaningDateIso;
    if (!iso) return '';

    const cleaningDate = new Date(`${iso}T00:00:00`);
    const monday = new Date(cleaningDate);
    monday.setDate(cleaningDate.getDate() - ((cleaningDate.getDay() + 6) % 7));
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    if (monday.getMonth() === sunday.getMonth()) {
      return `del ${monday.getDate()} al ${sunday.getDate()}`;
    }
    return (
      `del ${monday.getDate()}/${monday.getMonth() + 1} ` +
      `al ${sunday.getDate()}/${sunday.getMonth() + 1}`
    );
  });

  // Horas con el formato del recibo: coma decimal y singular/plural (p. ej. "2,5 horas").
  hoursLabel = computed(() => {
    const hours = this.data().hours;
    return `${String(hours).replace('.', ',')} ${hours === 1 ? 'hora' : 'horas'}`;
  });

  // Tarifa con coma decimal (p. ej. "12" o "12,5").
  hourlyRateLabel = computed(() => {
    const rate = this.data().hourlyRate;
    return rate === null ? '' : String(rate).replace('.', ',');
  });

  // Importe total expresado en letra (p. ej. "treinta euros").
  costWords = computed(() => amountToSpanishWords(this.data().cost));

  // Importe total con el formato numérico del recibo (p. ej. "30,00").
  costLabel = computed(() => this.data().cost.toFixed(2).replace('.', ','));

  // Líneas "Pago confirmado por <Nombre Apellidos> el día <fecha> a las <hora>", una
  // por cada parte que ya haya confirmado el pago.
  paidConfirmationLabels = computed(() =>
    this.data().paidConfirmations.map(confirmation =>
      paidConfirmationSentence(confirmation.name, confirmation.datetimeIso)
    )
  );

  private formatDate(iso: string): string {
    if (!iso) return '';
    const [year, month, day] = iso.split('-');
    return `${day}/${month}/${year}`;
  }
}
