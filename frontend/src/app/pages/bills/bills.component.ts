import { CurrencyPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import {
  Bill,
  BillRectifyRequest,
  BillState,
  BillUpdateStateRequest,
} from '../../models/bill.model';
import { CleaningType } from '../../models/cleaning-type.model';
import { BookingColorPipe } from '../../pipes/booking-color.pipe';
import { ApartmentService } from '../../services/apartment.service';
import { BillService } from '../../services/bill.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import { CleaningTypeService } from '../../services/cleaning-type.service';
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
  billStateLabel,
  billTransitionLabel,
} from '../../shared/utils/bill-transitions';
import {
  paidConfirmationSentence,
  paidConfirmationsOf,
} from '../../shared/utils/format-confirmation';
import { DismissableBackdropDirective } from '../../shared/directives/dismissable-backdrop.directive';

type ToastType = 'success' | 'error';

interface ToastMessage {
  type: ToastType;
  text: string;
}

@Component({
  selector: 'app-bills',
  standalone: true,
  imports: [
    CurrencyPipe,
    RouterLink,
    BillReceiptComponent,
    DateRangePickerComponent,
    DismissableBackdropDirective,
  ],
  templateUrl: './bills.component.html',
  styleUrl: './bills.component.scss',
})
export class BillsComponent implements OnInit, OnDestroy {
  readonly authService = inject(AuthService);
  private billService = inject(BillService);
  private apartmentService = inject(ApartmentService);
  private cleaningTypeService = inject(CleaningTypeService);
  private layout = inject(CalendarLayoutService);
  private colorPipe = new BookingColorPipe();
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;
  private searchRequestId = 0;
  private searchDebounce: ReturnType<typeof setTimeout> | null = null;

