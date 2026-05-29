/**
 * gallery.js — Photo Gallery Lightbox
 *
 * Adds a click-to-enlarge lightbox for gallery images.
 * Uses keyboard navigation (Escape to close, arrow keys for prev/next).
 */
(function () {
  'use strict';

  let lightbox, lightboxImg, lightboxCaption, currentIndex = 0;
  /** @type {HTMLElement[]} */
  let cards = [];

  function init() {
    lightbox        = document.getElementById('lightbox');
    lightboxImg     = document.getElementById('lightbox-img');
    lightboxCaption = document.getElementById('lightbox-caption');

    if (!lightbox) return;

    // Collect all gallery images with data-lightbox attribute
    cards = Array.from(document.querySelectorAll('[data-lightbox]'));

    cards.forEach((card, idx) => {
      card.addEventListener('click', () => openLightbox(idx));
      // Keyboard accessibility: Enter/Space on the wrapper
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openLightbox(idx); }
      });
    });

    // Close controls
    document.getElementById('lightbox-close')
      ?.addEventListener('click', closeLightbox);
    document.getElementById('lightbox-backdrop')
      ?.addEventListener('click', closeLightbox);

    // Prev / Next buttons
    document.getElementById('lightbox-prev')
      ?.addEventListener('click', prevPhoto);
    document.getElementById('lightbox-next')
      ?.addEventListener('click', nextPhoto);

    // Keyboard navigation
    document.addEventListener('keydown', onKeyDown);
  }

  /**
   * Open the lightbox at a given index.
   *
   * @param {number} idx - Index of the card in the `cards` array.
   */
  function openLightbox(idx) {
    if (idx < 0 || idx >= cards.length) return;
    currentIndex = idx;

    const card = cards[idx];
    lightboxImg.src     = card.dataset.lightbox;
    lightboxImg.alt     = card.dataset.caption || 'Wedding photo';
    lightboxCaption.textContent = card.dataset.caption || '';

    lightbox.hidden = false;
    document.body.style.overflow = 'hidden';
    lightbox.focus();
  }

  function closeLightbox() {
    lightbox.hidden = true;
    document.body.style.overflow = '';
  }

  function nextPhoto() {
    openLightbox((currentIndex + 1) % cards.length);
  }

  function prevPhoto() {
    openLightbox((currentIndex - 1 + cards.length) % cards.length);
  }

  /**
   * Handle keyboard events for lightbox navigation.
   *
   * @param {KeyboardEvent} e
   */
  function onKeyDown(e) {
    if (lightbox.hidden) return;
    switch (e.key) {
      case 'Escape':    closeLightbox(); break;
      case 'ArrowRight': nextPhoto();   break;
      case 'ArrowLeft':  prevPhoto();   break;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
