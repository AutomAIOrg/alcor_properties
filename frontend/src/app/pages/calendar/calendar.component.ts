// Primitivas de Angular necesarias: Component para definir el componente,
// computed para valores derivados reactivos, inject para inyección de dependencias,
// HostListener para escuchar eventos del documento, OnInit para el ciclo de vida, signal para estado reactivo.
import { Component, computed, effect, HostListener, inject, OnInit, signal } from '@angular/core';
import { BookingService } from '../../services/booking.service';
import { ApartmentService } from '../../services/apartment.service';
import { ApartmentColorService } from '../../services/apartment-color.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import { Booking, BASE_STATUSES } from '../../models/booking.model';
import { CalendarWeek } from '../../models/calendar.model';
import { CalendarHeaderComponent } from './components/calendar-header/calendar-header.component';
import { WeekRowComponent } from './components/week-row/week-row.component';
import { BookingModalComponent } from '../../shared/components/booking-modal/booking-modal.component';
import { BookingCreateModalComponent } from '../../shared/components/booking-create-modal/booking-create-modal.component';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-calendar',
  standalone: true,
  // Todos los subcomponentes y pipes usados en el template deben declararse aquí.
  imports: [
    CalendarHeaderComponent,
    WeekRowComponent,
    BookingModalComponent,
    BookingCreateModalComponent,
  ],
  templateUrl: './calendar.component.html',
  styleUrl: './calendar.component.scss',
})
export class CalendarComponent implements OnInit {
  // Inyección de dependencias: servicios disponibles en toda la clase.
  private bookingService = inject(BookingService);
  private apartmentService = inject(ApartmentService);
  private apartmentColor = inject(ApartmentColorService);
  private layout = inject(CalendarLayoutService);
  authService = inject(AuthService);
  private calendarRequestId = 0;

  // ─── Constantes de etiquetas ────────────────────────────────────────────────
  // Nombres de días para la cabecera del calendario (vista mes/semana).
  readonly WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  // Nombres de días indexados como Date.getDay() (0 = domingo).
  readonly DAYS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  // Nombres de meses indexados como Date.getMonth() (0 = enero).
  readonly MONTHS = [
    'Enero',
    'Febrero',
    'Marzo',
    'Abril',
    'Mayo',
    'Junio',
    'Julio',
    'Agosto',
    'Septiembre',
    'Octubre',
    'Noviembre',
    'Diciembre',
  ];
  // Array [0..23] para iterar las horas en la vista de día/semana.
  readonly HOURS = Array.from({ length: 24 }, (_, i) => i);

  // ─── Estado reactivo (signals) ───────────────────────────────────────────────
  // Vista activa del calendario. Añadir 'day' al union type para activar la vista diaria.
  viewMode = signal<'month' | 'week'>('month'); // signal<'month' | 'week' | 'day'>('month');
  // Fecha de referencia que determina qué mes/semana/día se muestra.
  currentDate = signal(new Date());
  // Reservas cargadas para la ventana visible del calendario.
  bookings = signal<Booking[]>([]);
  calendarLoading = signal(false);
  calendarError = signal<string | null>(null);
  allApartmentIds = signal<string[]>([]);
  apartmentIdsError = signal<string | null>(null);
  private apartmentIdsLoaded = false;
  // Reserva seleccionada que se muestra en el modal de detalle. null = modal cerrado.
  selectedBooking = signal<Booking | null>(null);
  // Controla la visibilidad del modal de creación de reserva.
  showCreateModal = signal(false);
  // Texto del buscador en tiempo real.
  searchQuery = signal('');
  // Controla si el desplegable de sugerencias está visible.
  showSuggestions = signal(false);
  // Reservas resueltas contra el backend (en TODA la base de datos) que coinciden
  // con el texto buscado: huésped, nº de reserva o ID. Se actualiza con debounce.
  searchMatches = signal<Booking[]>([]);
  private searchLookupTimer: ReturnType<typeof setTimeout> | null = null;
  private searchLookupRequestId = 0;

  // ─── Filtros ─────────────────────────────────────────────────────────────────
  // Arrays con los valores seleccionados. Array vacío = sin filtro activo.
  filterBookingIds = signal<string[]>([]);
  filterBookingStates = signal<string[]>([]);

  // Control de apertura de cada panel desplegable.
  showIdDropdown = signal(false);
  showStateDropdown = signal(false);

  // Lista de IDs únicos de reserva para las opciones del filtro.
  bookingIdOptions = computed(() => [...new Set(this.bookings().map(b => b.apartment_id))].sort());

  // Estados posibles — viene del modelo, éditalos en booking.model.ts.
  readonly BASE_STATUSES = BASE_STATUSES;

