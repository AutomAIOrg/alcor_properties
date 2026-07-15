import { CurrencyPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import {
  Bill,
  BillCreateRequest,
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

  // 'unpaid' es un filtro combinado (Pendiente de facturar + Pendiente de pago); es el valor
  // por defecto al entrar. El backend no combina estados en una consulta, así que se resuelve
  // en cliente pidiendo todas y filtrando a los estados Pendiente y Creada.
  private readonly UNPAID_FILTER = 'unpaid';

  readonly stateOptions: { value: string; label: string }[] = [
    { value: this.UNPAID_FILTER, label: 'Pendiente' },
    { value: 'Pendiente', label: 'Pendiente de facturar' },
    { value: 'Creada', label: 'Pendiente de pago' },
    { value: 'Pagada', label: 'Pagada' },
    { value: '', label: 'Todas' },
  ];

  bills = signal<Bill[]>([]);
  apartmentIds = signal<string[]>([]);
  isLoading = signal(false);
  loadError = signal<string | null>(null);
  isUpdating = signal(false);
  toast = signal<ToastMessage | null>(null);

  filterApartmentId = signal('');
  filterState = signal(this.UNPAID_FILTER);
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
  rectifyStartTime = signal('');
  rectifyEndTime = signal('');
  rectifyCleaningTypeId = signal<number | null>(null);

  // Tipo de limpieza seleccionado en el modal de rectificación (para mostrar la tarifa).
  rectifySelectedType = computed<CleaningType | null>(
    () =>
      this.cleaningTypes().find(type => type.cleaning_type_id === this.rectifyCleaningTypeId()) ??
      null
  );

  // Horas derivadas del intervalo inicio–fin, igual que en el modal de crear factura
  // (no se teclean a mano); null si el intervalo no es válido.
  rectifyHours = computed<number | null>(() =>
    this.computeHours(this.rectifyDate(), this.rectifyStartTime(), this.rectifyEndTime())
  );

  // Coste recalculado (horas × tarifa) mientras se rectifica; null si faltan datos válidos.
  rectifyCost = computed<number | null>(() => {
    const hours = this.rectifyHours();
    const type = this.rectifySelectedType();
    if (hours === null || type === null) return null;
    return Math.round(hours * type.hourly_rate * 100) / 100;
  });

  isRectifyValid = computed<boolean>(
    () =>
      !!this.rectifyDate() &&
      !!this.rectifyStartTime() &&
      !!this.rectifyEndTime() &&
      this.rectifyHours() !== null &&
      this.rectifySelectedType() !== null
  );

  // Generación de factura desde la propia página (mismo flujo que Organización Limpiezas):
  // se abre para una factura "Pendiente" (limpieza aún sin facturar).
  creatingBillFor = signal<Bill | null>(null);
  createDate = signal('');
  createStartTime = signal('');
  createEndTime = signal('');
  createCleaningTypeId = signal<number | null>(null);
  createFormError = signal<string | null>(null);
  showCreatePreview = signal(false);
  isCreatingBill = signal(false);
  private createEmissionIso = signal('');

  createSelectedType = computed<CleaningType | null>(
    () =>
      this.cleaningTypes().find(type => type.cleaning_type_id === this.createCleaningTypeId()) ??
      null
  );

  createHours = computed<number | null>(() =>
    this.computeHours(this.createDate(), this.createStartTime(), this.createEndTime())
  );

  createCost = computed<number | null>(() => {
    const hours = this.createHours();
    const type = this.createSelectedType();
    if (hours === null || type === null) return null;
    return Math.round(hours * type.hourly_rate * 100) / 100;
  });

  isCreateFormValid = computed<boolean>(
    () =>
      !!this.createDate() &&
      !!this.createStartTime() &&
      !!this.createEndTime() &&
      this.createHours() !== null &&
      this.createSelectedType() !== null
  );

  // Datos del recibo para el paso de previsualización, construidos desde el formulario
  // (la factura aún no existe); null mientras falten datos válidos.
  createReceiptData = computed<BillReceiptData | null>(() => {
    const opportunity = this.creatingBillFor();
    const type = this.createSelectedType();
    const hours = this.createHours();
    const cost = this.createCost();
    if (!opportunity || !type || hours === null || cost === null) return null;
    return {
      emissionIso: this.createEmissionIso(),
      cleaningDateIso: this.createDate(),
      apartmentId: opportunity.apartment_id,
      address: opportunity.address,
      hours,
      hourlyRate: type.hourly_rate,
      cleaningTypeName: type.name,
      cost,
      paid: false,
      paidAtIso: null,
      paidConfirmations: [],
    };
  });

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

    const stateFilter = this.filterState();
    if (this.filterApartmentId().trim()) {
      filters.apartment_id = this.filterApartmentId().trim();
    }
    // El filtro combinado 'unpaid' ("Pendiente") no se envía al backend: se piden todas y se
    // filtran en cliente a Pendiente de facturar + Pendiente de pago (el backend solo admite
    // un estado por consulta).
    if (stateFilter && stateFilter !== this.UNPAID_FILTER) {
      filters.state = stateFilter as BillState;
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
        this.bills.set(
          stateFilter === this.UNPAID_FILTER
            ? bills.filter(bill => bill.state === 'Pendiente' || bill.state === 'Creada')
            : bills
        );
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
    this.filterState.set(this.UNPAID_FILTER);
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

  // ¿Puede el usuario generar facturas? (mismo permiso que en Organización Limpiezas).
  canCreateBill(): boolean {
    return this.authService.hasPermission('bills:create');
  }

  // Botón "Generar factura" en las filas "Pendiente" (limpieza facturable sin factura real).
  canGenerateBill(bill: Bill): boolean {
    return this.isPendingBill(bill) && bill.record_id !== null && this.canCreateBill();
  }

  openCreateBill(bill: Bill): void {
    if (!this.canGenerateBill(bill) || this.isCreatingBill()) return;
    this.creatingBillFor.set(bill);
    // Fecha de limpieza por defecto: la de la oportunidad (checkout) o, si falta, hoy.
    this.createDate.set(bill.cleaning_date ?? this.layout.toIso(new Date()));
    this.createStartTime.set('');
    this.createEndTime.set('');
    this.createCleaningTypeId.set(null);
    this.showCreatePreview.set(false);
    this.createEmissionIso.set('');
    this.createFormError.set(
      this.cleaningTypes().length
        ? null
        : 'No hay tipos de limpieza disponibles. Créalos en el panel de administrador.'
    );
  }

  closeCreateBill(): void {
    if (this.isCreatingBill()) return;
    this.creatingBillFor.set(null);
    this.createDate.set('');
    this.createStartTime.set('');
    this.createEndTime.set('');
    this.createCleaningTypeId.set(null);
    this.createFormError.set(null);
    this.showCreatePreview.set(false);
    this.createEmissionIso.set('');
  }

  updateCreateDate(event: Event): void {
    this.createDate.set((event.target as HTMLInputElement).value);
    this.createFormError.set(null);
  }

  updateCreateStartTime(event: Event): void {
    this.createStartTime.set((event.target as HTMLInputElement).value);
    this.createFormError.set(null);
  }

  updateCreateEndTime(event: Event): void {
    this.createEndTime.set((event.target as HTMLInputElement).value);
    this.createFormError.set(null);
  }

  updateCreateCleaningType(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.createCleaningTypeId.set(value ? Number(value) : null);
    this.createFormError.set(null);
  }

  openCreatePreview(): void {
    if (this.isCreatingBill() || !this.isCreateFormValid()) return;
    if (this.createHours() === null) {
      this.createFormError.set('La hora de fin debe ser posterior a la hora de inicio.');
      return;
    }
    this.createFormError.set(null);
    this.createEmissionIso.set(this.layout.toIso(new Date()));
    this.showCreatePreview.set(true);
  }

  backToCreateForm(): void {
    if (this.isCreatingBill()) return;
    this.showCreatePreview.set(false);
  }

  submitCreateBill(): void {
    const bill = this.creatingBillFor();
    const type = this.createSelectedType();
    if (!bill?.record_id || !type || this.isCreatingBill() || !this.isCreateFormValid()) return;

    this.isCreatingBill.set(true);
    const payload: BillCreateRequest = {
      record_id: bill.record_id,
      cleaning_date: this.createDate(),
      start_time: this.createStartTime(),
      end_time: this.createEndTime(),
      cleaning_type_id: type.cleaning_type_id,
    };

    this.billService.createBill(payload).subscribe({
      next: created => {
        this.isCreatingBill.set(false);
        this.closeCreateBill();
        this.showToast(
          'success',
          `Factura #${created.bill_id} generada para el piso ${created.apartment_id}.`
        );
        // La fila "Pendiente" pasa a ser una factura real "Pendiente de pago".
        this.searchBills();
      },
      error: (error: HttpErrorResponse) => {
        this.isCreatingBill.set(false);
        this.showCreatePreview.set(false);
        this.createFormError.set(this.resolveCreateErrorMessage(error));
      },
    });
  }

  private resolveCreateErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 422 || error.status === 409) {
      const detail = error.error?.detail;
      if (typeof detail === 'string') return detail;
    }
    return 'No se ha podido generar la factura.';
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

  // Abre el modal de rectificación con los datos actuales de la factura (mismo aspecto que
  // el modal de crear factura). La factura solo almacena el total de horas —no el intervalo
  // original—, así que se reconstruye un tramo desde las 10:00 que produce esas mismas horas
  // para prerrellenar "Hora inicio"/"Hora fin".
  openRectify(bill: Bill): void {
    if (!this.canRectifyBill(bill) || this.isUpdating()) return;
    this.rectifyingBill.set(bill);
    this.rectifyDate.set(bill.cleaning_date ?? '');
    this.rectifyCleaningTypeId.set(bill.cleaning_type_id);
    const hours = bill.clean_hours ?? 0;
    this.rectifyStartTime.set('10:00');
    this.rectifyEndTime.set(this.addHoursToTime('10:00', hours));
  }

  closeRectifyModal(): void {
    if (this.isUpdating()) return;
    this.resetRectify();
  }

  updateRectifyDate(event: Event): void {
    this.rectifyDate.set((event.target as HTMLInputElement).value);
  }

  updateRectifyStartTime(event: Event): void {
    this.rectifyStartTime.set((event.target as HTMLInputElement).value);
  }

  updateRectifyEndTime(event: Event): void {
    this.rectifyEndTime.set((event.target as HTMLInputElement).value);
  }

  updateRectifyCleaningType(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.rectifyCleaningTypeId.set(value ? Number(value) : null);
  }

  confirmRectify(): void {
    const bill = this.rectifyingBill();
    const hours = this.rectifyHours();
    const cleaningTypeId = this.rectifyCleaningTypeId();
    if (
      !bill?.bill_id ||
      this.isUpdating() ||
      !this.isRectifyValid() ||
      hours === null ||
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
    this.rectifyStartTime.set('');
    this.rectifyEndTime.set('');
    this.rectifyCleaningTypeId.set(null);
  }

  // Horas del intervalo inicio–fin (mismo cálculo que el modal de crear factura).
  private computeHours(cleaningDate: string, startTime: string, endTime: string): number | null {
    if (!cleaningDate || !startTime || !endTime) return null;
    const start = new Date(`${cleaningDate}T${startTime}`);
    const end = new Date(`${cleaningDate}T${endTime}`);
    if (end <= start) return null;
    const seconds = (end.getTime() - start.getTime()) / 1000;
    return Math.round((seconds / 3600) * 100) / 100;
  }

  // Suma un número de horas (admite fracciones) a una hora "HH:MM" y devuelve "HH:MM".
  private addHoursToTime(time: string, hours: number): string {
    const [h, m] = time.split(':').map(Number);
    const total = h * 60 + m + Math.round(hours * 60);
    const hh = Math.floor(total / 60) % 24;
    const mm = total % 60;
    return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
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
