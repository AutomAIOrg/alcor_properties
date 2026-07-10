import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { BillsComponent } from './bills.component';
import { AuthService } from '../../auth/auth.service';
import { Bill } from '../../models/bill.model';
import { ApartmentService } from '../../services/apartment.service';
import { BillService } from '../../services/bill.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import { CleaningTypeService } from '../../services/cleaning-type.service';

function makeBill(overrides: Partial<Bill> = {}): Bill {
  return {
    bill_id: 1,
    record_id: 5,
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
    address: 'C/ Raquero 6 Bloque 3',
    apartment_description: 'Porto Fino',
    created_at: '2026-06-03',
    ...overrides,
  };
}

describe('BillsComponent', () => {
  let fixture: ComponentFixture<BillsComponent>;
  let component: BillsComponent;
  let billServiceSpy: jest.Mocked<BillService>;
  let authServiceSpy: jest.Mocked<AuthService>;
  let cleaningTypeServiceSpy: jest.Mocked<CleaningTypeService>;

  beforeEach(async () => {
    billServiceSpy = {
      listBills: jest.fn().mockReturnValue(of([makeBill()])),
      updateBillState: jest.fn(),
      rectifyBill: jest.fn(),
      createBill: jest.fn(),
    } as unknown as jest.Mocked<BillService>;

    cleaningTypeServiceSpy = {
      list: jest.fn().mockReturnValue(
        of([
          { cleaning_type_id: 1, name: 'Limpieza normal', hourly_rate: 15, active: true },
          { cleaning_type_id: 2, name: 'Limpieza profunda', hourly_rate: 25, active: true },
        ])
      ),
    } as unknown as jest.Mocked<CleaningTypeService>;

    authServiceSpy = {
      hasPermission: jest.fn().mockReturnValue(true),
      // Por defecto el usuario de las pruebas actúa como administrador.
      hasRole: jest.fn().mockImplementation((role: string) => role === 'admin'),
    } as unknown as jest.Mocked<AuthService>;

    await TestBed.configureTestingModule({
      imports: [BillsComponent],
      providers: [
        provideRouter([]),
        { provide: BillService, useValue: billServiceSpy },
        { provide: AuthService, useValue: authServiceSpy },
        {
          provide: ApartmentService,
          useValue: {
            getAllApartmentIds: jest.fn().mockReturnValue(of(['R180', 'R181'])),
          },
        },
        { provide: CleaningTypeService, useValue: cleaningTypeServiceSpy },
        CalendarLayoutService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(BillsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('carga facturas al iniciar', () => {
    expect(billServiceSpy.listBills).toHaveBeenCalledTimes(1);
    expect(component.bills().length).toBe(1);
  });

  it('aplica filtros al buscar', () => {
    component.filterApartmentId.set('R180');
    component.filterState.set('Creada');
    component.searchBills();

    expect(billServiceSpy.listBills).toHaveBeenLastCalledWith({
      apartment_id: 'R180',
      state: 'Creada',
    });
  });

  it('busca automáticamente al cambiar el desplegable de estado', () => {
    billServiceSpy.listBills.mockClear();

    const select = fixture.nativeElement.querySelector('.filter-field select') as HTMLSelectElement;
    select.value = 'Pagada';
    select.dispatchEvent(new Event('change'));

    expect(billServiceSpy.listBills).toHaveBeenCalledTimes(1);
    expect(billServiceSpy.listBills).toHaveBeenLastCalledWith({ state: 'Pagada' });
  });

  it('busca automáticamente con retardo al escribir en un campo de texto', () => {
    jest.useFakeTimers();
    billServiceSpy.listBills.mockClear();

    component.updateFilterApartmentId({ target: { value: 'R18' } } as unknown as Event);
    component.updateFilterApartmentId({ target: { value: 'R180' } } as unknown as Event);

    // Aún no se ha lanzado la petición: el debounce sigue pendiente.
    expect(billServiceSpy.listBills).not.toHaveBeenCalled();

    jest.advanceTimersByTime(400);

    expect(billServiceSpy.listBills).toHaveBeenCalledTimes(1);
    expect(billServiceSpy.listBills).toHaveBeenLastCalledWith({ apartment_id: 'R180' });

    jest.useRealTimers();
  });

  it('muestra acciones para factura creada: confirmar pago y rectificar (ya no cancelar)', () => {
    fixture.detectChanges();

    const buttons = [...fixture.nativeElement.querySelectorAll('.action-btn')].map(
      (button: HTMLButtonElement) => button.textContent?.trim()
    );

    expect(buttons).toContain('Confirmar pago');
    expect(buttons).toContain('Rectificar factura');
    expect(buttons).not.toContain('Cancelar');
  });

  it('el filtro muestra "Pendiente de pago" en vez de "Creada" y no ofrece "Cancelada"', () => {
    const options = [...fixture.nativeElement.querySelectorAll('.filter-field select option')].map(
      (option: HTMLOptionElement) => option.textContent?.trim()
    );

    expect(options).not.toContain('Cancelada');
    expect(options).not.toContain('Creada');
    expect(options).toEqual(
      expect.arrayContaining(['Todos', 'Pendiente', 'Pendiente de pago', 'Pagada'])
    );
  });

  it('muestra el estado "Creada" como "Pendiente de pago" en el chip', () => {
    fixture.detectChanges();

    const chip: HTMLElement = fixture.nativeElement.querySelector('.bill-state-chip');
    expect(chip.textContent?.trim()).toBe('Pendiente de pago');
  });

  it('una factura pagada no muestra acciones: queda solo para previsualización', () => {
    billServiceSpy.listBills.mockReturnValue(
      of([makeBill({ state: 'Pagada', paid_at: '2026-06-05' })])
    );
    component.searchBills();
    fixture.detectChanges();

    // Sin botones de acción (no se puede revertir ni modificar una factura pagada)...
    expect(fixture.nativeElement.querySelector('.action-btn')).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('Revertir a creada');
    // ...pero el chip de estado sigue permitiendo abrir el recibo.
    expect(fixture.nativeElement.querySelector('button.bill-state-chip')).not.toBeNull();
  });

  it('oculta "Confirmar pago" cuando el rol actual ya confirmó el pago y muestra quién y cuándo', () => {
    billServiceSpy.listBills.mockReturnValue(
      of([
        makeBill({
          paid_confirmed_by_admin: '2026-06-03T14:30:00',
          paid_confirmed_by_admin_name: 'Admin User',
        }),
      ])
    );
    component.searchBills();
    fixture.detectChanges();

    const buttons = [...fixture.nativeElement.querySelectorAll('.action-btn')].map(
      (button: HTMLButtonElement) => button.textContent?.trim()
    );

    expect(buttons).not.toContain('Confirmar pago');
    expect(buttons).toContain('Rectificar factura');
    expect(fixture.nativeElement.textContent).toContain(
      'Pago confirmado por Admin User el día 03/06/2026 a las 14:30'
    );
  });

  it('muestra una línea de confirmación por cada parte que ya haya confirmado', () => {
    billServiceSpy.listBills.mockReturnValue(
      of([
        makeBill({
          state: 'Pagada',
          paid_at: '2026-06-04',
          paid_confirmed_by_admin: '2026-06-03T14:30:00',
          paid_confirmed_by_admin_name: 'Admin User',
          paid_confirmed_by_cleaner: '2026-06-04T09:15:00',
          paid_confirmed_by_cleaner_name: 'Limpiadora Test',
        }),
      ])
    );
    component.searchBills();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Pago confirmado por Admin User el día 03/06/2026 a las 14:30'
    );
    expect(fixture.nativeElement.textContent).toContain(
      'Pago confirmado por Limpiadora Test el día 04/06/2026 a las 09:15'
    );
  });

  it('la primera confirmación (admin) no pide fecha de pago y avisa de que falta la otra parte', () => {
    billServiceSpy.updateBillState.mockReturnValue(
      of(
        makeBill({
          state: 'Creada',
          paid_confirmed_by_admin: '2026-06-03T14:30:00',
          paid_confirmed_by_admin_name: 'Admin User',
        })
      )
    );

    component.requestTransition(makeBill(), 'Pagada');
    fixture.detectChanges();

    // La fecha de pago la declara la limpiadora: administración no ve el campo.
    expect(fixture.nativeElement.querySelector('.confirm-dialog input[type="date"]')).toBeNull();

    component.confirmMarkPaid();
    fixture.detectChanges();

    expect(billServiceSpy.updateBillState).toHaveBeenCalledWith(1, { state: 'Pagada' });
    expect(component.bills()[0].state).toBe('Creada');
    expect(component.bills()[0].paid_confirmed_by_admin).toBe('2026-06-03T14:30:00');
    expect(fixture.nativeElement.textContent).toContain(
      'Pasará a Pagada cuando confirme la otra parte'
    );
    expect(fixture.nativeElement.textContent).toContain(
      'Pago confirmado por Admin User el día 03/06/2026 a las 14:30'
    );
  });

  it('muestra el recibo de la factura al pulsar el chip de estado', () => {
    fixture.detectChanges();

    const chipButton: HTMLButtonElement =
      fixture.nativeElement.querySelector('button.bill-state-chip');
    chipButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.receipt')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.receipt-paid-badge')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('RECIBO');
    expect(fixture.nativeElement.textContent).toContain('treinta euros');
    expect(fixture.nativeElement.textContent).toContain('C/ Raquero 6 Bloque 3');
    expect(fixture.nativeElement.textContent).not.toContain('Porto Fino');
    // La FECHA usa el created_at congelado de la factura, no el día actual.
    expect(fixture.nativeElement.textContent).toContain('FECHA 03/06/2026');

    const closeButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.receipt-dialog .secondary-btn'
    );
    closeButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.receipt')).toBeNull();
  });

  it('muestra el sello PAGADA y la fecha de pago en el recibo de una factura pagada', () => {
    billServiceSpy.listBills.mockReturnValue(
      of([makeBill({ state: 'Pagada', paid_at: '2026-06-05' })])
    );
    component.searchBills();
    fixture.detectChanges();

    const chipButton: HTMLButtonElement =
      fixture.nativeElement.querySelector('button.bill-state-chip');
    chipButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.receipt-paid-badge')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('PAGADA');
    expect(fixture.nativeElement.textContent).toContain('Total pagado');
    expect(fixture.nativeElement.textContent).toContain('Pagada el 05/06/2026');
  });

  it('muestra en el recibo quién confirmó el pago y cuándo', () => {
    billServiceSpy.listBills.mockReturnValue(
      of([
        makeBill({
          state: 'Pagada',
          paid_at: '2026-06-05',
          paid_confirmed_by_admin: '2026-06-04T14:30:00',
          paid_confirmed_by_admin_name: 'Admin User',
          paid_confirmed_by_cleaner: '2026-06-05T09:15:00',
          paid_confirmed_by_cleaner_name: 'Limpiadora Test',
        }),
      ])
    );
    component.searchBills();
    fixture.detectChanges();

    const chipButton: HTMLButtonElement =
      fixture.nativeElement.querySelector('button.bill-state-chip');
    chipButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Pago confirmado por Admin User el día 04/06/2026 a las 14:30'
    );
    expect(fixture.nativeElement.textContent).toContain(
      'Pago confirmado por Limpiadora Test el día 05/06/2026 a las 09:15'
    );
  });

  it('la limpiadora declara la fecha de pago al confirmar desde el modal', () => {
    authServiceSpy.hasRole.mockImplementation(role => role === 'limpiadora');
    billServiceSpy.updateBillState.mockReturnValue(
      of(makeBill({ state: 'Pagada', paid_at: '2026-06-03' }))
    );

    component.requestTransition(makeBill(), 'Pagada');
    fixture.detectChanges();

    expect(
      fixture.nativeElement.querySelector('.confirm-dialog input[type="date"]')
    ).not.toBeNull();

    component.paidAtDate.set('2026-06-03');
    component.confirmMarkPaid();
    fixture.detectChanges();

    expect(billServiceSpy.updateBillState).toHaveBeenCalledWith(1, {
      state: 'Pagada',
      paid_at: '2026-06-03',
    });
    expect(component.bills()[0].state).toBe('Pagada');
  });

  it('rectifica una factura creada recalculando el coste y manteniéndola creada', () => {
    billServiceSpy.rectifyBill.mockReturnValue(
      of(
        makeBill({
          state: 'Creada',
          cleaning_date: '2026-07-01',
          clean_hours: 3,
          hourly_rate: 25,
          cost: 75,
          cleaning_type_id: 2,
          cleaning_type_name: 'Limpieza profunda',
        })
      )
    );

    component.openRectify(makeBill());
    fixture.detectChanges();

    // El modal precarga los datos actuales de la factura: la factura base tiene 2 h, por lo
    // que el intervalo reconstruido es 10:00–12:00.
    expect(fixture.nativeElement.querySelector('#rectify-bill-title')).not.toBeNull();
    expect(component.rectifyStartTime()).toBe('10:00');
    expect(component.rectifyEndTime()).toBe('12:00');

    // Las horas se derivan del intervalo inicio–fin, no se teclean a mano.
    component.rectifyDate.set('2026-07-01');
    component.rectifyStartTime.set('10:00');
    component.rectifyEndTime.set('13:00');
    component.rectifyCleaningTypeId.set(2);
    expect(component.rectifyHours()).toBe(3);
    // Coste recalculado: 3 h × 25 €/h = 75 €.
    expect(component.rectifyCost()).toBe(75);

    component.confirmRectify();
    fixture.detectChanges();

    expect(billServiceSpy.rectifyBill).toHaveBeenCalledWith(1, {
      cleaning_date: '2026-07-01',
      clean_hours: 3,
      cleaning_type_id: 2,
    });
    expect(component.bills()[0].cost).toBe(75);
    expect(component.bills()[0].state).toBe('Creada');
    // El modal se cierra tras rectificar.
    expect(component.rectifyingBill()).toBeNull();
  });

  it('muestra toast de error si falla la rectificación', () => {
    billServiceSpy.rectifyBill.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 422, error: { detail: 'Datos inválidos' } }))
    );

    component.openRectify(makeBill());
    component.rectifyDate.set('2026-07-01');
    component.rectifyStartTime.set('10:00');
    component.rectifyEndTime.set('13:00');
    component.rectifyCleaningTypeId.set(2);
    component.confirmRectify();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Datos inválidos');
    expect(fixture.nativeElement.querySelector('.toast.error')).not.toBeNull();
  });

  it('no muestra acciones en facturas pendientes virtuales', () => {
    billServiceSpy.listBills.mockReturnValue(
      of([makeBill({ bill_id: null, state: 'Pendiente', cost: null, hourly_rate: null })])
    );
    component.searchBills();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.action-btn')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Generar desde Org. Limpiezas');
  });
});
