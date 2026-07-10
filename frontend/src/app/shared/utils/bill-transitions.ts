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

// Etiqueta visible del estado de una factura. El valor interno "Creada" (factura emitida
// a la espera de cobro) se muestra como "Pendiente de pago"; el resto se muestran igual.
export function billStateLabel(state: BillState | string): string {
  return state === 'Creada' ? 'Pendiente de pago' : state;
}

export function billTransitionLabel(_currentState: BillState, targetState: BillState): string {
  if (targetState === 'Pagada') return 'Confirmar pago';
  return targetState;
}
