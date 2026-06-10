import { Component, OnInit, ViewChild, inject, signal } from '@angular/core';

import { Apartment } from '../../models/apartment.model';
import { Booking } from '../../models/booking.model';
import { ApartmentService } from '../../services/apartment.service';
import { BookingModalComponent } from '../../shared/components/booking-modal/booking-modal.component';
import {
  ApartmentSearchComponent,
  type ApartmentLoadRequest,
} from './components/apartment-search/apartment-search.component';
import { AvailabilitySearchComponent } from './components/availability-search/availability-search.component';
import { BookingSearchComponent } from './components/booking-search/booking-search.component';

type Tab = 'availability' | 'apartment' | 'bookings';

@Component({
  selector: 'app-searches',
  standalone: true,
  imports: [
    BookingModalComponent,
    AvailabilitySearchComponent,
    ApartmentSearchComponent,
    BookingSearchComponent,
  ],
  templateUrl: './searches.component.html',
  styleUrl: './searches.component.scss',
})
export class SearchesComponent implements OnInit {
  private apartmentService = inject(ApartmentService);

  @ViewChild(ApartmentSearchComponent) private apartmentSearch?: ApartmentSearchComponent;
  @ViewChild(BookingSearchComponent) private bookingSearch?: BookingSearchComponent;

  private apartmentRequestId = 0;

  activeTab = signal<Tab>('availability');
  selectedBooking = signal<Booking | null>(null);
  apartmentToLoad = signal<ApartmentLoadRequest | null>(null);
  allApartmentIds = signal<string[]>([]);

  ngOnInit(): void {
    this.apartmentService.getAllApartmentIds().subscribe({
      next: ids => this.allApartmentIds.set(ids),
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

  onBookingSaved(updated: Booking): void {
    this.apartmentSearch?.applyBookingUpdate(updated);
    this.bookingSearch?.applyBookingUpdate(updated);
    this.selectedBooking.set(updated);
  }
}
