import { Injectable } from '@angular/core';

const LAST_ACTIVITY_KEY = 'auth_last_activity_at';
const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;
const ACTIVITY_EVENTS = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'] as const;

@Injectable({ providedIn: 'root' })
export class SessionActivityService {
  readonly timeoutMs = INACTIVITY_TIMEOUT_MS;

  private timeoutId: ReturnType<typeof setTimeout> | null = null;
  private onExpired: (() => void) | null = null;
  private listening = false;
  private readonly activityHandler = () => this.recordActivity();

  start(onExpired: () => void): void {
    this.onExpired = onExpired;

    if (!this.getLastActivityAt()) {
      this.recordActivity();
    }

    if (!this.listening) {
      ACTIVITY_EVENTS.forEach(eventName =>
        window.addEventListener(eventName, this.activityHandler, { passive: true })
      );
      this.listening = true;
    }

    this.scheduleLogout();
  }

  stop(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    if (this.listening) {
      ACTIVITY_EVENTS.forEach(eventName =>
        window.removeEventListener(eventName, this.activityHandler)
      );
      this.listening = false;
    }

    this.onExpired = null;
    localStorage.removeItem(LAST_ACTIVITY_KEY);
  }

  recordActivity(): void {
    localStorage.setItem(LAST_ACTIVITY_KEY, Date.now().toString());
    this.scheduleLogout();
  }

  isIdleExpired(): boolean {
    const lastActivityAt = this.getLastActivityAt();
    if (!lastActivityAt) return true;
    return Date.now() - lastActivityAt >= INACTIVITY_TIMEOUT_MS;
  }

  getLastActivityAt(): number | null {
    const value = localStorage.getItem(LAST_ACTIVITY_KEY);
    if (!value) return null;

    const timestamp = Number(value);
    return Number.isFinite(timestamp) ? timestamp : null;
  }

  private scheduleLogout(): void {
    if (!this.onExpired) return;

    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }

    const lastActivityAt = this.getLastActivityAt() ?? Date.now();
    const remainingMs = Math.max(INACTIVITY_TIMEOUT_MS - (Date.now() - lastActivityAt), 0);

    this.timeoutId = setTimeout(() => {
      if (this.isIdleExpired()) {
        this.onExpired?.();
      } else {
        this.scheduleLogout();
      }
    }, remainingMs);
  }
}
