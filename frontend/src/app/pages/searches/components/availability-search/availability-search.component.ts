import { Component, inject, output, signal } from '@angular/core';

import { Apartment } from '../../../../models/apartment.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { ApartmentService } from '../../../../services/apartment.service';
import {
  DateRangePickerComponent,
  type DateRangeValue,
} from '../../../../shared/components/date-range-picker/date-range-picker.component';

export type AvailabilityBookingCreateRequest = {
  apartment: Apartment;
  checkIn: string;
  checkOut: string;
};

@Component({
  selector: 'app-availability-search',
  standalone: true,
  imports: [BookingColorPipe, DateRangePickerComponent],
  templateUrl: './availability-search.component.html',
  styleUrl: './availability-search.component.scss',
})
export class AvailabilitySearchComponent {
  private apartmentService = inject(ApartmentService);
  private availabilityRequestId = 0;

  apartmentSelected = output<Apartment>();
  bookingCreateRequested = output<AvailabilityBookingCreateRequest>();

  avail = {
    from: signal(''),
    to: signal(''),
    q: signal(''),
    community: signal(''),
    minRooms: signal<number | null>(null),
    minBathrooms: signal<number | null>(null),
    minOccupants: signal<number | null>(null),
    parking: signal<string | null>(null),
    loading: signal(false),
    error: signal(''),
    results: signal<Apartment[]>([]),
  };

  searchAvailability(): void {
    if (!this.avail.from() || !this.avail.to()) return;

    const requestId = ++this.availabilityRequestId;

    this.avail.loading.set(true);
    this.avail.error.set('');
    this.avail.results.set([]);

    const filters: Parameters<typeof this.apartmentService.searchApartments>[0] = {
      available_from: this.avail.from(),
      available_to: this.avail.to(),
    };
    if (this.avail.q()) filters.q = this.avail.q();
    if (this.avail.community()) filters.community = this.avail.community();
    if (this.avail.minRooms() != null) filters.min_rooms = this.avail.minRooms()!;
    if (this.avail.minBathrooms() != null) filters.min_bathrooms = this.avail.minBathrooms()!;
    if (this.avail.minOccupants() != null) filters.min_occupants = this.avail.minOccupants()!;

    const parking = this.avail.parking();
    if (parking) {
      filters.parking = parking;
    }

    this.apartmentService.searchApartments(filters).subscribe({
      next: apartments => {
        if (requestId !== this.availabilityRequestId) return;

        this.avail.results.set(apartments);
        this.avail.loading.set(false);
      },
      error: () => {
        if (requestId !== this.availabilityRequestId) return;

        this.avail.error.set('Error al cargar pisos. Comprueba los filtros.');
        this.avail.loading.set(false);
      },
    });
  }

  clearAvailability(): void {
    this.availabilityRequestId += 1;
    this.avail.from.set('');
    this.avail.to.set('');
    this.avail.q.set('');
    this.avail.community.set('');
    this.avail.minRooms.set(null);
    this.avail.minBathrooms.set(null);
    this.avail.minOccupants.set(null);
    this.avail.parking.set(null);
    this.avail.loading.set(false);
    this.avail.results.set([]);
    this.avail.error.set('');
  }

  setAvailabilityRange(range: DateRangeValue): void {
    this.avail.from.set(range.from);
    this.avail.to.set(range.to);
  }

  completeAvailabilityRange(range: DateRangeValue): void {
    this.setAvailabilityRange(range);
    this.searchAvailability();
  }

  searchAvailabilityIfDatesReady(): void {
    if (this.avail.from() && this.avail.to()) {
      this.searchAvailability();
    }
  }

  selectApartment(apartment: Apartment): void {
    this.apartmentSelected.emit(apartment);
  }

  requestBookingCreate(apartment: Apartment, event?: Event): void {
    event?.stopPropagation();

    if (!this.avail.from() || !this.avail.to()) return;

    this.bookingCreateRequested.emit({
      apartment,
      checkIn: this.avail.from(),
      checkOut: this.avail.to(),
    });
  }

  inputValue(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }

  inputNumberOrNull(event: Event): number | null {
    const value = (event.target as HTMLInputElement).value;
    return value === '' ? null : Number(value);
  }

  selectValue(event: Event): string {
    return (event.target as HTMLSelectElement).value;
  }

  updateAvailabilityParking(event: Event): void {
    this.avail.parking.set(this.selectValue(event));
    this.searchAvailabilityIfDatesReady();
  }
}
