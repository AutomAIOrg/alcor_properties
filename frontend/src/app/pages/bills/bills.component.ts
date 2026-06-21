import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

import { AuthService } from '../../auth/auth.service';
import { Bill, BillCreatePayload, BillSearchFilters } from '../../models/bill.model';
import { BookingColorPipe } from '../../pipes/booking-color.pipe';
import { BillService } from '../../services/bill.service';
import { BillingSettingsService } from '../../services/billing-settings.service';
import { environment } from '../../../environments/environment';

const BILL_STATES = ['Pendiente', 'Creada', 'Pagada', 'Cancelada'] as const;

@Component({
  selector: 'app-bills',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, DecimalPipe, FormsModule, BookingColorPipe],
  templateUrl: './bills.component.html',
  styleUrl: './bills.component.scss',
})
export class BillsComponent implements OnInit {
  private billService = inject(BillService);
  private billingSettings = inject(BillingSettingsService);
  private authService = inject(AuthService);
  private http = inject(HttpClient);
  private searchRequestId = 0;

  readonly STATE_OPTIONS = BILL_STATES;

  // Solo el admin puede cambiar el estado de las facturas (pagar, cancelar, etc.).
  // La limpiadora únicamente puede generar facturas a partir de las pendientes.
  isAdmin = computed(() => this.authService.hasRole('admin'));

  allApartmentIds = signal<string[]>([]);

  filters = {
    apartmentId: signal(''),
    state: signal('Pendiente'),
    dateFrom: signal(''),
    dateTo: signal(''),
    costMin: signal(''),
    costMax: signal(''),
  };

  loading = signal(false);
  error = signal('');
  results = signal<Bill[]>([]);
  hasSearched = signal(false);

  // Acciones de estado
  actionBillId = signal<number | null>(null);
  toast = signal<{ type: 'success' | 'error'; text: string } | null>(null);
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;

  // Modal de pago
  payModalBill = signal<Bill | null>(null);
  payDate = signal('');

  // Modal de generación de factura (a partir de una factura pendiente)
  invoiceBill = signal<Bill | null>(null);
  invoiceDate = signal('');
  invoiceStart = signal('');
  invoiceEnd = signal('');
  invoiceHourlyRate = signal('');
  generating = signal(false);

  // Modal de confirmación genérico
  confirmModal = signal<{ message: string; confirm: () => void } | null>(null);

  ngOnInit(): void {
    this.loadApartmentIds();
    this.search();
  }

  search(): void {
    const requestId = ++this.searchRequestId;

    this.loading.set(true);
    this.error.set('');
    this.results.set([]);
    this.hasSearched.set(true);

    const filters: BillSearchFilters = {};
    if (this.filters.apartmentId()) filters.apartment_id = this.filters.apartmentId();
    if (this.filters.state()) filters.state = this.filters.state();
    if (this.filters.dateFrom()) filters.date_from = this.filters.dateFrom();
    if (this.filters.dateTo()) filters.date_to = this.filters.dateTo();
    if (this.filters.costMin()) filters.cost_min = Number(this.filters.costMin());
    if (this.filters.costMax()) filters.cost_max = Number(this.filters.costMax());

    this.billService.searchBills(filters).subscribe({
      next: bills => {
        if (requestId !== this.searchRequestId) return;
        this.results.set(bills);
        this.loading.set(false);
      },
      error: () => {
        if (requestId !== this.searchRequestId) return;
        this.error.set('No se pudieron cargar las facturas.');
        this.loading.set(false);
      },
    });
  }

  clear(): void {
    this.searchRequestId += 1;
    this.filters.apartmentId.set('');
    this.filters.state.set('');
    this.filters.dateFrom.set('');
    this.filters.dateTo.set('');
    this.filters.costMin.set('');
    this.filters.costMax.set('');
    this.loading.set(false);
    this.results.set([]);
    this.error.set('');
    this.hasSearched.set(false);
  }

  onFilterChange(field: keyof typeof this.filters, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.filters[field].set(value);
    if (this.hasSearched()) this.search();
  }

  onSelectChange(field: keyof typeof this.filters, event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.filters[field].set(value);
    if (this.hasSearched()) this.search();
  }

  totalCost(): number {
    return this.results().reduce((sum, bill) => sum + (bill.cost ?? 0), 0);
  }

  totalHours(): number {
    return this.results().reduce((sum, bill) => sum + bill.clean_hours, 0);
  }

  trackBill(_: number, bill: Bill): string {
    return bill.bill_id != null ? `b${bill.bill_id}` : `p${bill.record_id}`;
  }

  // -------------------------------------------------------------------- //
  // Generación de factura (desde una pendiente)                          //
  // -------------------------------------------------------------------- //

  openInvoiceModal(bill: Bill): void {
    if (bill.record_id == null) return;
    this.invoiceBill.set(bill);
    this.invoiceDate.set(bill.cleaning_date ?? this.todayIso());
    this.invoiceStart.set('10:00');
    this.invoiceEnd.set('12:00');
    this.invoiceHourlyRate.set('');

    // Se carga la tarifa vigente para todos los roles. El admin puede editarla;
    // la limpiadora la ve como solo lectura (el precio por hora que se le pagará).
    this.billingSettings.getCleaningRate().subscribe({
      next: response => this.invoiceHourlyRate.set(String(response.cleaning_hourly_rate)),
      error: () => this.invoiceHourlyRate.set(''),
    });
  }