  // Indica si hay algún filtro activo; se usa para mostrar el botón "Limpiar todo".
  hasActiveFilters = computed(
    () =>
      this.filterBookingIds().length > 0 ||
      this.filterBookingStates().length > 0 ||
      this.searchQuery().trim().length > 0
  );

  // Sugerencias del buscador: reservas (de cualquier mes) que coinciden con el
  // texto, resueltas contra el backend. Solo se muestran si hay texto buscado.
  searchSuggestions = computed(() => (this.searchQuery().trim() ? this.searchMatches() : []));

  // Reservas tras aplicar todos los filtros activos.
  // Este computed es el punto central del filtrado: todos los computeds de vista
  // consumen filteredBookings, así que cualquier filtro nuevo solo requiere
  // añadir su condición aquí.
  private filteredBookings = computed(() => {
    const ids = this.filterBookingIds();
    const states = this.filterBookingStates();
    const query = this.searchQuery().trim().toLowerCase();

    if (!ids.length && !states.length && !query) return this.bookings();

    return this.bookings().filter(b => {
      const matchesId = !ids.length || ids.includes(b.apartment_id);
      const matchesState =
        !states.length || states.some(s => s.toUpperCase() === b.status?.toUpperCase());
      const matchesQuery =
        !query ||
        b.guest_name?.toLowerCase().includes(query) ||
        (b.booking_number?.toLowerCase().includes(query) ?? false) ||
        String(b.record_id).includes(query);

      return matchesId && matchesState && matchesQuery;
    });
  });

  // ─── Computeds de vista ──────────────────────────────────────────────────────
  // Estructura de semanas del mes actual, usada por la vista mensual.
  // buildLaneAssignment calcula en qué "carril" (fila) va cada reserva para
  // que no se solapen visualmente.
  weeks = computed<CalendarWeek[]>(() => {
    const d = this.currentDate();
    const today = this.layout.toIso(new Date());
    const fb = this.filteredBookings();
    return this.layout.buildWeeks(
      d.getFullYear(),
      d.getMonth(),
      fb,
      today,
      this.layout.buildLaneAssignment(fb),
      id => this.apartmentColor.resolve(id)
    );
  });

  // Semana concreta que contiene la fecha actual, usada por la vista semanal.
  currentWeek = computed<CalendarWeek>(() => {
    const iso = this.layout.toIso(this.currentDate());
    return (
      this.weeks().find(w => w.days.some(d => this.layout.toIso(d.date) === iso)) ?? this.weeks()[0]
    );
  });

  // Reservas activas en el día actual (check_in <= hoy <= check_out), usadas
  // por la vista diaria.
  currentDayBookings = computed<Booking[]>(() => {
    const iso = this.layout.toIso(this.currentDate());
    return this.filteredBookings().filter(b => b.check_in <= iso && b.check_out >= iso);
  });

  // ─── Ciclo de vida ───────────────────────────────────────────────────────────

  constructor() {
    // Cuando hay búsqueda activa y ningún resultado es visible en el período actual,
    // navega automáticamente al mes/semana del primer resultado encontrado.
    effect(() => {
      const query = this.searchQuery().trim();
      if (!query) return;

      const matches = this.filteredBookings();
      if (!matches.length) return;

      const cur = this.currentDate();
      const mode = this.viewMode();
      let periodStart: string;
      let periodEnd: string;

      if (mode === 'month') {
        periodStart = this.layout.toIso(new Date(cur.getFullYear(), cur.getMonth(), 1));
        periodEnd = this.layout.toIso(new Date(cur.getFullYear(), cur.getMonth() + 1, 0));
      } else {
        const day = cur.getDay();
        const monday = new Date(cur);
        monday.setDate(cur.getDate() - ((day + 6) % 7));
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        periodStart = this.layout.toIso(monday);
        periodEnd = this.layout.toIso(sunday);
      }

      const visibleInPeriod = matches.some(
        b => b.check_in <= periodEnd && b.check_out >= periodStart
      );

      if (!visibleInPeriod) {
        const first = [...matches].sort((a, b) => a.check_in.localeCompare(b.check_in))[0];
        const d = new Date(first.check_in + 'T00:00:00');
        this.currentDate.set(mode === 'month' ? new Date(d.getFullYear(), d.getMonth(), 1) : d);
      }
    });
  }

  // Se ejecuta una vez al montar el componente: carga solo las reservas visibles.
  ngOnInit(): void {
    this.apartmentColor.ensureLoaded();
    this.loadCalendarBookings();
  }

