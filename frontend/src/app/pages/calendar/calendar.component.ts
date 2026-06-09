// Primitivas de Angular necesarias: Component para definir el componente,
// computed para valores derivados reactivos, inject para inyección de dependencias,
// HostListener para escuchar eventos del documento, OnInit para el ciclo de vida, signal para estado reactivo.
import { Component, computed, effect, HostListener, inject, OnInit, signal } from '@angular/core';
import { BookingService } from '../../services/booking.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import { Booking, BASE_STATUSES } from '../../models/booking.model';
import { CalendarWeek } from '../../models/calendar.model';
import { CalendarHeaderComponent } from './components/calendar-header/calendar-header.component';
import { WeekRowComponent } from './components/week-row/week-row.component';
import { BookingModalComponent } from './components/booking-modal/booking-modal.component';
import { BookingCreateModalComponent } from './components/booking-create-modal/booking-create-modal.component';
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
  private layout = inject(CalendarLayoutService);
  authService = inject(AuthService);

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
  // Lista completa de reservas cargadas desde la API.
  bookings = signal<Booking[]>([]);
  // Reserva seleccionada que se muestra en el modal de detalle. null = modal cerrado.
  selectedBooking = signal<Booking | null>(null);
  // Controla la visibilidad del modal de creación de reserva.
  showCreateModal = signal(false);
  // Texto del buscador en tiempo real.
  searchQuery = signal('');
  // Controla si el desplegable de sugerencias está visible.
  showSuggestions = signal(false);

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

  // Sugerencias de autocompletado: nombres de huésped y números de reserva que
  // contienen el texto buscado. Máximo 10 resultados.
  suggestions = computed(() => {
    const query = this.searchQuery().trim().toLowerCase();
    if (!query) return [];

    const results: { text: string; label: string }[] = [];
    const seen = new Set<string>();

    for (const b of this.bookings()) {
      if (b.guest_name && b.guest_name.toLowerCase().includes(query) && !seen.has(b.guest_name)) {
        seen.add(b.guest_name);
        results.push({ text: b.guest_name, label: 'Huésped' });
      }
      if (
        b.booking_number &&
        b.booking_number.toLowerCase().includes(query) &&
        !seen.has(b.booking_number)
      ) {
        seen.add(b.booking_number);
        results.push({ text: b.booking_number, label: 'Nº reserva' });
      }
    }

    return results.slice(0, 10);
  });

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
        (b.booking_number?.toLowerCase().includes(query) ?? false);

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
      this.layout.buildLaneAssignment(fb)
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

  // Se ejecuta una vez al montar el componente: carga todas las reservas desde la API.
  ngOnInit(): void {
    this.bookingService.getBookings().subscribe(bookings => {
      this.bookings.set(bookings);
    });
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
  }

  // Vuelve al mes/semana/día de hoy.
  goToToday(): void {
    this.currentDate.set(new Date());
  }

  // Salta directamente a un mes y año concretos (lo emite el calendar-header).
  goToDate(event: { month: number; year: number }): void {
    this.currentDate.set(new Date(event.year, event.month, 1));
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
  }

  onSearchFocus(): void {
    if (this.suggestions().length > 0) {
      this.showSuggestions.set(true);
    }
  }

  selectSuggestion(text: string): void {
    this.searchQuery.set(text);
    this.showSuggestions.set(false);
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

  // Añade la reserva recién creada a la lista local y cierra el modal.
  onBookingCreated(booking: Booking): void {
    this.bookings.update(list => [...list, booking]);
    this.showCreateModal.set(false);
  }

  formatHour(h: number): string {
    return `${String(h).padStart(2, '0')}:00`;
  }

  isToday(date: Date): boolean {
    return this.layout.toIso(date) === this.layout.toIso(new Date());
  }
}
