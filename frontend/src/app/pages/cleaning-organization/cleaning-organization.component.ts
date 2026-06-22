import { Component, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { AuthService } from '../../auth/auth.service';
import { CleaningOpportunity as CleaningOpportunityDto } from '../../models/booking.model';
import { BookingColorPipe } from '../../pipes/booking-color.pipe';
import { BookingService } from '../../services/booking.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';

interface CleaningWindow {
  apartmentId: string;
  availableFromDate: string;
  availableFromTime: string;
  availableUntilDate: string | null;
  availableUntilTime: string;
  comments: string;
  sourceBookingRecordId: number;
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
  templateUrl: './cleaning-organization.component.html',
  styleUrl: './cleaning-organization.component.scss',
})
export class CleaningOrganizationComponent implements OnInit, OnDestroy {
  private bookingService = inject(BookingService);
  private authService = inject(AuthService);
  private layout = inject(CalendarLayoutService);
  private colorPipe = new BookingColorPipe();
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
  toast = signal<ToastMessage | null>(null);
  isAdmin = computed(() => this.authService.hasRole('admin'));

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
  weekLabel = computed(
    () => `${this.formatDate(this.weekStartIso())} - ${this.formatDate(this.weekEndIso())}`
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
    return this.colorPipe.transform(apartmentId);
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
