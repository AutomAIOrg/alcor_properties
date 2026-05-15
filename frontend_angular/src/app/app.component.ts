import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common'; 

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})

export class AppComponent {
  isSidebarHidden = false; //variable para controlar la visibilidad de la barra lateral

  toggleSidebar() {
    this.isSidebarHidden = !this.isSidebarHidden; //cambia el estado de la barra lateral
  }
}
