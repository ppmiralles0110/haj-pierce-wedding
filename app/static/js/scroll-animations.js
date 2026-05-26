/**
 * scroll-animations.js — IntersectionObserver Fade-In-Up Animations
 *
 * Elements with class `.animate-on-scroll` start invisible (set in CSS)
 * and receive the `.visible` class when they enter the viewport,
 * triggering the CSS transition.
 */
(function () {
  'use strict';

  /**
   * Initialise scroll animations using IntersectionObserver.
   * Falls back gracefully if the API is not supported.
   */
  function init() {
    const elements = document.querySelectorAll('.animate-on-scroll');
    if (!elements.length) return;

    if (!('IntersectionObserver' in window)) {
      // Fallback: make everything visible immediately
      elements.forEach((el) => el.classList.add('visible'));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            // Unobserve once triggered (one-shot animation)
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.12,        // Trigger when 12% of element is visible
        rootMargin: '0px 0px -40px 0px',  // Trigger slightly before fully in viewport
      }
    );

    elements.forEach((el) => observer.observe(el));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
