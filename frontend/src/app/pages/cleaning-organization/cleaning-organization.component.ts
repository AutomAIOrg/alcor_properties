import { CurrencyPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { AuthService } from '../../auth/auth.service';
import { CleaningOpportunity as CleaningOpportunityDto } from '../../models/booking.model';
import { CleaningType } from '../../models/cleaning-type.model';
import { ApartmentColorService } from '../../services/apartment-color.service';
import { BillService } from '../../services/bill.service';
import { BookingService } from '../../services/booking.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import { CleaningTypeService } from '../../services/cleaning-type.service';
import {
  BillReceiptComponent,
  BillReceiptData,
  billToReceiptData,
} from '../../shared/components/bill-receipt/bill-receipt.component';
import { DismissableBackdropDirective } from '../../shared/directives/dismissable-backdrop.directive';

interface CleaningWindow {
  apartmentId: string;
  availableFromDate: string;
  availableFromTime: string;
  availableUntilDate: string | null;
  availableUntilTime: string;
  comments: string;
  sourceBookingRecordId: number;
  canBill: boolean;
  hasBill: boolean;
  billState: string | null;
  address: string | null;
}

interface CleaningWeekDay {
  date: Date;
  iso: string;
  label: string;
  isToday: boolean;
}

interface CleaningBar {
  opportunity: CleaningWindow;
  laneIndex: number;
  leftPct: number;
  widthPct: number;
  isStartInWeek: boolean;
  isEndInWeek: boolean;
  top: number;
  color: string;
}

type PendingCleaningBar = Omit<CleaningBar, 'laneIndex' | 'top' | 'color'>;
type ToastType = 'success' | 'error';

interface ToastMessage {
  type: ToastType;
  text: string;
}

@Component({
  selector: 'app-cleaning-organization',
  standalone: true,
  imports: [CurrencyPipe, BillReceiptComponent, DismissableBackdropDirective],
  templateUrl: './cleaning-organization.component.html',
  styleUrl: './cleaning-organization.component.scss',
})
export class CleaningOrganizationComponent implements OnInit, OnDestroy {
  private bookingService = inject(BookingService);
  private billService = inject(BillService);
  private cleaningTypeService = inject(CleaningTypeService);
  private authService = inject(AuthService);
  private layout = inject(CalendarLayoutService);
  private apartmentColor = inject(ApartmentColorService);
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;

  readonly weekdays = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  readonly pendingTime = 'Pendiente';
  readonly barHeight = 22;

  private readonly barGap = 4;
  private readonly dayHeaderHeight = 34;
  private readonly barTopPad = 8;

  currentDate = signal(new Date());
  apiCleaningOpportunities = signal<CleaningOpportunityDto[]>([]);
  isLoading = signal(false);
  loadError = signal<string | null>(null);
  selectedCommentOpportunity = signal<CleaningWindow | null>(null);
  commentDraft = signal('');
  isSavingComment = signal(false);
  selectedInvoiceOpportunity = signal<CleaningWindow | null>(null);
  cleaningDate = signal('');
  startTime = signal('');
  endTime = signal('');
  cleaningTypes = signal<CleaningType[]>([]);
  selectedCleaningTypeId = signal<number | null>(null);
  isLoadingCleaningTypes = signal(false);
  isCreatingBill = signal(false);
  invoiceFormError = signal<string | null>(null);
  showInvoicePreview = signal(false);
  previewEmissionIso = signal('');
  billReceiptView = signal<BillReceiptData | null>(null);
  isLoadingBillReceipt = signal(false);
  toast = signal<ToastMessage | null>(null);
  isAdmin = computed(() => this.authService.hasRole('admin'));
  canCreateBill = computed(() => this.authService.hasPermission('bills:create'));

  selectedCleaningType = computed<CleaningType | null>(() => {
    const id = this.selectedCleaningTypeId();
    if (id === null) return null;
    return this.cleaningTypes().find(type => type.cleaning_type_id === id) ?? null;
  });

  previewHours = computed(() =>
    this.computeHours(this.cleaningDate(), this.startTime(), this.endTime())
  );

  previewCost = computed(() => {
    const hours = this.previewHours();
    const cleaningType = this.selectedCleaningType();
    if (hours === null || cleaningType === null) return null;
    return Math.round(hours * cleaningType.hourly_rate * 100) / 100;
  });

  isInvoiceFormValid = computed(
    () =>
      !!this.cleaningDate() &&
      !!this.startTime() &&
      !!this.endTime() &&
      this.previewHours() !== null &&
      this.selectedCleaningType() !== null
  );

  // Datos del recibo para el paso de previsualización; null mientras el formulario
  // esté incompleto. El formato (semana, importe en letra...) lo resuelve BillReceiptComponent.
  invoiceReceiptData = computed<BillReceiptData | null>(() => {
    const opportunity = this.selectedInvoiceOpportunity();
    const cleaningType = this.selectedCleaningType();
    const hours = this.previewHours();
    const cost = this.previewCost();
    if (!opportunity || !cleaningType || hours === null || cost === null) return null;

    return {
      emissionIso: this.previewEmissionIso(),
      cleaningDateIso: this.cleaningDate(),
      apartmentId: opportunity.apartmentId,
      address: opportunity.address,
      hours,
      hourlyRate: cleaningType.hourly_rate,
      cleaningTypeName: cleaningType.name,
      cost,
      paid: false,
      paidAtIso: null,
      paidConfirmations: [],
    };
  });

  weekDays = computed<CleaningWeekDay[]>(() => {
    const monday = this.getWeekStart(this.currentDate());
    const todayIso = this.layout.toIso(new Date());

    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(monday);
      date.setDate(monday.getDate() + index);

      const iso = this.layout.toIso(date);

      return {
        date,
        iso,
        label: this.weekdays[index],
        isToday: iso === todayIso,
      };
    });
  });

  weekStartIso = computed(() => this.weekDays()[0].iso);
  weekEndIso = computed(() => this.weekDays()[6].iso);
  // Número de semana ISO del año (1..53) de la semana mostrada.
  weekNumber = computed(() => this.layout.isoWeekNumber(this.weekDays()[0].date));
  weekLabel = computed(
    () => `${this.formatDate(this.weekStartIso())} al ${this.formatDate(this.weekEndIso())}`
  );
  currentWeekStartIso = computed(() => this.layout.toIso(this.getWeekStart(new Date())));
  nextWeekStartIso = computed(() => {
    const nextWeekStart = this.getWeekStart(new Date());
    nextWeekStart.setDate(nextWeekStart.getDate() + 7);
    return this.layout.toIso(nextWeekStart);
  });
  canGoPrevWeek = computed(() => this.weekStartIso() > this.currentWeekStartIso());
  canGoNextWeek = computed(() => this.isAdmin() || this.weekStartIso() < this.nextWeekStartIso());

  cleaningOpportunities = computed<CleaningWindow[]>(() =>
    this.apiCleaningOpportunities()
      .filter(opportunity =>
        this.isCleaningWindowVisibleInCurrentWeek(
          opportunity.available_from,
          opportunity.available_until
        )
      )
      .map(opportunity => ({
        apartmentId: opportunity.apartment_id,
        availableFromDate: opportunity.available_from,
        availableFromTime: this.pendingTime,
        availableUntilDate: opportunity.available_until,
        availableUntilTime: this.pendingTime,
        comments: opportunity.comments,
        sourceBookingRecordId: opportunity.source_booking_record_id,
        canBill: opportunity.can_bill,
        hasBill: opportunity.has_bill,
        billState: opportunity.bill_state,
        address: opportunity.address,
      }))
  );

  cleaningBars = computed<CleaningBar[]>(() => {
    const bars = this.cleaningOpportunities()
      .map(opportunity => this.buildCleaningBar(opportunity))
      .filter((bar): bar is PendingCleaningBar => bar !== null)
      .sort(
        (a, b) =>
          a.leftPct - b.leftPct ||
          a.leftPct + a.widthPct - (b.leftPct + b.widthPct) ||
          a.opportunity.apartmentId.localeCompare(b.opportunity.apartmentId)
      );

    const laneEnds: number[] = [];

    return bars.map(bar => {
      let laneIndex = laneEnds.findIndex(end => end <= bar.leftPct);
      if (laneIndex === -1) laneIndex = laneEnds.length;

      laneEnds[laneIndex] = bar.leftPct + bar.widthPct;

      return {
        ...bar,
        laneIndex,
        top: this.barTop(laneIndex),
        color: this.getApartmentColor(bar.opportunity.apartmentId),
      };
    });
  });

  weekGridHeight = computed(() => {
    const totalLanes = this.cleaningBars().reduce(
      (max, bar) => Math.max(max, bar.laneIndex + 1),
      0
    );
    const contentHeight =
      this.dayHeaderHeight + this.barTopPad + totalLanes * (this.barHeight + this.barGap) + 12;

    return Math.max(150, contentHeight);
  });

  ngOnInit(): void {
    // El mapa de colores se sirve desde un endpoint solo-admin. Para limpiadoras
    // (sin acceso) se mantiene el color automático, que es válido por sí solo.
    if (this.isAdmin()) this.apartmentColor.ensureLoaded();
    this.loadBookings();
  }

  ngOnDestroy(): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
      this.toastTimeout = null;
    }
  }

  loadBookings(): void {
    this.isLoading.set(true);
    this.loadError.set(null);

    this.bookingService.getCleaningOpportunities().subscribe({
      next: opportunities => {
        this.apiCleaningOpportunities.set(opportunities);
        this.isLoading.set(false);
      },
      error: () => {
        this.apiCleaningOpportunities.set([]);
        this.loadError.set('No se han podido cargar las reservas para organizar las limpiezas.');
        this.isLoading.set(false);
      },
    });
  }

  prevWeek(): void {
    if (!this.canGoPrevWeek()) return;

    const date = new Date(this.currentDate());
    date.setDate(date.getDate() - 7);
    this.currentDate.set(date);
  }

  nextWeek(): void {
    if (!this.canGoNextWeek()) return;

    const date = new Date(this.currentDate());
    date.setDate(date.getDate() + 7);
    this.currentDate.set(date);
  }

  goToToday(): void {
    this.currentDate.set(new Date());
  }

  formatDate(iso: string | null): string {
    if (!iso) return 'Pendiente';

    const [year, month, day] = iso.split('-');
    return `${day}/${month}/${year}`;
  }

  getApartmentColor(apartmentId: string): string {
    return this.apartmentColor.resolve(apartmentId);
  }

  canGenerateInvoice(opportunity: CleaningWindow): boolean {
    return opportunity.canBill && !opportunity.hasBill;
  }

  openInvoiceModal(opportunity: CleaningWindow): void {
    if (!this.canGenerateInvoice(opportunity)) return;

    this.selectedInvoiceOpportunity.set(opportunity);
    this.cleaningDate.set(this.layout.toIso(new Date()));
    this.startTime.set('');
    this.endTime.set('');
    this.selectedCleaningTypeId.set(null);
    this.invoiceFormError.set(null);
    this.isLoadingCleaningTypes.set(true);

    this.cleaningTypeService.list(true).subscribe({
      next: cleaningTypes => {
        this.cleaningTypes.set(cleaningTypes);
        this.isLoadingCleaningTypes.set(false);
        if (!cleaningTypes.length) {
          this.invoiceFormError.set(
            'No hay tipos de limpieza disponibles. Créalos en el panel de administrador.'
          );
        }
      },
      error: () => {
        this.cleaningTypes.set([]);
        this.isLoadingCleaningTypes.set(false);
        this.invoiceFormError.set('No se han podido cargar los tipos de limpieza.');
      },
    });
  }

  updateSelectedCleaningType(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.selectedCleaningTypeId.set(value ? Number(value) : null);
    this.invoiceFormError.set(null);
  }

  closeInvoiceModal(): void {
    if (this.isCreatingBill()) return;

    this.selectedInvoiceOpportunity.set(null);
    this.cleaningDate.set('');
    this.startTime.set('');
    this.endTime.set('');
    this.cleaningTypes.set([]);
    this.selectedCleaningTypeId.set(null);
    this.invoiceFormError.set(null);
    this.showInvoicePreview.set(false);
    this.previewEmissionIso.set('');
  }

  openInvoicePreview(): void {
    if (this.isCreatingBill() || !this.isInvoiceFormValid()) return;

    if (this.previewHours() === null) {
      this.invoiceFormError.set('La hora de fin debe ser posterior a la hora de inicio.');
      return;
    }

    this.invoiceFormError.set(null);
    this.previewEmissionIso.set(this.layout.toIso(new Date()));
    this.showInvoicePreview.set(true);
  }

  backToInvoiceForm(): void {
    if (this.isCreatingBill()) return;
    this.showInvoicePreview.set(false);
  }

  // Recupera la factura de la limpieza y muestra su recibo (mismo formato
  // que la previsualización previa al guardado).
  openBillReceipt(opportunity: CleaningWindow): void {
    if (!opportunity.hasBill || this.isLoadingBillReceipt()) return;

    this.isLoadingBillReceipt.set(true);
    this.billService.listBills({ apartment_id: opportunity.apartmentId }).subscribe({
      next: bills => {
        this.isLoadingBillReceipt.set(false);
        const bill = bills.find(
          item => item.record_id === opportunity.sourceBookingRecordId && item.bill_id !== null
        );
        const receipt = bill ? billToReceiptData(bill) : null;
        if (!receipt) {
          this.showToast('error', 'No se ha podido cargar la factura.');
          return;
        }
        this.billReceiptView.set(receipt);
      },
      error: () => {
        this.isLoadingBillReceipt.set(false);
        this.showToast('error', 'No se ha podido cargar la factura.');
      },
    });
  }

  closeBillReceipt(): void {
    this.billReceiptView.set(null);
  }

  updateCleaningDate(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.cleaningDate.set(input.value);
    this.invoiceFormError.set(null);
  }

  updateStartTime(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.startTime.set(input.value);
    this.invoiceFormError.set(null);
  }

  updateEndTime(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.endTime.set(input.value);
    this.invoiceFormError.set(null);
  }

  submitInvoice(): void {
    const opportunity = this.selectedInvoiceOpportunity();
    const cleaningType = this.selectedCleaningType();
    if (!opportunity || !cleaningType || this.isCreatingBill() || !this.isInvoiceFormValid())
      return;

    if (this.previewHours() === null) {
      this.invoiceFormError.set('La hora de fin debe ser posterior a la hora de inicio.');
      return;
    }

    this.isCreatingBill.set(true);
    this.invoiceFormError.set(null);

    this.billService
      .createBill({
        record_id: opportunity.sourceBookingRecordId,
        cleaning_date: this.cleaningDate(),
        start_time: this.startTime(),
        end_time: this.endTime(),
        cleaning_type_id: cleaningType.cleaning_type_id,
      })
      .subscribe({
        next: bill => {
          this.apiCleaningOpportunities.update(opportunities =>
            opportunities.map(item =>
              item.source_booking_record_id === opportunity.sourceBookingRecordId
                ? { ...item, has_bill: true, bill_state: bill.state }
                : item
            )
          );
          this.isCreatingBill.set(false);
          this.selectedInvoiceOpportunity.set(null);
          this.showInvoicePreview.set(false);
          this.previewEmissionIso.set('');
          this.showToast(
            'success',
            `Factura creada (${bill.cleaning_type_name}): ${bill.clean_hours} h × ` +
              `${bill.hourly_rate} €/h = ${bill.cost} €`
          );
        },
        error: (error: HttpErrorResponse) => {
          this.isCreatingBill.set(false);
          this.showToast('error', this.resolveInvoiceErrorMessage(error));
        },
      });
  }

  openCommentModal(opportunity: CleaningWindow): void {
    if (!this.isAdmin()) return;

    this.selectedCommentOpportunity.set(opportunity);
    this.commentDraft.set(opportunity.comments);
  }

  closeCommentModal(): void {
    if (this.isSavingComment()) return;

    this.selectedCommentOpportunity.set(null);
    this.commentDraft.set('');
  }

  updateCommentDraft(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    this.commentDraft.set(textarea.value);
  }

  saveComment(): void {
    const opportunity = this.selectedCommentOpportunity();
    if (!opportunity || this.isSavingComment()) return;

    const notesCleaning = this.commentDraft().trim();

    this.isSavingComment.set(true);

    this.bookingService
      .updateBooking(opportunity.sourceBookingRecordId, { notes_cleaning: notesCleaning })
      .subscribe({
        next: updatedBooking => {
          this.apiCleaningOpportunities.update(opportunities =>
            opportunities.map(item =>
              item.source_booking_record_id === updatedBooking.record_id
                ? { ...item, comments: (updatedBooking.notes_cleaning ?? '').trim() }
                : item
            )
          );
          this.isSavingComment.set(false);
          this.selectedCommentOpportunity.set(null);
          this.commentDraft.set('');
          this.showToast('success', 'Comentario guardado con éxito');
        },
        error: () => {
          this.isSavingComment.set(false);
          this.showToast('error', 'Ha fallado al guardar el comentario');
        },
      });
  }

  private resolveInvoiceErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 409) {
      return 'Ya existe una factura para esta reserva.';
    }
    if (error.status === 422) {
      const detail = error.error?.detail;
      if (typeof detail === 'string') return detail;
      return 'Datos de factura inválidos.';
    }
    return 'No se ha podido crear la factura.';
  }

  private computeHours(cleaningDate: string, startTime: string, endTime: string): number | null {
    if (!cleaningDate || !startTime || !endTime) return null;

    const start = new Date(`${cleaningDate}T${startTime}`);
    const end = new Date(`${cleaningDate}T${endTime}`);
    if (end <= start) return null;

    const seconds = (end.getTime() - start.getTime()) / 1000;
    return Math.round((seconds / 3600) * 100) / 100;
  }

  private getWeekStart(date: Date): Date {
    const monday = new Date(date);
    monday.setHours(0, 0, 0, 0);
    monday.setDate(date.getDate() - ((date.getDay() + 6) % 7));
    return monday;
  }

  private isCleaningWindowVisibleInCurrentWeek(
    availableFromDate: string,
    availableUntilDate: string | null
  ): boolean {
    const hasCheckOutInWeek =
      availableFromDate >= this.weekStartIso() && availableFromDate <= this.weekEndIso();
    const hasCheckInInWeek =
      !!availableUntilDate &&
      availableUntilDate >= this.weekStartIso() &&
      availableUntilDate <= this.weekEndIso();

    return hasCheckOutInWeek || hasCheckInInWeek;
  }

  private buildCleaningBar(opportunity: CleaningWindow): PendingCleaningBar | null {
    const weekStart = this.weekStartIso();
    const weekEnd = this.weekEndIso();
    const visibleEnd = opportunity.availableUntilDate ?? weekEnd;

    if (opportunity.availableFromDate > weekEnd || visibleEnd < weekStart) return null;

    const cellPct = 100 / 7;
    const isStartInWeek =
      opportunity.availableFromDate >= weekStart && opportunity.availableFromDate <= weekEnd;
    const isEndInWeek =
      !!opportunity.availableUntilDate &&
      opportunity.availableUntilDate >= weekStart &&
      opportunity.availableUntilDate <= weekEnd;

    const startCol = isStartInWeek
      ? this.weekDays().findIndex(day => day.iso === opportunity.availableFromDate)
      : 0;
    const endCol = isEndInWeek
      ? this.weekDays().findIndex(day => day.iso === opportunity.availableUntilDate)
      : 6;

    if (startCol < 0 || endCol < 0) return null;

    const leftPct = isStartInWeek ? (startCol + 1 / 3) * cellPct : 0;
    const rightPct = isEndInWeek ? (endCol + 2 / 3) * cellPct : 100;
    const widthPct = rightPct - leftPct;

    if (widthPct <= 0) return null;

    return {
      opportunity,
      leftPct,
      widthPct,
      isStartInWeek,
      isEndInWeek,
    };
  }

  private barTop(laneIndex: number): number {
    return this.dayHeaderHeight + this.barTopPad + laneIndex * (this.barHeight + this.barGap);
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
