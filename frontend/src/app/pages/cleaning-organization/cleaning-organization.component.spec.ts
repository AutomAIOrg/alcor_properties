import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';

import { CleaningOrganizationComponent } from './cleaning-organization.component';
import { AuthService } from '../../auth/auth.service';
import { Bill } from '../../models/bill.model';
import { Booking, CleaningOpportunity as CleaningOpportunityDto } from '../../models/booking.model';
import { CleaningType } from '../../models/cleaning-type.model';
import { BillService } from '../../services/bill.service';
import { ApartmentService } from '../../services/apartment.service';
import { BookingService } from '../../services/booking.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import { CleaningTypeService } from '../../services/cleaning-type.service';

function makeCleaningOpportunity(
  overrides: Partial<CleaningOpportunityDto> = {}
): CleaningOpportunityDto {
  return {
    source_booking_record_id: 1,
    apartment_id: 'R180',
    available_from: '2026-06-02',
    available_until: null,
    comments: '',
    can_bill: false,
    has_bill: false,
    bill_state: null,
    ...overrides,
  };
}

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R180',
    guest_name: 'Ana García',
    check_in: '2026-05-30',
    check_out: '2026-06-02',
    status: 'Confirmed',
    nights: 3,
    persons: 2,
    adults: 2,
    children: 0,
    price: null,
    charges: null,
    electric_allowance: null,
    email: null,
    phone: null,
    booking_number: null,
    notes: null,
    notes_cleaning: null,
    ...overrides,
  };
}

function makeBill(overrides: Partial<Bill> = {}): Bill {
  return {
    bill_id: 10,
    record_id: 1,
    apartment_id: 'R180',
    cleaning_date: '2026-06-02',
    clean_hours: 2,
    cost: 30,
    hourly_rate: 15,
    cleaning_type_id: 1,
    cleaning_type_name: 'Limpieza normal',
    state: 'Creada',
    paid_at: null,
    cancellation_note: null,
    previously_cancelled: false,
    ...overrides,
  };
}

function makeCleaningType(overrides: Partial<CleaningType> = {}): CleaningType {
  return {
    cleaning_type_id: 1,
    name: 'Limpieza normal',
    hourly_rate: 15,
    active: true,
    ...overrides,
  };
}