  // ─── Navegación del calendario ───────────────────────────────────────────────
  // Retrocede un período según la vista activa (mes, semana o día).
  prevPeriod(): void {
    const d = this.currentDate();
    switch (this.viewMode()) {
      case 'month':
        this.currentDate.set(new Date(d.getFullYear(), d.getMonth() - 1, 1));
        break;
      case 'week':
        this.currentDate.set(new Date(d.getFullYear(), d.getMonth(), d.getDate() - 7));
        break;
      // case 'day':   this.currentDate.set(new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1)); break;
    }
    this.loadCalendarBookings();
  }

  // Avanza un período según la vista activa (mes, semana o día).
  nextPeriod(): void {
    const d = this.currentDate();
    switch (this.viewMode()) {
      case 'month':
        this.currentDate.set(new Date(d.getFullYear(), d.getMonth() + 1, 1));
        break;
      case 'week':
        this.currentDate.set(new Date(d.getFullYear(), d.getMonth(), d.getDate() + 7));
        break;
      // case 'day':   this.currentDate.set(new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1)); break;
    }
    this.loadCalendarBookings();
  }

  // Vuelve al mes/semana/día de hoy.
  goToToday(): void {
    this.currentDate.set(new Date());
    this.loadCalendarBookings();
  }

  // Salta directamente a un mes y año concretos (lo emite el calendar-header).
  goToDate(event: { month: number; year: number }): void {
    this.currentDate.set(new Date(event.year, event.month, 1));
    this.loadCalendarBookings();
  }

  changeViewMode(mode: string): void {
    if (mode !== 'month' && mode !== 'week') return;
    if (this.viewMode() === mode) return;

    this.viewMode.set(mode);
    this.loadCalendarBookings();
  }

  openCreateModal(): void {
    this.ensureApartmentIdsLoaded();
    this.showCreateModal.set(true);
  }

  // ─── Métodos de filtro ────────────────────────────────────────────────────────
  // Cierra cada desplegable si el click fue fuera de su propio contenedor.
  @HostListener('document:click', ['$event.target'])
  onDocumentClick(target: HTMLElement): void {
    if (!target.closest('.id-filter-dropdown')) {
      this.showIdDropdown.set(false);
    }
    if (!target.closest('.state-filter-dropdown')) {
      this.showStateDropdown.set(false);
    }
    if (!target.closest('.search-wrapper')) {
      this.showSuggestions.set(false);
    }
  }

  // Añade o quita un apartment_id del filtro activo.
  toggleBookingId(id: string): void {
    this.filterBookingIds.update(ids =>
      ids.includes(id) ? ids.filter(i => i !== id) : [...ids, id]
    );
  }

  // Añade o quita un estado del filtro activo.
  toggleBookingState(state: string): void {
    this.filterBookingStates.update(states =>
      states.includes(state) ? states.filter(s => s !== state) : [...states, state]
    );
  }

  // Limpia todos los filtros a la vez.
  clearAllFilters(): void {
    this.filterBookingIds.set([]);
    this.filterBookingStates.set([]);
    this.searchQuery.set('');
    this.resetSearchLookup();

    this.goToToday();
  }

  // ─── Buscador con autocompletado ──────────────────────────────────────────────
  onSearchInputEvent(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.onSearchInput(input.value);
  }

  onSearchInput(value: string): void {
    this.searchQuery.set(value);
    this.showSuggestions.set(true);
    this.scheduleSearchLookup();
  }

  onSearchFocus(): void {
    if (this.searchSuggestions().length > 0) {
      this.showSuggestions.set(true);
    }
  }

  // Al pulsar Enter, si el texto es un ID exacto de una coincidencia salta a ella;
  // si solo hay una coincidencia, también; si no, deja elegir en el desplegable.
  onSearchEnter(): void {
    const matches = this.searchSuggestions();
    if (!matches.length) return;

    const query = this.searchQuery().trim();
    const exact = matches.find(b => String(b.record_id) === query);
    if (exact) {
      this.goToBooking(exact);
    } else if (matches.length === 1) {
      this.goToBooking(matches[0]);
    }
  }

  // Selecciona una reserva del buscador (huésped, nº de reserva o ID). Deja el
  // ID en el buscador (que filtra el calendario a esa reserva) y sitúa el
  // calendario en el periodo donde cae, aunque esté en otro mes. No abre el modal.
  goToBooking(booking: Booking): void {
    this.showSuggestions.set(false);
    this.resetSearchLookup();
    this.searchQuery.set(String(booking.record_id));

    const checkIn = new Date(booking.check_in + 'T00:00:00');
    this.currentDate.set(
      this.viewMode() === 'month' ? new Date(checkIn.getFullYear(), checkIn.getMonth(), 1) : checkIn
    );
    this.loadCalendarBookings();
  }

