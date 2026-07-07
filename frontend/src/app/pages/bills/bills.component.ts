import { CurrencyPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { Bill, BillState, BillUpdateStateRequest } from '../../models/bill.model';
import { BookingColorPipe } from '../../pipes/booking-color.pipe';
import { ApartmentService } from '../../services/apartment.service';
import { BillService } from '../../services/bill.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import {
  BillReceiptComponent,
  BillReceiptData,
  billToReceiptData,
} from '../../shared/components/bill-receipt/bill-receipt.component';
import {
  DateRangePickerComponent,
  DateRangeValue,
} from '../../shared/components/date-range-picker/date-range-picker.component';
import {
  allowedBillTransitions,
  billConfirmationMessage,
  billStateRequiresConfirmation,
  billTransitionLabel,
} from '../../shared/utils/bill-transitions';

type ToastType = 'success' | 'error';

interface ToastMessage {
  type: ToastType;
  text: string;
}

interface PendingTransition {
  bill: Bill;
  targetState: BillState;
}

@Component({
  selector: 'app-bills',
  standalone: true,
  imports: [CurrencyPipe, RouterLink, BillReceiptComponent, DateRangePickerComponent],
  templateUrl: './bills.component.html',
  styleUrl: './bills.component.scss',
})
export class BillsComponent implements OnInit, OnDestroy {
  readonly authService = inject(AuthService);
  private billService = inject(BillService);
  private apartmentService = inject(ApartmentService);
  private layout = inject(CalendarLayoutService);
  private colorPipe = new BookingColorPipe();
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;
  private searchRequestId = 0;

  readonly stateOptions: { value: string; label: string }[] = [
    { value: '', label: 'Todos' },
    { value: 'Pendiente', label: 'Pendiente' },
    { value: 'Creada', label: 'Creada' },
    { value: 'Pagada', label: 'Pagada' },
    { value: 'Cancelada', label: 'Cancelada' },
  ];

  bills = signal<Bill[]>([]);
  apartmentIds = signal<string[]>([]);
  isLoading = signal(false);
  loadError = signal<string | null>(null);
  isUpdating = signal(false);
  toast = signal<ToastMessage | null>(null);

  filterApartmentId = signal('');
  filterState = signal('');
  filterDateFrom = signal('');
  filterDateTo = signal('');
  filterCostMin = signal('');
  filterCostMax = signal('');

  billReceiptView = signal<BillReceiptData | null>(null);
  markPaidBill = signal<Bill | null>(null);
  paidAtDate = signal('');
  cancelBill = signal<Bill | null>(null);
  cancelNote = signal('');
  pendingTransition = signal<PendingTransition | null>(null);

  readonly allowedBillTransitions = allowedBillTransitions;
  readonly billTransitionLabel = billTransitionLabel;

  ngOnInit(): void {
    this.apartmentService.getAllApartmentIds().subscribe({
      next: ids => this.apartmentIds.set(ids),
      error: () => this.apartmentIds.set([]),
    });
    this.searchBills();
  }