describe('CleaningOrganizationComponent', () => {
  let fixture: ComponentFixture<CleaningOrganizationComponent>;
  let component: CleaningOrganizationComponent;
  let bookingServiceSpy: jest.Mocked<BookingService>;
  let billServiceSpy: jest.Mocked<BillService>;
  let cleaningTypeServiceSpy: jest.Mocked<CleaningTypeService>;
  let authServiceSpy: jest.Mocked<AuthService>;

  function setup(
    opportunities: CleaningOpportunityDto[] = [],
    isAdmin = false,
    canCreateBill = true
  ): void {
    bookingServiceSpy = {
      getCleaningOpportunities: jest.fn().mockReturnValue(of(opportunities)),
      updateBooking: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;

    billServiceSpy = {
      createBill: jest.fn(),
    } as unknown as jest.Mocked<BillService>;

    cleaningTypeServiceSpy = {
      list: jest.fn().mockReturnValue(of([makeCleaningType()])),
    } as unknown as jest.Mocked<CleaningTypeService>;

    authServiceSpy = {
      hasRole: jest.fn().mockReturnValue(isAdmin),
      hasPermission: jest.fn().mockImplementation((permission: string) => {
        if (permission === 'bills:create') return canCreateBill;
        return true;
      }),
    } as unknown as jest.Mocked<AuthService>;

    TestBed.configureTestingModule({
      imports: [CleaningOrganizationComponent],
      providers: [
        { provide: BookingService, useValue: bookingServiceSpy },
        { provide: BillService, useValue: billServiceSpy },
        { provide: CleaningTypeService, useValue: cleaningTypeServiceSpy },
        { provide: AuthService, useValue: authServiceSpy },
        {
          provide: ApartmentService,
          useValue: { getAllApartments: jest.fn().mockReturnValue(of([])) },
        },
        CalendarLayoutService,
      ],
    });

    fixture = TestBed.createComponent(CleaningOrganizationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  beforeEach(() => {
    TestBed.resetTestingModule();
  });

  it('carga las oportunidades de limpieza al iniciar', () => {
    setup([makeCleaningOpportunity()]);

    expect(bookingServiceSpy.getCleaningOpportunities).toHaveBeenCalledTimes(1);
    expect(component.apiCleaningOpportunities().length).toBe(1);
  });

  it('construye una semana de lunes a domingo', () => {
    setup();

    component.currentDate.set(new Date(2026, 5, 3));

    expect(component.weekDays().map(day => day.iso)).toEqual([
      '2026-06-01',
      '2026-06-02',
      '2026-06-03',
      '2026-06-04',
      '2026-06-05',
      '2026-06-06',
      '2026-06-07',
    ]);
  });

  it('limita la navegación de limpiadora a la semana actual y la siguiente', () => {
    setup([], false);

    const currentWeek = component.weekStartIso();

    expect(component.canGoPrevWeek()).toBe(false);
    expect(component.canGoNextWeek()).toBe(true);

    component.prevWeek();
    expect(component.weekStartIso()).toBe(currentWeek);

    component.nextWeek();
    const nextWeek = component.weekStartIso();
    expect(nextWeek).not.toBe(currentWeek);
    expect(component.canGoPrevWeek()).toBe(true);
    expect(component.canGoNextWeek()).toBe(false);

    component.nextWeek();
    expect(component.weekStartIso()).toBe(nextWeek);
  });

  it('permite a admin avanzar semanas pero no retroceder antes de la actual', () => {
    setup([], true);

    const currentWeek = component.weekStartIso();

    expect(component.canGoPrevWeek()).toBe(false);
    expect(component.canGoNextWeek()).toBe(true);

    component.prevWeek();
    expect(component.weekStartIso()).toBe(currentWeek);

    component.nextWeek();
    component.nextWeek();
    expect(component.weekStartIso()).not.toBe(currentWeek);
    expect(component.canGoPrevWeek()).toBe(true);
  });

  it('filtra ventanas visibles en la semana seleccionada', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        comments: 'Llevar llaves',
      }),
      makeCleaningOpportunity({
        source_booking_record_id: 2,
        apartment_id: 'R181',
        available_from: '2026-06-20',
        available_until: '2026-06-25',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));

    expect(component.cleaningOpportunities()).toEqual([
      {
        apartmentId: 'R180',
        availableFromDate: '2026-06-02',
        availableFromTime: 'Pendiente',
        availableUntilDate: '2026-06-05',
        availableUntilTime: 'Pendiente',
        comments: 'Llevar llaves',
        sourceBookingRecordId: 1,
        canBill: false,
        hasBill: false,
        billState: null,
      },
    ]);
  });

  it('calcula barras semanales desde la fecha disponible hasta la fecha límite', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: '2026-06-05',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));

    const [bar] = component.cleaningBars();

    expect(bar.opportunity.apartmentId).toBe('R180');
    expect(bar.isStartInWeek).toBe(true);
    expect(bar.isEndInWeek).toBe(true);
    expect(bar.laneIndex).toBe(0);
    expect(bar.leftPct).toBeCloseTo(19.047, 2);
    expect(bar.widthPct).toBeCloseTo(47.619, 2);
  });

  it('continúa la barra en la semana del check-in si el check-out fue en una semana anterior', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: '2026-06-10',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 10));

    const [bar] = component.cleaningBars();

    expect(component.cleaningOpportunities()[0].availableFromDate).toBe('2026-06-02');
    expect(component.cleaningOpportunities()[0].availableUntilDate).toBe('2026-06-10');
    expect(bar.isStartInWeek).toBe(false);
    expect(bar.isEndInWeek).toBe(true);
    expect(bar.leftPct).toBe(0);
    expect(bar.widthPct).toBeCloseTo(38.095, 2);
  });

  it('oculta ventanas de limpieza en semanas intermedias sin check-out ni check-in', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: '2026-06-18',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 10));

    expect(component.cleaningOpportunities()).toEqual([]);
    expect(component.cleaningBars()).toEqual([]);
  });

  it('no repite indefinidamente limpiezas sin siguiente check-in en semanas futuras', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: null,
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 10));

    expect(component.cleaningOpportunities()).toEqual([]);
    expect(component.cleaningBars()).toEqual([]);
  });

  it('asigna el mismo color a barras del mismo piso y colores distintos a pisos diferentes', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-01',
        available_until: '2026-06-03',
      }),
      makeCleaningOpportunity({
        source_booking_record_id: 2,
        apartment_id: 'R180',
        available_from: '2026-06-03',
        available_until: '2026-06-07',
      }),
      makeCleaningOpportunity({
        source_booking_record_id: 3,
        apartment_id: 'R181',
        available_from: '2026-06-02',
        available_until: '2026-06-06',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));

    const bars = component.cleaningBars();
    const r180Bars = bars.filter(bar => bar.opportunity.apartmentId === 'R180');
    const r181Bar = bars.find(bar => bar.opportunity.apartmentId === 'R181');

    expect(r180Bars).toHaveLength(2);
    expect(r181Bar).toBeDefined();
    expect(r180Bars[0].color).toBe(r180Bars[1].color);
    expect(r180Bars[0].color).not.toBe(r181Bar!.color);
  });

  it('muestra pendiente como fecha final si no hay siguiente reserva del mismo piso', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: null,
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));

    expect(component.cleaningOpportunities()[0].availableUntilDate).toBeNull();
    expect(component.formatDate(component.cleaningOpportunities()[0].availableUntilDate)).toBe(
      'Pendiente'
    );
    expect(component.cleaningBars()[0].isEndInWeek).toBe(false);
  });

  it('renderiza el calendario semanal y la tabla de detalle', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        comments: 'Llevar llaves',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const textContent = fixture.nativeElement.textContent;
    const cleaningBar: HTMLDivElement = fixture.nativeElement.querySelector('.cleaning-bar');
    const referenceChip: HTMLSpanElement = fixture.nativeElement.querySelector('.reference-chip');
    const invoiceButton: HTMLButtonElement = fixture.nativeElement.querySelector('.invoice-btn');

    expect(textContent).toContain('Semana del 01/06/2026 - 07/06/2026');
    expect(textContent).toContain('R180');
    expect(textContent).toContain('02/06/2026');
    expect(textContent).toContain('05/06/2026');
    expect(textContent).toContain('Llevar llaves');
    expect(cleaningBar.textContent).toContain('R180');
    expect(cleaningBar.style.background).toBeTruthy();
    expect(referenceChip.style.background).toBe(cleaningBar.style.background);
    expect(invoiceButton.disabled).toBe(true);
    expect(invoiceButton.title).toContain('11:00');
  });

  it('habilita el botón de factura cuando can_bill es true y no hay factura', () => {
    setup([
      makeCleaningOpportunity({
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        can_bill: true,
        has_bill: false,
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const invoiceButton: HTMLButtonElement = fixture.nativeElement.querySelector('.invoice-btn');
    expect(invoiceButton.disabled).toBe(false);
    expect(invoiceButton.textContent).toContain('Generar factura');
  });

  it('muestra chip de estado cuando ya existe factura', () => {
    setup([
      makeCleaningOpportunity({
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        can_bill: true,
        has_bill: true,
        bill_state: 'Pagada',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.invoice-btn')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Pagada');
    expect(fixture.nativeElement.querySelector('.bill-state-chip.paid')).not.toBeNull();
  });

  it('abre el modal de factura, crea la factura y actualiza la fila', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        comments: 'Llevar llaves',
        can_bill: true,
        has_bill: false,
      }),
    ]);
    billServiceSpy.createBill.mockReturnValue(of(makeBill()));

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const invoiceButton: HTMLButtonElement = fixture.nativeElement.querySelector('.invoice-btn');
    invoiceButton.click();
    fixture.detectChanges();

    expect(cleaningTypeServiceSpy.list).toHaveBeenCalledTimes(1);
    expect(fixture.nativeElement.querySelector('.invoice-dialog')).not.toBeNull();

    const submitButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .primary-btn'
    );
    expect(submitButton.disabled).toBe(true);

    component.selectedCleaningTypeId.set(1);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('15 €/h');
    expect(fixture.nativeElement.textContent).not.toContain('Total:');

    component.startTime.set('10:00');
    component.endTime.set('12:00');
    fixture.detectChanges();

    expect(submitButton.disabled).toBe(false);
    expect(fixture.nativeElement.textContent).toContain('Total: 30 €');

    submitButton.click();
    fixture.detectChanges();

    expect(billServiceSpy.createBill).toHaveBeenCalledWith({
      record_id: 1,
      cleaning_date: expect.any(String),
      start_time: '10:00',
      end_time: '12:00',
      cleaning_type_id: 1,
    });
    expect(component.apiCleaningOpportunities()[0].has_bill).toBe(true);
    expect(component.apiCleaningOpportunities()[0].bill_state).toBe('Creada');
    expect(fixture.nativeElement.textContent).toContain(
      'Factura creada (Limpieza normal): 2 h × 15 €/h = 30 €'
    );
    expect(fixture.nativeElement.querySelector('.invoice-dialog')).toBeNull();
  });

  it('mantiene bloqueado el botón de generar factura hasta introducir horas', () => {
    setup([
      makeCleaningOpportunity({
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        can_bill: true,
        has_bill: false,
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const invoiceButton: HTMLButtonElement = fixture.nativeElement.querySelector('.invoice-btn');
    invoiceButton.click();
    fixture.detectChanges();

    component.selectedCleaningTypeId.set(1);
    fixture.detectChanges();

    const submitButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .primary-btn'
    );
    expect(component.startTime()).toBe('');
    expect(component.endTime()).toBe('');
    expect(submitButton.disabled).toBe(true);

    component.startTime.set('10:00');
    fixture.detectChanges();
    expect(submitButton.disabled).toBe(true);

    component.endTime.set('12:00');
    fixture.detectChanges();
    expect(submitButton.disabled).toBe(false);
  });

  it('muestra toast de error si falla la creación de factura', () => {
    setup([
      makeCleaningOpportunity({
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        can_bill: true,
        has_bill: false,
      }),
    ]);
    billServiceSpy.createBill.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 409, error: { detail: 'Duplicado' } }))
    );

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const invoiceButton: HTMLButtonElement = fixture.nativeElement.querySelector('.invoice-btn');
    invoiceButton.click();
    fixture.detectChanges();

    component.selectedCleaningTypeId.set(1);
    component.startTime.set('10:00');
    component.endTime.set('12:00');
    fixture.detectChanges();

    const submitButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .primary-btn'
    );
    submitButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Ya existe una factura para esta reserva.');
    expect(fixture.nativeElement.querySelector('.toast.error')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.invoice-dialog')).not.toBeNull();
  });

  it('deshabilita generar factura si la hora fin no es posterior a la de inicio', () => {
    setup([
      makeCleaningOpportunity({
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        can_bill: true,
        has_bill: false,
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const invoiceButton: HTMLButtonElement = fixture.nativeElement.querySelector('.invoice-btn');
    invoiceButton.click();
    fixture.detectChanges();

    component.startTime.set('10:00');
    component.endTime.set('09:00');
    fixture.detectChanges();

    const submitButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .primary-btn'
    );
    expect(submitButton.disabled).toBe(true);
    expect(billServiceSpy.createBill).not.toHaveBeenCalled();
  });

  it('oculta el botón de generar factura sin permiso bills:create', () => {
    setup(
      [
        makeCleaningOpportunity({
          available_from: '2026-06-02',
          available_until: '2026-06-05',
          can_bill: true,
          has_bill: false,
        }),
      ],
      false,
      false
    );

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.invoice-btn')).toBeNull();
  });

  it('muestra el lápiz de comentarios solo para admin', () => {
    setup(
      [makeCleaningOpportunity({ source_booking_record_id: 1, comments: 'Comentario' })],
      false
    );
    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.edit-btn')).toBeNull();

    TestBed.resetTestingModule();
    setup([makeCleaningOpportunity({ source_booking_record_id: 1, comments: 'Comentario' })], true);
    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.edit-btn')).not.toBeNull();
  });

  it('abre el modal de comentarios y lo cierra al pulsar fuera sin guardar', () => {
    setup(
      [makeCleaningOpportunity({ source_booking_record_id: 1, comments: 'Comentario inicial' })],
      true
    );

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const editButton: HTMLButtonElement = fixture.nativeElement.querySelector('.edit-btn');
    editButton.click();
    fixture.detectChanges();

    const textarea: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea');
    expect(textarea.value).toBe('Comentario inicial');

    const backdrop: HTMLDivElement = fixture.nativeElement.querySelector('.modal-backdrop');
    backdrop.click();
    fixture.detectChanges();

    expect(bookingServiceSpy.updateBooking).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('.comment-dialog')).toBeNull();
  });

  it('guarda comentarios con PUT y muestra toast de éxito', () => {
    setup(
      [makeCleaningOpportunity({ source_booking_record_id: 1, comments: 'Comentario inicial' })],
      true
    );
    bookingServiceSpy.updateBooking.mockReturnValue(
      of(makeBooking({ record_id: 1, notes_cleaning: 'Nuevo comentario' }))
    );

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const editButton: HTMLButtonElement = fixture.nativeElement.querySelector('.edit-btn');
    editButton.click();
    fixture.detectChanges();

    const textarea: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea');
    textarea.value = 'Nuevo comentario';
    textarea.dispatchEvent(new Event('input'));

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    expect(bookingServiceSpy.updateBooking).toHaveBeenCalledWith(1, {
      notes_cleaning: 'Nuevo comentario',
    });
    expect(component.cleaningOpportunities()[0].comments).toBe('Nuevo comentario');
    expect(fixture.nativeElement.textContent).toContain('Comentario guardado con éxito');
    expect(fixture.nativeElement.querySelector('.comment-dialog')).toBeNull();
  });

  it('borra comentarios enviando string vacío y vuelve a mostrar Sin comentarios', () => {
    setup(
      [makeCleaningOpportunity({ source_booking_record_id: 1, comments: 'Comentario inicial' })],
      true
    );
    bookingServiceSpy.updateBooking.mockReturnValue(
      of(makeBooking({ record_id: 1, notes_cleaning: '' }))
    );

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const editButton: HTMLButtonElement = fixture.nativeElement.querySelector('.edit-btn');
    editButton.click();
    fixture.detectChanges();

    const textarea: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea');
    textarea.value = '';
    textarea.dispatchEvent(new Event('input'));

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    expect(bookingServiceSpy.updateBooking).toHaveBeenCalledWith(1, { notes_cleaning: '' });
    expect(component.cleaningOpportunities()[0].comments).toBe('');
    expect(fixture.nativeElement.textContent).toContain('Sin comentarios');
  });

  it('muestra toast de error si falla al guardar el comentario', () => {
    setup(
      [makeCleaningOpportunity({ source_booking_record_id: 1, comments: 'Comentario inicial' })],
      true
    );
    bookingServiceSpy.updateBooking.mockReturnValue(throwError(() => new Error('API error')));

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const editButton: HTMLButtonElement = fixture.nativeElement.querySelector('.edit-btn');
    editButton.click();
    fixture.detectChanges();

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Ha fallado al guardar el comentario');
    expect(fixture.nativeElement.querySelector('.toast.error')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.comment-dialog')).not.toBeNull();
  });

  it('muestra error y permite reintentar si no se pueden cargar las reservas', () => {
    bookingServiceSpy = {
      getCleaningOpportunities: jest.fn().mockReturnValue(throwError(() => new Error('Forbidden'))),
      updateBooking: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;

    billServiceSpy = {
      createBill: jest.fn(),
    } as unknown as jest.Mocked<BillService>;

    cleaningTypeServiceSpy = {
      list: jest.fn().mockReturnValue(of([makeCleaningType()])),
    } as unknown as jest.Mocked<CleaningTypeService>;

    authServiceSpy = {
      hasRole: jest.fn().mockReturnValue(false),
      hasPermission: jest.fn().mockReturnValue(false),
    } as unknown as jest.Mocked<AuthService>;

    TestBed.configureTestingModule({
      imports: [CleaningOrganizationComponent],
      providers: [
        { provide: BookingService, useValue: bookingServiceSpy },
        { provide: BillService, useValue: billServiceSpy },
        { provide: CleaningTypeService, useValue: cleaningTypeServiceSpy },
        { provide: AuthService, useValue: authServiceSpy },
        {
          provide: ApartmentService,
          useValue: { getAllApartments: jest.fn().mockReturnValue(of([])) },
        },
        CalendarLayoutService,
      ],
    });

    fixture = TestBed.createComponent(CleaningOrganizationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.loadError()).toBe(
      'No se han podido cargar las reservas para organizar las limpiezas.'
    );
    expect(fixture.nativeElement.textContent).toContain('No se han podido cargar las reservas');
  });
});
