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
    cancellation_note: null,
    previously_cancelled: false,
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

    expect(buttons).toContain('Marcar pagada');
    expect(buttons).toContain('Cancelar');
  });

  it('marca una factura como pagada desde el modal', () => {
    billServiceSpy.updateBillState.mockReturnValue(
      of(makeBill({ state: 'Pagada', paid_at: '2026-06-03' }))
    );

    component.requestTransition(makeBill(), 'Pagada');
    fixture.detectChanges();

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