  ngOnDestroy(): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
      this.toastTimeout = null;
    }
  }

  searchBills(): void {
    const requestId = ++this.searchRequestId;
    this.isLoading.set(true);
    this.loadError.set(null);

    const filters: {
      apartment_id?: string;
      state?: BillState;
      date_from?: string;
      date_to?: string;
      cost_min?: number;
      cost_max?: number;
    } = {};

    if (this.filterApartmentId().trim()) {
      filters.apartment_id = this.filterApartmentId().trim();
    }
    if (this.filterState()) {
      filters.state = this.filterState() as BillState;
    }
    if (this.filterDateFrom()) {
      filters.date_from = this.filterDateFrom();
    }
    if (this.filterDateTo()) {
      filters.date_to = this.filterDateTo();
    }
    const costMin = this.parseOptionalNumber(this.filterCostMin());
    const costMax = this.parseOptionalNumber(this.filterCostMax());
    if (costMin !== null) filters.cost_min = costMin;
    if (costMax !== null) filters.cost_max = costMax;

    this.billService.listBills(filters).subscribe({
      next: bills => {
        if (requestId !== this.searchRequestId) return;
        this.bills.set(bills);
        this.isLoading.set(false);
      },
      error: () => {
        if (requestId !== this.searchRequestId) return;
        this.bills.set([]);
        this.loadError.set('No se han podido cargar las facturas.');
        this.isLoading.set(false);
      },
    });
  }

  clearFilters(): void {
    this.filterApartmentId.set('');
    this.filterState.set('');
    this.filterDateFrom.set('');
    this.filterDateTo.set('');
    this.filterCostMin.set('');
    this.filterCostMax.set('');
    this.searchBills();
  }

  setDateRange(range: DateRangeValue): void {
    this.filterDateFrom.set(range.from);
    this.filterDateTo.set(range.to);
  }

  updateFilterApartmentId(event: Event): void {
    this.filterApartmentId.set((event.target as HTMLInputElement).value);
  }

  updateFilterState(event: Event): void {
    this.filterState.set((event.target as HTMLSelectElement).value);
  }

  updateFilterCostMin(event: Event): void {
    this.filterCostMin.set((event.target as HTMLInputElement).value);
  }

  updateFilterCostMax(event: Event): void {
    this.filterCostMax.set((event.target as HTMLInputElement).value);
  }

  getApartmentColor(apartmentId: string): string {
    return this.colorPipe.transform(apartmentId);
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    const [year, month, day] = iso.split('-');
    return `${day}/${month}/${year}`;
  }

  isPendingBill(bill: Bill): boolean {
    return bill.bill_id === null || bill.state === 'Pendiente';
  }

  canUpdateBill(bill: Bill): boolean {
    return (
      this.authService.hasPermission('bills:update') &&
      bill.bill_id !== null &&
      !this.isPendingBill(bill)
    );
  }

  // Muestra el recibo de una factura ya creada (mismo formato que la
  // previsualización previa al guardado en Organización Limpiezas).
  openBillReceipt(bill: Bill): void {
    const receipt = billToReceiptData(bill, this.layout.toIso(new Date()));
    if (!receipt) {
      this.showToast('error', 'No se ha podido cargar la factura.');
      return;
    }
    this.billReceiptView.set(receipt);
  }

  closeBillReceipt(): void {
    this.billReceiptView.set(null);
  }

  requestTransition(bill: Bill, targetState: BillState): void {
    if (!this.canUpdateBill(bill) || this.isUpdating()) return;

    if (targetState === 'Pagada') {
      this.markPaidBill.set(bill);
      this.paidAtDate.set(this.layout.toIso(new Date()));
      return;
    }

    if (targetState === 'Cancelada') {
      this.cancelBill.set(bill);
      this.cancelNote.set('');
      return;
    }

    if (billStateRequiresConfirmation(targetState)) {
      this.pendingTransition.set({ bill, targetState });
      return;
    }

    this.applyTransition(bill, targetState);
  }

  closeMarkPaidModal(): void {
    if (this.isUpdating()) return;
    this.markPaidBill.set(null);
    this.paidAtDate.set('');
  }

  updatePaidAtDate(event: Event): void {
    this.paidAtDate.set((event.target as HTMLInputElement).value);
  }

  confirmMarkPaid(): void {
    const bill = this.markPaidBill();
    if (!bill?.bill_id || !this.paidAtDate() || this.isUpdating()) return;

    this.applyTransition(bill, 'Pagada', this.paidAtDate());
  }

  closeCancelModal(): void {
    if (this.isUpdating()) return;
    this.cancelBill.set(null);
    this.cancelNote.set('');
  }

  updateCancelNote(event: Event): void {
    this.cancelNote.set((event.target as HTMLTextAreaElement).value);
  }

  confirmCancel(): void {
    const bill = this.cancelBill();
    if (!bill?.bill_id || this.isUpdating()) return;

    this.applyTransition(bill, 'Cancelada', undefined, this.cancelNote().trim());
  }

  closeConfirmDialog(): void {
    if (this.isUpdating()) return;
    this.pendingTransition.set(null);
  }

  confirmPendingTransition(): void {
    const pending = this.pendingTransition();
    if (!pending || this.isUpdating()) return;

    this.applyTransition(pending.bill, pending.targetState);
  }

  confirmationMessage(pending: PendingTransition): string {
    return billConfirmationMessage(
      pending.bill.state,
      pending.targetState,
      pending.bill.bill_id ?? 0
    );
  }

  private applyTransition(
    bill: Bill,
    targetState: BillState,
    paidAt?: string,
    cancellationNote?: string
  ): void {
    if (!bill.bill_id) return;

    this.isUpdating.set(true);

    const payload: BillUpdateStateRequest = { state: targetState };
    if (targetState === 'Pagada' && paidAt) {
      payload.paid_at = paidAt;
    }
    if (targetState === 'Cancelada' && cancellationNote) {
      payload.cancellation_note = cancellationNote;
    }

    this.billService.updateBillState(bill.bill_id, payload).subscribe({
      next: updated => {
        this.bills.update(items =>
          items.map(item => (item.bill_id === updated.bill_id ? updated : item))
        );
        this.isUpdating.set(false);
        this.markPaidBill.set(null);
        this.paidAtDate.set('');
        this.cancelBill.set(null);
        this.cancelNote.set('');
        this.pendingTransition.set(null);
        this.showToast('success', `Factura #${updated.bill_id} actualizada a ${updated.state}.`);
      },
      error: (error: HttpErrorResponse) => {
        this.isUpdating.set(false);
        this.showToast('error', this.resolveUpdateErrorMessage(error));
      },
    });
  }

  private resolveUpdateErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 422) {
      const detail = error.error?.detail;
      if (typeof detail === 'string') return detail;
      return 'Transición de estado no permitida.';
    }
    if (error.status === 404) return 'Factura no encontrada.';
    return 'No se ha podido actualizar la factura.';
  }

  private parseOptionalNumber(value: string): number | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
  }

  private showToast(type: ToastType, text: string): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
    }

    this.toast.set({ type, text });
    this.toastTimeout = setTimeout(() => {
      this.toast.set(null);
      this.toastTimeout = null;
    }, 5000);
  }
}
