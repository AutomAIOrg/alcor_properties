import { Directive, ElementRef, inject, output } from '@angular/core';

/**
 * Cierra un modal al hacer click en su fondo (backdrop), pero solo si tanto la
 * pulsación como la soltura del ratón ocurren sobre el propio fondo.
 *
 * Esto evita cierres accidentales cuando el usuario empieza a pulsar dentro del
 * modal (por ejemplo, seleccionando texto de un input) y suelta el botón fuera
 * de él: en ese caso el evento `click` del navegador se dispara sobre el fondo
 * (el ancestro común), pero la interacción empezó dentro del modal.
 *
 * Uso:
 *   <div class="modal-backdrop" appDismissableBackdrop (backdropDismiss)="close()">
 *     <div class="modal-card">…</div>
 *   </div>
 *
 * El contenido interior no necesita `stopPropagation`: solo se emite el cierre
 * cuando el objetivo del click es el propio fondo, no un elemento hijo.
 */
@Directive({
  selector: '[appDismissableBackdrop]',
  standalone: true,
  host: {
    '(mousedown)': 'onMouseDown($event)',
    '(click)': 'onClick($event)',
  },
})
export class DismissableBackdropDirective {
  private host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

  /** Se emite cuando el usuario cierra el modal pulsando en el fondo. */
  backdropDismiss = output<void>();

  private pressStartedOnBackdrop = false;

  onMouseDown(event: MouseEvent): void {
    this.pressStartedOnBackdrop = event.target === this.host;
  }

  onClick(event: MouseEvent): void {
    const dismiss = this.pressStartedOnBackdrop && event.target === this.host;
    this.pressStartedOnBackdrop = false;
    if (dismiss) this.backdropDismiss.emit();
  }
}
