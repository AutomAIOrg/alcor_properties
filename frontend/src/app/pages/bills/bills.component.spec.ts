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

  beforeEach(async () => {
    billServiceSpy = {
      listBills: jest.fn().mockReturnValue(of([makeBill()])),
      updateBillState: jest.fn(),
      createBill: jest.fn(),
    } as unknown as jest.Mocked<BillService>;

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

  it('muestra acciones para factura creada', () => {
    fixture.detectChanges();

    const buttons = [...fixture.nativeElement.querySelectorAll('.action-btn')].map(
      (button: HTMLButtonElement) => button.textContent?.trim()
    );

    expect(buttons).toContain('Confirmar pago');
    expect(buttons).toContain('Cancelar');
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
    expect(buttons).toContain('Cancelar');
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

  it('cancela una factura con nota explicativa desde el modal', () => {
    billServiceSpy.updateBillState.mockReturnValue(
      of(makeBill({ state: 'Cancelada', cancellation_note: 'Reserva duplicada' }))
    );

    component.requestTransition(makeBill(), 'Cancelada');
    fixture.detectChanges();

    component.cancelNote.set('Reserva duplicada');
    component.confirmCancel();
    fixture.detectChanges();

    expect(billServiceSpy.updateBillState).toHaveBeenCalledWith(1, {
      state: 'Cancelada',
      cancellation_note: 'Reserva duplicada',
    });
    expect(component.bills()[0].state).toBe('Cancelada');
    expect(component.bills()[0].cancellation_note).toBe('Reserva duplicada');
  });

  it('cancela sin nota cuando el campo se deja vacío', () => {
    billServiceSpy.updateBillState.mockReturnValue(of(makeBill({ state: 'Cancelada' })));

    component.requestTransition(makeBill(), 'Cancelada');
    fixture.detectChanges();
    component.confirmCancel();
    fixture.detectChanges();

    expect(billServiceSpy.updateBillState).toHaveBeenCalledWith(1, { state: 'Cancelada' });
  });

  it('muestra toast de error si falla la actualización de estado', () => {
    billServiceSpy.updateBillState.mockReturnValue(
      throwError(
        () => new HttpErrorResponse({ status: 422, error: { detail: 'Transición inválida' } })
      )
    );

    component.requestTransition(makeBill(), 'Cancelada');
    fixture.detectChanges();
    component.confirmCancel();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Transición inválida');
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
