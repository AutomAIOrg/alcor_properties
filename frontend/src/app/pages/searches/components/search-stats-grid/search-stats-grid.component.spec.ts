import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SearchStatsGridComponent, type SearchStatsGridData } from './search-stats-grid.component';

function makeStats(overrides: Partial<SearchStatsGridData> = {}): SearchStatsGridData {
  return {
    total_bookings: 4,
    active_bookings: 2,
    cancelled_bookings: 1,
    cancellation_rate: 25,
    total_nights: 7,
    avg_nights_per_booking: 3.5,
    total_persons: 6,
    avg_persons_per_booking: 3,
    total_revenue: 700,
    avg_revenue_per_booking: 350,
    avg_revenue_per_night: 100,
    total_charges: 40,
    total_electric_allowance: 20,
    occupancy_pct: 50,
    status_breakdown: { Confirmed: 2, Pending: 1, Cancelled: 1 },
    ...overrides,
  };
}

describe('SearchStatsGridComponent', () => {
  let fixture: ComponentFixture<SearchStatsGridComponent>;
  let component: SearchStatsGridComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SearchStatsGridComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SearchStatsGridComponent);
    component = fixture.componentInstance;
    component.stats = makeStats();
    fixture.detectChanges();
  });

  it('muestra una tarjeta con las reservas pendientes', () => {
    const text = fixture.nativeElement.textContent as string;

    expect(component.pendingBookings()).toBe(1);
    expect(text).toContain('Pendientes');
    expect(text).toContain('1');
  });

  it('cuenta tambien estados pendientes en espanol', () => {
    component.stats = makeStats({ status_breakdown: { Pendiente: 2, Pending: 1 } });

    expect(component.pendingBookings()).toBe(3);
  });
});
