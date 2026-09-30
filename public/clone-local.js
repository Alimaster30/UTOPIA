/* Local-only adaptations. Original styling and theme behavior live in wp-content. */
(() => {
  // Never forward an admissions request from the development copy.
  document.addEventListener('submit', event => {
    if (!event.target.matches('.wpcf7-form')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const form = event.target;
    const output = form.querySelector('.wpcf7-response-output');
    const message = 'Local preview only. Your request has not been sent to Tilton School.';
    if (output) { output.textContent = message; output.style.display = 'block'; output.setAttribute('role', 'status'); }
    else { const note = document.createElement('p'); note.setAttribute('role', 'status'); note.textContent = message; form.append(note); }
    form.classList.remove('submitting');
  }, true);
})();
