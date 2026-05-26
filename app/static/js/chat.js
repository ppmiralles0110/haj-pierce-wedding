/**
 * chat.js — AI Wedding Concierge Chatbot (Floating Widget)
 *
 * Handles:
 * - FAB open/close toggle
 * - Sending messages via fetch POST to /api/chat
 * - Receiving SSE (Server-Sent Events) streaming tokens
 * - Rendering bot messages token by token
 * - Maintaining conversation history in memory
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  /** @type {Array<{role: string, content: string}>} */
  const history = [];

  // ---------------------------------------------------------------------------
  // DOM references — only queried once on init
  // ---------------------------------------------------------------------------
  let fab, panel, closeBtn, messagesEl, inputEl, formEl;

  /**
   * Initialise chat widget once the DOM is ready.
   */
  function init() {
    fab        = document.getElementById('chat-fab');
    panel      = document.getElementById('chat-panel');
    closeBtn   = document.getElementById('chat-close');
    messagesEl = document.getElementById('chat-messages');
    inputEl    = document.getElementById('chat-input');
    formEl     = document.getElementById('chat-input-form');

    if (!fab || !panel) return;  // Widget not present on this page

    fab.addEventListener('click', openPanel);
    closeBtn.addEventListener('click', closePanel);
    formEl.addEventListener('submit', handleSubmit);

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && panel.classList.contains('chat-panel--open')) {
        closePanel();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Panel open / close
  // ---------------------------------------------------------------------------

  function openPanel() {
    panel.classList.add('chat-panel--open');
    panel.removeAttribute('aria-hidden');
    fab.setAttribute('aria-expanded', 'true');
    inputEl.focus();
  }

  function closePanel() {
    panel.classList.remove('chat-panel--open');
    panel.setAttribute('aria-hidden', 'true');
    fab.setAttribute('aria-expanded', 'false');
  }

  // ---------------------------------------------------------------------------
  // Message rendering helpers
  // ---------------------------------------------------------------------------

  /**
   * Append a complete message bubble to the chat messages container.
   *
   * @param {'user'|'bot'} role
   * @param {string} text
   * @returns {HTMLElement} The created message element.
   */
  function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `chat-message chat-message--${role}`;
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
  }

  /**
   * Append an empty bot message bubble that will be filled by streaming.
   *
   * @returns {HTMLElement} The empty message element.
   */
  function appendStreamingMessage() {
    const div = document.createElement('div');
    div.className = 'chat-message chat-message--bot';
    div.setAttribute('aria-live', 'polite');
    div.innerHTML = '<span class="chat-typing">…</span>';
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ---------------------------------------------------------------------------
  // Form submission & SSE streaming
  // ---------------------------------------------------------------------------

  /**
   * Handle the chat form submission.
   *
   * @param {SubmitEvent} e
   */
  async function handleSubmit(e) {
    e.preventDefault();

    const message = (inputEl.value || '').trim();
    if (!message) return;

    inputEl.value = '';
    inputEl.disabled = true;

    // Render user message immediately
    appendMessage('user', message);

    // Add to local history
    history.push({ role: 'user', content: message });

    // Prepare streaming bot message element
    const botEl = appendStreamingMessage();
    let fullResponse = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history: history.slice(0, -1) }),
        credentials: 'same-origin',
      });

      if (!response.ok) {
        botEl.textContent = 'Sorry, something went wrong. Please try again.';
        return;
      }

      // Read SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE lines
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';  // Keep incomplete chunk in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const payload = JSON.parse(line.slice(6));

            if (payload.error) {
              botEl.textContent = 'Sorry, the AI service is temporarily unavailable.';
              return;
            }

            if (payload.token) {
              fullResponse += payload.token;
              botEl.textContent = fullResponse;
              scrollToBottom();
            }

            if (payload.done) {
              fullResponse = payload.full || fullResponse;
              botEl.textContent = fullResponse;
              scrollToBottom();
            }
          } catch {
            // Malformed JSON line — skip
          }
        }
      }
    } catch (err) {
      console.error('[chat] Stream error:', err);
      botEl.textContent = 'Network error. Please check your connection and try again.';
    } finally {
      inputEl.disabled = false;
      inputEl.focus();

      // Save bot response to local history
      if (fullResponse) {
        history.push({ role: 'assistant', content: fullResponse });
        // Trim history to last 10 turns to save memory
        while (history.length > 20) history.shift();
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Bootstrap
  // ---------------------------------------------------------------------------
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
