import { Component, OnInit, ViewChild, inject, signal } from '@angular/core';

import { Apartment } from '../../models/apartment.model';
import { Booking } from '../../models/booking.model';
import { ApartmentService } from '../../services/apartment.service';
import { BookingService } from '../../services/booking.service';
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
  private bookingService = inject(BookingService);

  @ViewChild(AvailabilitySearchComponent) private availabilitySearch?: AvailabilitySearchComponent;
  @ViewChild(ApartmentSearchComponent) private apartmentSearch?: ApartmentSearchComponent;
  @ViewChild(BookingSearchComponent) private bookingSearch?: BookingSearchComponent;

  private apartmentRequestId = 0;

  activeTab = signal<Tab>('availability');
  selectedBooking = signal<Booking | null>(null);
  createBookingInitialValues = signal<BookingCreateInitialValues | null>(null);
  apartmentToLoad = signal<ApartmentLoadRequest | null>(null);
  allApartmentIds = signal<string[]>([]);
  bookings = signal<Booking[]>([]);

  ngOnInit(): void {
    this.apartmentService.getAllApartmentIds().subscribe({
      next: ids => this.allApartmentIds.set(ids),
    });

    this.bookingService.getBookings().subscribe({
      next: bookings => this.bookings.set(bookings),
    });
  }

  selectTab(tab: Tab): void {
    this.activeTab.set(tab);
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
    this.bookings.update(bookings => [created, ...bookings]);
    this.createBookingInitialValues.set(null);
    this.availabilitySearch?.searchAvailabilityIfDatesReady();
    this.apartmentSearch?.refreshAfterBookingSaved(created);
    this.bookingSearch?.refreshAfterBookingSaved(created);
  }

  onBookingSaved(updated: Booking): void {
    this.bookings.update(bookings =>
      bookings.map(booking => (booking.record_id === updated.record_id ? updated : booking))
    );
    this.apartmentSearch?.refreshAfterBookingSaved(updated);
    this.bookingSearch?.refreshAfterBookingSaved(updated);
    this.selectedBooking.set(updated);
  }
}
