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
    // La limpieza la identifica la reserva que llega (source); la que se va abre la ventana.
    source_booking_record_id: 1,
    apartment_id: 'R180',
    available_from: '2026-06-02',
    available_until: '2026-06-05',
    available_from_time: '11:00:00',
    available_until_time: '16:00:00',
    comments: '',
    can_bill: false,
    has_bill: false,
    bill_state: null,
    address: null,
    apartment_description: null,
    previous_booking_record_id: 2,
    persons: 2,
    nights: 3,
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
    check_in_time: null,
    check_out_time: null,
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
    paid_confirmed_by_admin: null,
    paid_confirmed_by_admin_name: null,
    paid_confirmed_by_cleaner: null,
    paid_confirmed_by_cleaner_name: null,
    cancellation_note: null,
    previously_cancelled: false,
    address: null,
    apartment_description: null,
    created_at: null,
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
      listBills: jest.fn(),
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

  it('limita la navegación hacia delante de limpiadora a la semana siguiente', () => {
    setup([], false);

    const currentWeek = component.weekStartIso();

    expect(component.canGoNextWeek()).toBe(true);

    component.nextWeek();
    const nextWeek = component.weekStartIso();
    expect(nextWeek).not.toBe(currentWeek);
    expect(component.canGoNextWeek()).toBe(false);

    component.nextWeek();
    expect(component.weekStartIso()).toBe(nextWeek);
  });

  it('permite retroceder semanas sin límite y recarga la semana visible', () => {
    setup([], false);

    const currentWeek = component.weekStartIso();

    for (let i = 0; i < 10; i++) component.prevWeek();

    const tenWeeksBack = component.weekStartIso();
    expect(tenWeeksBack < currentWeek).toBe(true);
    expect(bookingServiceSpy.getCleaningOpportunities).toHaveBeenLastCalledWith(tenWeeksBack);

    component.goToToday();
    expect(component.weekStartIso()).toBe(currentWeek);
  });

  it('permite a admin retroceder antes de la semana actual', () => {
    setup([], true);

    const currentWeek = component.weekStartIso();

    component.prevWeek();
    expect(component.weekStartIso() < currentWeek).toBe(true);
  });

  it('muestra solo las limpiezas con check-in en la semana seleccionada', () => {
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
      // Sale en la semana pero la entrada cae fuera: no se muestra.
      makeCleaningOpportunity({
        source_booking_record_id: 3,
        apartment_id: 'R182',
        available_from: '2026-06-04',
        available_until: '2026-06-20',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));

    expect(component.cleaningOpportunities()).toEqual([
      {
        apartmentId: 'R180',
        availableFromDate: '2026-06-02',
        availableFromTime: '11:00:00',
        availableUntilDate: '2026-06-05',
        availableUntilTime: '16:00:00',
        comments: 'Llevar llaves',
        sourceBookingRecordId: 1,
        canBill: false,
        hasBill: false,
        billState: null,
        address: null,
        previousBookingRecordId: 2,
        persons: 2,
        nights: 3,
      },
    ]);
  });

  it('ordena las limpiezas por entrada (check-in) de más antigua a más reciente', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R181',
        available_from: '2026-06-01',
        available_until: '2026-06-06',
      }),
      makeCleaningOpportunity({
        source_booking_record_id: 2,
        apartment_id: 'R182',
        available_from: '2026-06-01',
        available_until: '2026-06-02',
      }),
      makeCleaningOpportunity({
        source_booking_record_id: 3,
        apartment_id: 'R183',
        available_from: '2026-06-01',
        available_until: '2026-06-04',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));

    const order = component.cleaningOpportunities().map(o => o.sourceBookingRecordId);
    expect(order).toEqual([2, 3, 1]);
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

  it('pinta la limpieza de una reserva sin reserva anterior', () => {
    // Ventana de cabecera: el backend la abre el lunes de la semana del check-in.
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-01',
        available_until: '2026-06-03',
        previous_booking_record_id: null,
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));

    expect(component.cleaningOpportunities().length).toBe(1);
    const [bar] = component.cleaningBars();
    expect(bar.isStartInWeek).toBe(true);
    expect(bar.isEndInWeek).toBe(true);
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

    expect(textContent).toContain('Semana 23 del 01/06/2026 al 07/06/2026');
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
        address: 'C/ Raquero 6 Bloque 3',
        apartment_description: 'Porto Fino',
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

    const previewButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .preview-btn'
    );
    expect(previewButton.disabled).toBe(true);

    component.selectedCleaningTypeId.set(1);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('15 €/h');
    expect(fixture.nativeElement.textContent).not.toContain('Total:');

    component.startTime.set('10:00');
    component.endTime.set('12:00');
    fixture.detectChanges();

    expect(previewButton.disabled).toBe(false);
    expect(fixture.nativeElement.textContent).toContain('Total: 30 €');

    previewButton.click();
    fixture.detectChanges();

    // Antes de guardar se muestra la previsualización del recibo, sin crear la factura.
    expect(component.showInvoicePreview()).toBe(true);
    expect(fixture.nativeElement.querySelector('.receipt')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('RECIBO');
    expect(fixture.nativeElement.textContent).toContain('treinta euros');
    expect(fixture.nativeElement.textContent).toContain('C/ Raquero 6 Bloque 3');
    expect(fixture.nativeElement.textContent).not.toContain('Porto Fino');
    expect(billServiceSpy.createBill).not.toHaveBeenCalled();

    const confirmButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .confirm-btn'
    );
    confirmButton.click();
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

  it('muestra el recibo de una factura ya creada al pulsar el chip de estado', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        apartment_id: 'R180',
        available_from: '2026-06-02',
        available_until: '2026-06-05',
        can_bill: true,
        has_bill: true,
        bill_state: 'Creada',
      }),
    ]);
    billServiceSpy.listBills.mockReturnValue(
      of([
        makeBill({
          record_id: 1,
          address: 'C/ Raquero 6 Bloque 3',
          apartment_description: 'Porto Fino',
        }),
      ])
    );

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const chipButton: HTMLButtonElement =
      fixture.nativeElement.querySelector('button.bill-state-chip');
    chipButton.click();
    fixture.detectChanges();

    expect(billServiceSpy.listBills).toHaveBeenCalledWith({ apartment_id: 'R180' });
    expect(fixture.nativeElement.querySelector('.receipt')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('RECIBO');
    expect(fixture.nativeElement.textContent).toContain('treinta euros');
    expect(fixture.nativeElement.textContent).toContain('C/ Raquero 6 Bloque 3');
    expect(fixture.nativeElement.textContent).not.toContain('Porto Fino');
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

    const previewButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .preview-btn'
    );
    previewButton.click();
    fixture.detectChanges();

    const confirmButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.invoice-dialog .confirm-btn'
    );
    confirmButton.click();
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
    // Pulsar y soltar sobre el propio fondo cierra el modal (descartando cambios).
    backdrop.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
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

  it('muestra las horas de salida y entrada de la reserva', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        available_from_time: '11:00:00',
        available_until_time: '16:00:00',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const times = Array.from(
      fixture.nativeElement.querySelectorAll('.time-cell span')
    ) as HTMLElement[];
    expect(times.map(cell => cell.textContent?.trim())).toEqual(['11:00', '16:00']);
  });

  it('muestra la hora pactada cuando la reserva tiene uno distinta de la estándar', () => {
    setup([
      makeCleaningOpportunity({
        source_booking_record_id: 1,
        available_from_time: '13:30:00',
        available_until_time: '18:00:00',
      }),
    ]);

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const times = Array.from(
      fixture.nativeElement.querySelectorAll('.time-cell span')
    ) as HTMLElement[];
    expect(times.map(cell => cell.textContent?.trim())).toEqual(['13:30', '18:00']);
  });

  it('muestra el lápiz de horas solo para admin', () => {
    setup([makeCleaningOpportunity({ source_booking_record_id: 1 })], false);
    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.time-edit-btn')).toBeNull();

    TestBed.resetTestingModule();
    setup([makeCleaningOpportunity({ source_booking_record_id: 1 })], true);
    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.time-edit-btn')).not.toBeNull();
  });

  it('el lápiz de salida edita solo la hora de salida, en la reserva que se va', () => {
    setup(
      [
        makeCleaningOpportunity({
          source_booking_record_id: 1,
          previous_booking_record_id: 2,
          available_from_time: '11:00:00',
          available_until_time: '16:00:00',
        }),
      ],
      true
    );
    bookingServiceSpy.updateBooking.mockReturnValue(of(makeBooking()));

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const [checkOutPencil] = Array.from(
      fixture.nativeElement.querySelectorAll('.time-edit-btn')
    ) as HTMLButtonElement[];
    checkOutPencil.click();
    fixture.detectChanges();

    // Un único campo, precargado con la hora de salida.
    const inputs = fixture.nativeElement.querySelectorAll('.times-form-grid input[type="time"]');
    expect(inputs.length).toBe(1);
    expect((inputs[0] as HTMLInputElement).value).toBe('11:00');
    expect(fixture.nativeElement.textContent).toContain('Editar hora de salida');

    (inputs[0] as HTMLInputElement).value = '13:30';
    inputs[0].dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    expect(bookingServiceSpy.updateBooking).toHaveBeenCalledTimes(1);
    // La hora de salida vive en la reserva anterior, no en la que ancla la limpieza.
    expect(bookingServiceSpy.updateBooking).toHaveBeenCalledWith(2, { check_out_time: '13:30' });
    expect(component.cleaningOpportunities()[0].availableFromTime).toBe('13:30');
    expect(component.cleaningOpportunities()[0].availableUntilTime).toBe('16:00:00');
    expect(fixture.nativeElement.textContent).toContain('Hora guardada con éxito');
  });

  it('el lápiz de entrada edita solo la hora de entrada, en la reserva que llega', () => {
    setup(
      [
        makeCleaningOpportunity({
          source_booking_record_id: 1,
          previous_booking_record_id: 2,
          available_from_time: '11:00:00',
          available_until_time: '16:00:00',
        }),
      ],
      true
    );
    bookingServiceSpy.updateBooking.mockReturnValue(of(makeBooking()));

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const [, checkInPencil] = Array.from(
      fixture.nativeElement.querySelectorAll('.time-edit-btn')
    ) as HTMLButtonElement[];
    checkInPencil.click();
    fixture.detectChanges();

    const inputs = fixture.nativeElement.querySelectorAll('.times-form-grid input[type="time"]');
    expect(inputs.length).toBe(1);
    expect((inputs[0] as HTMLInputElement).value).toBe('16:00');
    expect(fixture.nativeElement.textContent).toContain('Editar hora de entrada');

    (inputs[0] as HTMLInputElement).value = '18:00';
    inputs[0].dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    expect(bookingServiceSpy.updateBooking).toHaveBeenCalledTimes(1);
    // La hora de entrada vive en la reserva que llega, que es la que ancla la limpieza.
    expect(bookingServiceSpy.updateBooking).toHaveBeenCalledWith(1, { check_in_time: '18:00' });
    expect(component.cleaningOpportunities()[0].availableFromTime).toBe('11:00:00');
    expect(component.cleaningOpportunities()[0].availableUntilTime).toBe('18:00');
  });

  it('no envía PUT si la hora no ha cambiado', () => {
    setup(
      [
        makeCleaningOpportunity({
          source_booking_record_id: 1,
          available_from_time: '11:00:00',
        }),
      ],
      true
    );
    bookingServiceSpy.updateBooking.mockReturnValue(of(makeBooking()));

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const editButton: HTMLButtonElement = fixture.nativeElement.querySelector('.time-edit-btn');
    editButton.click();
    fixture.detectChanges();

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    expect(bookingServiceSpy.updateBooking).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('.comment-dialog')).toBeNull();
  });

  it('permite editar la hora de salida incluso sin reserva anterior', () => {
    setup(
      [
        makeCleaningOpportunity({
          source_booking_record_id: 1,
          previous_booking_record_id: null,
          available_from_time: '11:00:00',
          available_until_time: '16:00:00',
        }),
      ],
      true
    );
    bookingServiceSpy.updateBooking.mockReturnValue(of(makeBooking()));

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    // Sin reserva anterior aun se muestra el lápiz de salida y su hora.
    const pencils = fixture.nativeElement.querySelectorAll('.time-edit-btn');
    expect(pencils.length).toBe(2);
    expect(pencils[0].getAttribute('title')).toBe('Editar hora de salida');
    expect(pencils[1].getAttribute('title')).toBe('Editar hora de entrada');

    // La hora de salida se muestra y se puede editar (se guarda en la propia reserva que llega).
    const [checkOutPencil] = pencils as HTMLButtonElement[];
    checkOutPencil.click();
    fixture.detectChanges();

    const inputs = fixture.nativeElement.querySelectorAll('.times-form-grid input[type="time"]');
    expect(inputs.length).toBe(1);
    expect((inputs[0] as HTMLInputElement).value).toBe('11:00');
    expect(fixture.nativeElement.textContent).toContain('Editar hora de salida');

    (inputs[0] as HTMLInputElement).value = '13:30';
    inputs[0].dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    // Como no hay reserva anterior, se guarda en la propia reserva que llega.
    expect(bookingServiceSpy.updateBooking).toHaveBeenCalledWith(1, { check_out_time: '13:30' });
    expect(component.cleaningOpportunities()[0].availableFromTime).toBe('13:30');
    expect(component.cleaningOpportunities()[0].availableUntilTime).toBe('16:00:00');
    expect(fixture.nativeElement.textContent).toContain('Hora guardada con éxito');
  });

  it('muestra toast de error si falla al guardar la hora', () => {
    setup([makeCleaningOpportunity({ source_booking_record_id: 1 })], true);
    bookingServiceSpy.updateBooking.mockReturnValue(throwError(() => new Error('API error')));

    component.currentDate.set(new Date(2026, 5, 3));
    fixture.detectChanges();

    const editButton: HTMLButtonElement = fixture.nativeElement.querySelector('.time-edit-btn');
    editButton.click();
    fixture.detectChanges();

    const checkOutInput: HTMLInputElement = fixture.nativeElement.querySelector(
      '.times-form-grid input[type="time"]'
    );
    checkOutInput.value = '13:30';
    checkOutInput.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const acceptButton: HTMLButtonElement = fixture.nativeElement.querySelector('.primary-btn');
    acceptButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Ha fallado al guardar la hora');
    expect(fixture.nativeElement.querySelector('.toast.error')).not.toBeNull();
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
