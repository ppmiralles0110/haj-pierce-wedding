/**
 * idle-logout.js — Auto-logout after 5 minutes of inactivity.
 *
 * Shows a "still there?" warning at 4 minutes, then redirects to
 * /logout at 5 minutes if the user takes no action.
 * Any activity (mouse, keyboard, touch, scroll) resets the timer.
 */
(function () {
  'use strict';

  const WARN_MS   = 4 * 60 * 1000;  // show warning at 4 min
  const LOGOUT_MS = 5 * 60 * 1000;  // logout at 5 min
  const LOGOUT_URL = '/logout';

  const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'click', 'scroll', 'wheel'];

  let warnTimer   = null;
  let logoutTimer = null;
  let warningEl   = null;
  let countdownInterval = null;
  let secondsLeft = 60;

  // ---------------------------------------------------------------------------
  // Warning overlay
  // ---------------------------------------------------------------------------

  function buildWarning() {
    const el = document.createElement('div');
    el.id = 'idle-warning';
    el.setAttribute('role', 'alertdialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-labelledby', 'idle-warning-title');
    el.style.cssText = [
      'display:none',
      'position:fixed',
      'inset:0',
      'z-index:10000',
      'background:rgba(0,0,0,0.75)',
      'align-items:center',
      'justify-content:center',
    ].join(';');

    el.innerHTML = `
      <div style="
        background:var(--color-bg-card,#1a1a2e);
        border:1px solid rgba(201,169,110,0.30);
        border-radius:12px;
        padding:40px 48px;
        text-align:center;
        max-width:380px;
        width:calc(100% - 48px);
        box-shadow:0 24px 64px rgba(0,0,0,0.5);
      ">
        <p id="idle-warning-title" style="
          font-family:var(--font-subheading,sans-serif);
          font-size:10px;
          letter-spacing:3px;
          text-transform:uppercase;
          color:var(--color-primary,#800020);
          margin:0 0 16px;
        ">Session Timeout</p>

        <p style="
          color:var(--color-text-primary,#fff);
          font-size:16px;
          font-weight:600;
          margin:0 0 8px;
        ">Are you still there?</p>

        <p style="
          color:var(--color-text-muted,#aaa);
          font-size:13px;
          margin:0 0 24px;
          line-height:1.6;
        ">
          You'll be logged out in
          <strong id="idle-countdown" style="color:var(--color-primary,#800020);">60</strong>s
          due to inactivity.
        </p>

        <button id="idle-stay-btn" style="
          background:var(--color-primary,#800020);
          color:#ffffff;
          border:none;
          padding:13px 36px;
          border-radius:6px;
          font-family:var(--font-subheading,sans-serif);
          font-size:11px;
          font-weight:600;
          letter-spacing:2px;
          text-transform:uppercase;
          cursor:pointer;
        ">Stay Logged In</button>
      </div>
    `;

    document.body.appendChild(el);

    el.querySelector('#idle-stay-btn').addEventListener('click', function () {
      resetTimers();
    });

    return el;
  }

  // ---------------------------------------------------------------------------
  // Timer management
  // ---------------------------------------------------------------------------

  function showWarning() {
    if (!warningEl) warningEl = buildWarning();
    warningEl.style.display = 'flex';
    secondsLeft = 60;
    document.getElementById('idle-countdown').textContent = secondsLeft;

    countdownInterval = setInterval(function () {
      secondsLeft -= 1;
      const cd = document.getElementById('idle-countdown');
      if (cd) cd.textContent = secondsLeft;
      if (secondsLeft <= 0) clearInterval(countdownInterval);
    }, 1000);
  }

  function hideWarning() {
    if (warningEl) warningEl.style.display = 'none';
    clearInterval(countdownInterval);
  }

  function doLogout() {
    window.location.href = LOGOUT_URL;
  }

  function resetTimers() {
    clearTimeout(warnTimer);
    clearTimeout(logoutTimer);
    hideWarning();

    warnTimer   = setTimeout(showWarning, WARN_MS);
    logoutTimer = setTimeout(doLogout,    LOGOUT_MS);
  }

  // ---------------------------------------------------------------------------
  // Bootstrap
  // ---------------------------------------------------------------------------

  function init() {
    ACTIVITY_EVENTS.forEach(function (evt) {
      document.addEventListener(evt, resetTimers, { passive: true });
    });
    resetTimers();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
