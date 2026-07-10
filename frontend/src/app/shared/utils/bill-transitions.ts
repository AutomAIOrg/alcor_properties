import { BillState } from '../../models/bill.model';

const BILL_TRANSITIONS: Record<BillState, BillState[]> = {
  Pendiente: [],
  // Una factura "Creada" solo puede pasar a "Pagada" (o corregirse con "Rectificar
  // factura", que la mantiene "Creada"). Ya no se cancela.
  Creada: ['Pagada'],
  // "Pagada" es terminal: no admite transiciones. Una factura pagada queda solo para
  // consulta del recibo; no puede revertirse ni modificarse.
  Pagada: [],
  Cancelada: [],
};

export function allowedBillTransitions(state: BillState): BillState[] {
  return BILL_TRANSITIONS[state] ?? [];
}

// Etiqueta visible del estado de una factura:
//  - "Pendiente" (limpieza aún sin facturar) → "Pendiente de facturar".
//  - "Creada" (factura emitida a la espera de cobro) → "Pendiente de pago".
//  - el resto se muestran igual.
export function billStateLabel(state: BillState | string): string {
  if (state === 'Pendiente') return 'Pendiente de facturar';
  if (state === 'Creada') return 'Pendiente de pago';
  return state;
}

export function billTransitionLabel(_currentState: BillState, targetState: BillState): string {
  if (targetState === 'Pagada') return 'Confirmar pago';
  return targetState;
}
