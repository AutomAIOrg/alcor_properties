// Primitivas de Angular necesarias: Component para definir el componente,
// computed para valores derivados reactivos, inject para inyección de dependencias,
// HostListener para escuchar eventos del documento, OnInit para el ciclo de vida, signal para estado reactivo.
import { Component, computed, HostListener, inject, OnInit, signal } from '@angular/core';
// Servicio que comunica con la API REST para leer y actualizar reservas.
import { BookingService } from '../../services/booking.service';
// Servicio con utilidades de cálculo del calendario (semanas, carriles, fechas ISO).
import { CalendarLayoutService } from '../../services/calendar-layout.service';
// Tipos de datos: Booking representa una reserva, CalendarWeek una fila de semana.
import { Booking, BASE_STATUSES } from '../../models/booking.model';
import { CalendarWeek } from '../../models/calendar.model';
// Pipe que asigna un color a cada reserva según su booking_id.
import { BookingColorPipe } from '../../pipes/booking-color.pipe';
// Subcomponentes visuales del calendario.
import { CalendarHeaderComponent } from './components/calendar-header/calendar-header.component';
import { WeekRowComponent } from './components/week-row/week-row.component';
import { BookingModalComponent } from './components/booking-modal/booking-modal.component';
import { BookingCreateModalComponent } from './components/booking-create-modal/booking-create-modal.component';

@Component({
  selector: 'app-calendar',
  standalone: true,
  // Todos los subcomponentes y pipes usados en el template deben declararse aquí.
  imports: [CalendarHeaderComponent, WeekRowComponent, BookingModalComponent, BookingCreateModalComponent, BookingColorPipe],
  templateUrl: './calendar.component.html',
  styleUrl: './calendar.component.scss'
})
export class CalendarComponent implements OnInit {

  // Inyección de dependencias: servicios disponibles en toda la clase.
  private bookingService = inject(BookingService);
  private layout         = inject(CalendarLayoutService);

  // ─── Constantes de etiquetas ────────────────────────────────────────────────
  // Nombres de días para la cabecera del calendario (vista mes/semana).
  readonly WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  // Nombres de días indexados como Date.getDay() (0 = domingo).
  readonly DAYS     = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  // Nombres de meses indexados como Date.getMonth() (0 = enero).
  readonly MONTHS   = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];
  // Array [0..23] para iterar las horas en la vista de día/semana.
  readonly HOURS = Array.from({ length: 24 }, (_, i) => i);

  // ─── Estado reactivo (signals) ───────────────────────────────────────────────
  // Vista activa del calendario. Añadir 'day' al union type para activar la vista diaria.
  viewMode        = signal<'month' | 'week'>('month'); // signal<'month' | 'week' | 'day'>('month');
  // Fecha de referencia que determina qué mes/semana/día se muestra.
  currentDate     = signal(new Date());
  // Lista completa de reservas cargadas desde la API.
  bookings        = signal<Booking[]>([]);
  // Reserva seleccionada que se muestra en el modal de detalle. null = modal cerrado.
  selectedBooking = signal<Booking | null>(null);
  // Controla la visibilidad del modal de creación de reserva.
  showCreateModal = signal(false);

  // ─── Filtros ─────────────────────────────────────────────────────────────────
  // Arrays con los valores seleccionados. Array vacío = sin filtro activo.
  filterBookingIds    = signal<string[]>([]);
  filterBookingStates = signal<string[]>([]);

  // Control de apertura de cada panel desplegable.
  showIdDropdown    = signal(false);
  showStateDropdown = signal(false);

  // Lista de IDs únicos de reserva para las opciones del filtro.
  bookingIdOptions = computed(() =>
    [...new Set(this.bookings().map(b => b.booking_id))].sort()
  );

  // Estados posibles — viene del modelo, éditalos en booking.model.ts.
  readonly BASE_STATUSES = BASE_STATUSES;

  // Indica si hay algún filtro activo; se usa para mostrar el botón "Limpiar todo".
  hasActiveFilters = computed(() =>
    this.filterBookingIds().length > 0 || this.filterBookingStates().length > 0
  );

  // Reservas tras aplicar todos los filtros activos.
  // Este computed es el punto central del filtrado: todos los computeds de vista
  // consumen filteredBookings, así que cualquier filtro nuevo solo requiere
  // añadir su condición aquí.
  private filteredBookings = computed(() => {
    const ids    = this.filterBookingIds();
    const states = this.filterBookingStates();

    // Si no hay filtros activos, devolvemos todas las reservas sin crear un nuevo array.
    if (!ids.length && !states.length) return this.bookings();

    return this.bookings().filter(b => {
      // Comprobamos el ID (debe estar entre los seleccionados)
      const matchesId    = !ids.length    || ids.includes(b.booking_id);
      // Comprobamos el Estado (comparación sin distinción de mayúsculas)
      const matchesState = !states.length || states.some(s => s.toUpperCase() === b.status?.toUpperCase());

      // Se devuelve true si la reserva cumple ambas condiciones
      return matchesId && matchesState;
    });
  });

  // ─── Computeds de vista ──────────────────────────────────────────────────────
  // Estructura de semanas del mes actual, usada por la vista mensual.
  // buildLaneAssignment calcula en qué "carril" (fila) va cada reserva para
  // que no se solapen visualmente.
  weeks = computed<CalendarWeek[]>(() => {
    const d     = this.currentDate();
    const today = this.layout.toIso(new Date());
    const fb    = this.filteredBookings();
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
    return this.weeks().find(w =>
      w.days.some(d => this.layout.toIso(d.date) === iso)
    ) ?? this.weeks()[0];
  });

  // Reservas activas en el día actual (check_in <= hoy <= check_out), usadas
  // por la vista diaria.
  currentDayBookings = computed<Booking[]>(() => {
    const iso = this.layout.toIso(this.currentDate());
    return this.filteredBookings().filter(b =>
      b.check_in <= iso && b.check_out >= iso
    );
  });

  // ─── Ciclo de vida ───────────────────────────────────────────────────────────
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
      case 'month': this.currentDate.set(new Date(d.getFullYear(), d.getMonth() - 1, 1)); break;
      case 'week':  this.currentDate.set(new Date(d.getFullYear(), d.getMonth(), d.getDate() - 7)); break;
      // case 'day':   this.currentDate.set(new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1)); break;
    }
  }

  // Avanza un período según la vista activa (mes, semana o día).
  nextPeriod(): void {
    const d = this.currentDate();
    switch (this.viewMode()) {
      case 'month': this.currentDate.set(new Date(d.getFullYear(), d.getMonth() + 1, 1)); break;
      case 'week':  this.currentDate.set(new Date(d.getFullYear(), d.getMonth(), d.getDate() + 7)); break;
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
  // Cierra ambos desplegables si el click fue fuera de un .filter-dropdown.
  @HostListener('document:click', ['$event.target'])
  onDocumentClick(target: HTMLElement): void {
    if (!target.closest('.filter-dropdown')) {
      this.showIdDropdown.set(false);
      this.showStateDropdown.set(false);
    }
  }

  // Añade o quita un booking_id del filtro activo.
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
    this.bookings.update(list =>
      list.map(b => b.record_id === updated.record_id ? updated : b)
    );
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