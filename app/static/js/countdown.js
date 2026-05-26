/**
 * countdown.js — Wedding Day Countdown Timer
 * Reads the target date from data-date attribute on #countdown.
 * Updates every second. Stops when the date arrives.
 */
(function () {
  'use strict';

  /**
   * Parse the wedding date string from the DOM and start the countdown.
   * The date attribute should be a human-readable string like
   * "December 12, 2026" or an ISO date string.
   */
  function initCountdown() {
    const el = document.getElementById('countdown');
    if (!el) return;

    const dateStr = el.dataset.date;
    if (!dateStr) return;

    const target = new Date(dateStr);
    if (isNaN(target.getTime())) {
      console.warn('[countdown] Invalid date:', dateStr);
      return;
    }

    const days    = document.getElementById('cd-days');
    const hours   = document.getElementById('cd-hours');
    const minutes = document.getElementById('cd-minutes');
    const seconds = document.getElementById('cd-seconds');

    /**
     * Calculate remaining time components and update the DOM.
     */
    function tick() {
      const now  = new Date();
      const diff = target.getTime() - now.getTime();

      if (diff <= 0) {
        // Wedding day has arrived!
        if (days)    days.textContent    = '0';
        if (hours)   hours.textContent   = '0';
        if (minutes) minutes.textContent = '0';
        if (seconds) seconds.textContent = '0';
        return;
      }

      const totalSec  = Math.floor(diff / 1000);
      const d = Math.floor(totalSec / 86400);
      const h = Math.floor((totalSec % 86400) / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      const s = totalSec % 60;

      if (days)    days.textContent    = String(d);
      if (hours)   hours.textContent   = String(h).padStart(2, '0');
      if (minutes) minutes.textContent = String(m).padStart(2, '0');
      if (seconds) seconds.textContent = String(s).padStart(2, '0');

      setTimeout(tick, 1000);
    }

    tick();
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCountdown);
  } else {
    initCountdown();
  }
}());