  readonly stateOptions: { value: string; label: string }[] = [
    { value: '', label: 'Todos' },
    { value: 'Pendiente', label: 'Pendiente' },
    { value: 'Creada', label: 'Pendiente de pago' },
    { value: 'Pagada', label: 'Pagada' },
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

  cleaningTypes = signal<CleaningType[]>([]);
  rectifyingBill = signal<Bill | null>(null);
  rectifyDate = signal('');
  rectifyHours = signal('');
  rectifyCleaningTypeId = signal<number | null>(null);

  // Tipo de limpieza seleccionado en el modal de rectificación (para mostrar la tarifa).
  rectifySelectedType = computed<CleaningType | null>(
    () =>
      this.cleaningTypes().find(type => type.cleaning_type_id === this.rectifyCleaningTypeId()) ??
      null
  );

  // Coste recalculado (horas × tarifa) mientras se rectifica; null si faltan datos válidos.
  rectifyCost = computed<number | null>(() => {
    const hours = this.parseOptionalNumber(this.rectifyHours());
    const type = this.rectifySelectedType();
    if (hours === null || hours <= 0 || type === null) return null;
    return Math.round(hours * type.hourly_rate * 100) / 100;
  });

  isRectifyValid = computed<boolean>(() => this.rectifyCost() !== null && !!this.rectifyDate());

  readonly billTransitionLabel = billTransitionLabel;
  readonly billStateLabel = billStateLabel;

  ngOnInit(): void {
    this.apartmentService.getAllApartmentIds().subscribe({
      next: ids => this.apartmentIds.set(ids),
      error: () => this.apartmentIds.set([]),
    });
    // Tipos de limpieza activos: alimentan el desplegable del modal de rectificación.
    this.cleaningTypeService.list(true).subscribe({
      next: types => this.cleaningTypes.set(types),
      error: () => this.cleaningTypes.set([]),
    });
    this.searchBills();
  }

  ngOnDestroy(): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
      this.toastTimeout = null;
    }
    if (this.searchDebounce) {
      clearTimeout(this.searchDebounce);
      this.searchDebounce = null;
    }
  }

  searchBills(): void {
    if (this.searchDebounce) {
      clearTimeout(this.searchDebounce);
      this.searchDebounce = null;
    }
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
    // Selección discreta de fechas: buscamos de inmediato.
    this.searchBills();
  }

  updateFilterApartmentId(event: Event): void {
    this.filterApartmentId.set((event.target as HTMLInputElement).value);
    this.scheduleSearch();
  }

  updateFilterState(event: Event): void {
    this.filterState.set((event.target as HTMLSelectElement).value);
    // Cambio discreto en el desplegable: buscamos de inmediato.
    this.searchBills();
  }

  updateFilterCostMin(event: Event): void {
    this.filterCostMin.set((event.target as HTMLInputElement).value);
    this.scheduleSearch();
  }

  updateFilterCostMax(event: Event): void {
    this.filterCostMax.set((event.target as HTMLInputElement).value);
    this.scheduleSearch();
  }

  // Búsqueda automática con retardo para los campos de texto/número: evita lanzar
  // una petición por cada pulsación mientras el usuario escribe.
  private scheduleSearch(): void {
    if (this.searchDebounce) {
      clearTimeout(this.searchDebounce);
    }
    this.searchDebounce = setTimeout(() => {
      this.searchDebounce = null;
      this.searchBills();
    }, 400);
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

  // Administración y limpiadora comparten esta página; el modal de confirmación de
  // pago y las transiciones visibles dependen del rol.
  isAdmin(): boolean {
    return this.authService.hasRole('admin');
  }

  // True si el rol del usuario actual ya registró su confirmación de pago.
  // Se usa `!= null` (no `!== null`) para que un campo ausente/undefined —p. ej. una
  // respuesta de un backend aún sin desplegar la doble confirmación— cuente como "sin
  // confirmar" y no oculte por error el botón "Confirmar pago".
  hasConfirmedPaid(bill: Bill): boolean {
    return this.isAdmin()
      ? bill.paid_confirmed_by_admin != null
      : bill.paid_confirmed_by_cleaner != null;
  }

  // Transiciones disponibles para el usuario actual: oculta "Confirmar pago"
  // cuando su parte ya confirmó (falta la confirmación de la otra).
  availableTransitions(bill: Bill): BillState[] {
    return allowedBillTransitions(bill.state).filter(
      targetState => targetState !== 'Pagada' || !this.hasConfirmedPaid(bill)
    );
  }

  // Una línea "Pago confirmado por <Nombre Apellidos> el día <fecha> a las <hora>" por
  // cada parte que ya haya confirmado el pago. Se muestran mientras falte la otra
  // confirmación y se conservan tras completarse el pago, como registro de quién lo
  // confirmó y cuándo.
  paidConfirmationDetails(bill: Bill): string[] {
    return paidConfirmationsOf(bill).map(confirmation =>
      paidConfirmationSentence(confirmation.name, confirmation.datetimeIso)
    );
  }

  // Muestra el recibo de una factura ya creada (mismo formato que la
  // previsualización previa al guardado en Organización Limpiezas).
  openBillReceipt(bill: Bill): void {
    const receipt = billToReceiptData(bill);
    if (!receipt) {
      this.showToast('error', 'No se ha podido cargar la factura.');
      return;
    }
    this.billReceiptView.set(receipt);
  }

  closeBillReceipt(): void {
    this.billReceiptView.set(null);
  }

  // Una factura "Creada" puede corregirse sin cancelarla: "Rectificar factura" abre un
  // modal para cambiar fecha, horas y tipo de limpieza; el coste se recalcula y la
  // factura sigue "Creada".
  canRectifyBill(bill: Bill): boolean {
    return this.canUpdateBill(bill) && bill.state === 'Creada';
  }

  requestTransition(bill: Bill, targetState: BillState): void {
    if (!this.canUpdateBill(bill) || this.isUpdating()) return;

    if (targetState === 'Pagada') {
      this.markPaidBill.set(bill);
      // La fecha de pago solo la declara la limpiadora (por defecto, hoy);
      // administración únicamente confirma.
      this.paidAtDate.set(this.isAdmin() ? '' : this.layout.toIso(new Date()));
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
    if (!bill?.bill_id || this.isUpdating()) return;

    // Administración solo confirma: no envía fecha de pago (el backend la ignoraría).
    if (this.isAdmin()) {
      this.applyTransition(bill, 'Pagada');
      return;
    }

    if (!this.paidAtDate()) return;
    this.applyTransition(bill, 'Pagada', this.paidAtDate());
  }

  // Abre el modal de rectificación con los datos actuales de la factura.
  openRectify(bill: Bill): void {
    if (!this.canRectifyBill(bill) || this.isUpdating()) return;
    this.rectifyingBill.set(bill);
    this.rectifyDate.set(bill.cleaning_date ?? '');
    this.rectifyHours.set(bill.clean_hours != null ? String(bill.clean_hours) : '');
    this.rectifyCleaningTypeId.set(bill.cleaning_type_id);
  }

  closeRectifyModal(): void {
    if (this.isUpdating()) return;
    this.resetRectify();
  }

  updateRectifyDate(event: Event): void {
    this.rectifyDate.set((event.target as HTMLInputElement).value);
  }

  updateRectifyHours(event: Event): void {
    this.rectifyHours.set((event.target as HTMLInputElement).value);
  }

  updateRectifyCleaningType(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.rectifyCleaningTypeId.set(value ? Number(value) : null);
  }

  confirmRectify(): void {
    const bill = this.rectifyingBill();
    const hours = this.parseOptionalNumber(this.rectifyHours());
    const cleaningTypeId = this.rectifyCleaningTypeId();
    if (
      !bill?.bill_id ||
      this.isUpdating() ||
      !this.rectifyDate() ||
      hours === null ||
      hours <= 0 ||
      cleaningTypeId === null
    ) {
      return;
    }

    this.isUpdating.set(true);
    const payload: BillRectifyRequest = {
      cleaning_date: this.rectifyDate(),
      clean_hours: hours,
      cleaning_type_id: cleaningTypeId,
    };

    this.billService.rectifyBill(bill.bill_id, payload).subscribe({
      next: updated => {
        this.bills.update(items =>
          items.map(item => (item.bill_id === updated.bill_id ? updated : item))
        );
        this.isUpdating.set(false);
        this.resetRectify();
        this.showToast('success', `Factura #${updated.bill_id} rectificada.`);
      },
      error: (error: HttpErrorResponse) => {
        this.isUpdating.set(false);
        this.showToast('error', this.resolveUpdateErrorMessage(error));
      },
    });
  }

  private resetRectify(): void {
    this.rectifyingBill.set(null);
    this.rectifyDate.set('');
    this.rectifyHours.set('');
    this.rectifyCleaningTypeId.set(null);
  }

  private applyTransition(bill: Bill, targetState: BillState, paidAt?: string): void {
    if (!bill.bill_id) return;

    this.isUpdating.set(true);

    const payload: BillUpdateStateRequest = { state: targetState };
    if (targetState === 'Pagada' && paidAt) {
      payload.paid_at = paidAt;
    }

    this.billService.updateBillState(bill.bill_id, payload).subscribe({
      next: updated => {
        this.bills.update(items =>
          items.map(item => (item.bill_id === updated.bill_id ? updated : item))
        );
        this.isUpdating.set(false);
        this.markPaidBill.set(null);
        this.paidAtDate.set('');
        // Si se confirmó el pago pero la factura sigue Creada, falta la otra parte.
        if (targetState === 'Pagada' && updated.state !== 'Pagada') {
          this.showToast(
            'success',
            `Pago de la factura #${updated.bill_id} confirmado. ` +
              'Pasará a Pagada cuando confirme la otra parte.'
          );
          return;
        }
        this.showToast(
          'success',
          `Factura #${updated.bill_id} actualizada a ${billStateLabel(updated.state)}.`
        );
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