  // Resuelve (con debounce) las reservas que coinciden con el texto buscado
  // —huésped, nº de reserva o ID— consultando el backend en TODA la base de
  // datos (no solo el mes visible). Si no hay coincidencias, no aparece nada.
  private scheduleSearchLookup(): void {
    if (this.searchLookupTimer) {
      clearTimeout(this.searchLookupTimer);
      this.searchLookupTimer = null;
    }

    const query = this.searchQuery().trim();
    if (!query) {
      this.searchLookupRequestId += 1;
      this.searchMatches.set([]);
      return;
    }

    const requestId = ++this.searchLookupRequestId;
    this.searchLookupTimer = setTimeout(() => {
      this.bookingService.searchBookings({ search: query, limit: 50 }).subscribe({
        next: bookings => {
          if (requestId === this.searchLookupRequestId) this.searchMatches.set(bookings);
        },
        error: () => {
          if (requestId === this.searchLookupRequestId) this.searchMatches.set([]);
        },
      });
    }, 250);
  }

  // Cancela cualquier búsqueda pendiente y descarta las coincidencias.
  private resetSearchLookup(): void {
    if (this.searchLookupTimer) {
      clearTimeout(this.searchLookupTimer);
      this.searchLookupTimer = null;
    }
    this.searchLookupRequestId += 1;
    this.searchMatches.set([]);
  }

  // ─── Modal de detalle de reserva ─────────────────────────────────────────────
  // Abre el modal asignando la reserva seleccionada.
  openBooking(booking: Booking): void {
    this.selectedBooking.set(booking);
    // Cierra los desplegables de filtro al abrir una reserva.
    this.showIdDropdown.set(false);
    this.showStateDropdown.set(false);
  }

  // Cierra el modal limpiando la selección.
  closeBooking(): void {
    this.selectedBooking.set(null);
  }

  // Recibe la reserva actualizada tras guardar en el modal y actualiza la lista
  // local sin volver a llamar a la API.
  onBookingSaved(updated: Booking): void {
    this.bookings.update(list => list.map(b => (b.record_id === updated.record_id ? updated : b)));
    this.selectedBooking.set(updated);
  }

  // Cierra el modal y recarga la ventana visible tras crear una reserva.
  onBookingCreated(_booking: Booking): void {
    this.showCreateModal.set(false);
    this.loadCalendarBookings();
  }

  formatHour(h: number): string {
    return `${String(h).padStart(2, '0')}:00`;
  }

  isToday(date: Date): boolean {
    return this.layout.toIso(date) === this.layout.toIso(new Date());
  }

  private loadCalendarBookings(): void {
    const { startDate, days } = this.visibleCalendarRange();
    const requestId = ++this.calendarRequestId;

    this.calendarLoading.set(true);
    this.calendarError.set(null);

    this.bookingService.getCalendarBookings(startDate, days).subscribe({
      next: bookings => {
        if (requestId !== this.calendarRequestId) return;

        this.bookings.set(bookings);
        this.calendarLoading.set(false);
      },
      error: () => {
        if (requestId !== this.calendarRequestId) return;

        this.bookings.set([]);
        this.calendarError.set('No se pudieron cargar las reservas del calendario.');
        this.calendarLoading.set(false);
      },
    });
  }

  private visibleCalendarRange(): { startDate: string; days: number } {
    const current = this.currentDate();

    if (this.viewMode() === 'week') {
      const monday = new Date(current);
      monday.setDate(current.getDate() - ((current.getDay() + 6) % 7));

      return {
        startDate: this.layout.toIso(monday),
        days: 7,
      };
    }

    const year = current.getFullYear();
    const month = current.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const leadingDays = (firstDay.getDay() + 6) % 7;
    const visibleDaysBeforePadding = leadingDays + lastDay.getDate();
    const trailingDays = (7 - (visibleDaysBeforePadding % 7)) % 7;
    const gridStart = new Date(year, month, 1 - leadingDays);

    return {
      startDate: this.layout.toIso(gridStart),
      days: visibleDaysBeforePadding + trailingDays,
    };
  }

  private ensureApartmentIdsLoaded(): void {
    if (this.apartmentIdsLoaded) return;

    this.apartmentIdsError.set(null);

    this.apartmentService.getAllApartmentIds().subscribe({
      next: ids => {
        this.allApartmentIds.set(ids);
        this.apartmentIdsLoaded = true;
      },
      error: () => {
        this.allApartmentIds.set([]);
        this.apartmentIdsError.set('No se pudieron cargar los pisos.');
      },
    });
  }
}