  closeInvoiceModal(): void {
    if (this.generating()) return;
    this.invoiceBill.set(null);
    this.invoiceDate.set('');
    this.invoiceStart.set('');
    this.invoiceEnd.set('');
    this.invoiceHourlyRate.set('');
  }

  updateInvoiceDate(event: Event): void {
    this.invoiceDate.set((event.target as HTMLInputElement).value);
  }

  updateInvoiceStart(event: Event): void {
    this.invoiceStart.set((event.target as HTMLInputElement).value);
  }

  updateInvoiceEnd(event: Event): void {
    this.invoiceEnd.set((event.target as HTMLInputElement).value);
  }

  updateInvoiceHourlyRate(event: Event): void {
    this.invoiceHourlyRate.set((event.target as HTMLInputElement).value);
  }

  confirmGenerateBill(): void {
    const bill = this.invoiceBill();
    if (!bill || bill.record_id == null || this.generating()) return;

    const date = this.invoiceDate();
    const start = this.invoiceStart();
    const end = this.invoiceEnd();

    if (!date || !start || !end) {
      this.showToast('error', 'Indica la fecha y el horario de la limpieza.');
      return;
    }
    if (end <= start) {
      this.showToast('error', 'La hora de fin debe ser posterior a la de inicio.');
      return;
    }

    this.generating.set(true);

    const payload: BillCreatePayload = {
      record_id: bill.record_id,
      cleaning_date: date,
      start_time: start,
      end_time: end,
    };
    const rate = Number(this.invoiceHourlyRate());
    if (this.invoiceHourlyRate() !== '' && Number.isFinite(rate) && rate >= 0) {
      payload.hourly_rate = rate;
    }

    this.billService.createBill(payload).subscribe({
      next: () => {
        this.generating.set(false);
        this.invoiceBill.set(null);
        this.showToast('success', 'Factura generada.');
        this.search();
      },
      error: (err: { status?: number }) => {
        this.generating.set(false);
        if (err?.status === 409) {
          this.invoiceBill.set(null);
          this.showToast('error', 'Esta limpieza ya tiene una factura.');
          this.search();
          return;
        }
        this.showToast('error', 'No se pudo generar la factura.');
      },
    });
  }

  // -------------------------------------------------------------------- //
  // Cambios de estado (solo admin)                                       //
  // -------------------------------------------------------------------- //

  openPayModal(bill: Bill): void {
    this.payModalBill.set(bill);
    this.payDate.set(this.todayIso());
  }

  closePayModal(): void {
    if (this.actionBillId() !== null) return;
    this.payModalBill.set(null);
    this.payDate.set('');
  }

  updatePayDate(event: Event): void {
    this.payDate.set((event.target as HTMLInputElement).value);
  }

  confirmPay(): void {
    const bill = this.payModalBill();
    if (!bill || bill.bill_id == null) return;
    if (!this.payDate()) {
      this.showToast('error', 'Indica la fecha de pago.');
      return;
    }
    this.changeState(bill, 'Pagada', this.payDate(), () => this.payModalBill.set(null));
  }

  cancelBill(bill: Bill): void {
    this.askConfirm('¿Cancelar esta factura?', () => this.changeState(bill, 'Cancelada'));
  }

  markUnpaid(bill: Bill): void {
    this.askConfirm('¿Cambiar el estado de la factura a "no pagada"?', () =>
      this.changeState(bill, 'Creada')
    );
  }

  reactivate(bill: Bill): void {
    this.changeState(bill, 'Creada');
  }

  askConfirm(message: string, confirm: () => void): void {
    this.confirmModal.set({ message, confirm });
  }

  closeConfirm(): void {
    if (this.actionBillId() !== null) return;
    this.confirmModal.set(null);
  }

  runConfirm(): void {
    const pending = this.confirmModal();
    this.confirmModal.set(null);
    pending?.confirm();
  }

  private changeState(bill: Bill, state: string, paidAt?: string, onSuccess?: () => void): void {
    if (bill.bill_id == null || this.actionBillId() !== null) return;

    this.actionBillId.set(bill.bill_id);

    this.billService
      .updateBillState(bill.bill_id, paidAt ? { state, paid_at: paidAt } : { state })
      .subscribe({
        next: updated => {
          this.results.update(list =>
            list.map(item => (item.bill_id === updated.bill_id ? updated : item))
          );
          this.actionBillId.set(null);
          onSuccess?.();
          this.showToast('success', 'Factura actualizada.');
        },
        error: () => {
          this.actionBillId.set(null);
          this.showToast('error', 'No se pudo actualizar la factura.');
        },
      });
  }

  private showToast(type: 'success' | 'error', text: string): void {
    if (this.toastTimeout) clearTimeout(this.toastTimeout);
    this.toast.set({ type, text });
    this.toastTimeout = setTimeout(() => this.toast.set(null), 4000);
  }

  private todayIso(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
      d.getDate()
    ).padStart(2, '0')}`;
  }

  private loadApartmentIds(): void {
    this.http
      .get<{ apartment_id: string }[]>(`${environment.apiUrl}/api/v1/apartments/`)
      .subscribe({
        next: apartments => {
          const ids = apartments
            .map(a => a.apartment_id)
            .filter(Boolean)
            .sort();
          this.allApartmentIds.set(ids);
        },
      });
  }
}
