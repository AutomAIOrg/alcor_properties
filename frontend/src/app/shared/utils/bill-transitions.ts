import { BillState } from '../../models/bill.model';

const BILL_TRANSITIONS: Record<BillState, BillState[]> = {
  Pendiente: [],
  Creada: ['Pagada', 'Cancelada'],
  Pagada: ['Creada'],
  Cancelada: ['Creada'],
};

export function allowedBillTransitions(state: BillState): BillState[] {
  return BILL_TRANSITIONS[state] ?? [];
}

export function billTransitionLabel(currentState: BillState, targetState: BillState): string {
  if (targetState === 'Pagada') return 'Confirmar pago';
  if (targetState === 'Cancelada') return 'Cancelar';
  if (targetState === 'Creada' && currentState === 'Pagada') return 'Revertir a creada';
  if (targetState === 'Creada' && currentState === 'Cancelada') return 'Reactivar';
  return targetState;
}

export function billStateRequiresConfirmation(targetState: BillState): boolean {
  return targetState === 'Cancelada' || targetState === 'Creada';
}

export function billConfirmationMessage(
  currentState: BillState,
  targetState: BillState,
  billId: number
): string {
  if (targetState === 'Cancelada') {
    return `¿Seguro que deseas cancelar la factura #${billId}?`;
  }
  if (targetState === 'Creada' && currentState === 'Pagada') {
    return `¿Revertir la factura #${billId} a estado Creada?`;
  }
  if (targetState === 'Creada' && currentState === 'Cancelada') {
    return `¿Reactivar la factura #${billId}?`;
  }
  return `¿Confirmar cambio de estado de la factura #${billId}?`;
}
