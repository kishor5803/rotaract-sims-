document.addEventListener("DOMContentLoaded", () => {
  // Reserved for accessible client-side enhancements. Server validation remains authoritative.
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const submit = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submit) {
        submit.dataset.originalText = submit.value || submit.textContent;
      }
    });
  });
});
