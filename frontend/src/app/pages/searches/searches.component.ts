import { Component, OnInit, ViewChild, inject, signal } from '@angular/core';

import { Apartment } from '../../models/apartment.model';
import { Booking } from '../../models/booking.model';
import { ApartmentColorService } from '../../services/apartment-color.service';
import { ApartmentService } from '../../services/apartment.service';
import {
  BookingCreateModalComponent,
  type BookingCreateInitialValues,
} from '../../shared/components/booking-create-modal/booking-create-modal.component';
import { BookingModalComponent } from '../../shared/components/booking-modal/booking-modal.component';
import {
  ApartmentSearchComponent,
  type ApartmentLoadRequest,
} from './components/apartment-search/apartment-search.component';
import {
  AvailabilitySearchComponent,
  type AvailabilityBookingCreateRequest,
} from './components/availability-search/availability-search.component';
import { BookingSearchComponent } from './components/booking-search/booking-search.component';

type Tab = 'availability' | 'apartment' | 'bookings';

@Component({
  selector: 'app-searches',
  standalone: true,
  imports: [
    BookingModalComponent,
    BookingCreateModalComponent,
    AvailabilitySearchComponent,
    ApartmentSearchComponent,
    BookingSearchComponent,
  ],
  templateUrl: './searches.component.html',
  styleUrl: './searches.component.scss',
})
export class SearchesComponent implements OnInit {
  private apartmentService = inject(ApartmentService);
  private apartmentColor = inject(ApartmentColorService);

  @ViewChild(AvailabilitySearchComponent) private availabilitySearch?: AvailabilitySearchComponent;
  @ViewChild(ApartmentSearchComponent) private apartmentSearch?: ApartmentSearchComponent;
  @ViewChild(BookingSearchComponent) private bookingSearch?: BookingSearchComponent;

  private apartmentRequestId = 0;

  activeTab = signal<Tab>('availability');
  selectedBooking = signal<Booking | null>(null);
  createBookingInitialValues = signal<BookingCreateInitialValues | null>(null);
  apartmentToLoad = signal<ApartmentLoadRequest | null>(null);
  allApartmentIds = signal<string[]>([]);
  loadingApartmentIds = signal(false);
  apartmentIdsError = signal<string | null>(null);
  private apartmentIdsLoaded = false;

  ngOnInit(): void {
    // Los badges de apartamento usan el color personalizado del piso si lo tiene.
    this.apartmentColor.ensureLoaded();
  }

  selectTab(tab: Tab): void {
    this.activeTab.set(tab);

    if (tab === 'apartment' || tab === 'bookings') {
      this.ensureApartmentIdsLoaded();
    }
  }

  openApartmentDetail(apartment: Apartment): void {
    this.apartmentRequestId += 1;
    this.apartmentToLoad.set({
      apartmentId: apartment.apartment_id || '',
      requestId: this.apartmentRequestId,
    });
    this.activeTab.set('apartment');
  }

  openModal(booking: Booking): void {
    this.selectedBooking.set(booking);
  }

  closeModal(): void {
    this.selectedBooking.set(null);
  }

  openCreateBookingModal(request: AvailabilityBookingCreateRequest): void {
    this.ensureApartmentIdsLoaded();
    this.createBookingInitialValues.set({
      apartment_id: request.apartment.apartment_id,
      check_in: request.checkIn,
      check_out: request.checkOut,
    });
  }

  closeCreateBookingModal(): void {
    this.createBookingInitialValues.set(null);
  }

  onBookingCreated(created: Booking): void {
    this.createBookingInitialValues.set(null);
    this.availabilitySearch?.searchAvailabilityIfDatesReady();
    this.apartmentSearch?.refreshAfterBookingSaved(created);
    this.bookingSearch?.refreshAfterBookingSaved(created);
  }

  onBookingSaved(updated: Booking): void {
    this.apartmentSearch?.refreshAfterBookingSaved(updated);
    this.bookingSearch?.refreshAfterBookingSaved(updated);
    this.selectedBooking.set(updated);
  }

  private ensureApartmentIdsLoaded(): void {
    if (this.apartmentIdsLoaded || this.loadingApartmentIds()) return;

    this.loadingApartmentIds.set(true);
    this.apartmentIdsError.set(null);

    this.apartmentService.getAllApartmentIds().subscribe({
      next: ids => {
        this.allApartmentIds.set(ids);
        this.apartmentIdsLoaded = true;
        this.loadingApartmentIds.set(false);
      },
      error: () => {
        this.allApartmentIds.set([]);
        this.apartmentIdsError.set('No se pudieron cargar los pisos.');
        this.loadingApartmentIds.set(false);
      },
    });
  }
}
