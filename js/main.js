/* ═══════════════════════════════════════════════════════
   Ciracon – Shared JavaScript
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

  /* ── Mobile Navigation Toggle ── */
  var toggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.nav-links');

  if (toggle && navLinks) {
    toggle.addEventListener('click', function () {
      navLinks.classList.toggle('open');
      var isOpen = navLinks.classList.contains('open');
      toggle.setAttribute('aria-expanded', isOpen);
    });

    // Close menu when a link is clicked
    navLinks.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        navLinks.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ── Scroll Reveal ── */
  var reveals = document.querySelectorAll('.reveal');

  if (reveals.length > 0 && 'IntersectionObserver' in window) {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px'
    });

    reveals.forEach(function (el) {
      revealObserver.observe(el);
    });
  } else {
    // Fallback: show everything
    reveals.forEach(function (el) {
      el.classList.add('visible');
    });
  }

  /* ── Accordion ── */
  var accordionBtns = document.querySelectorAll('.accordion-btn');

  accordionBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var item = btn.closest('.accordion-item');
      var content = item.querySelector('.accordion-content');
      var inner = content.querySelector('.accordion-content-inner');
      var isOpen = item.classList.contains('open');

      // Close all siblings
      var parent = item.parentElement;
      parent.querySelectorAll('.accordion-item.open').forEach(function (openItem) {
        if (openItem !== item) {
          openItem.classList.remove('open');
          openItem.querySelector('.accordion-content').style.maxHeight = '0';
        }
      });

      // Toggle current
      if (isOpen) {
        item.classList.remove('open');
        content.style.maxHeight = '0';
      } else {
        item.classList.add('open');
        content.style.maxHeight = inner.scrollHeight + 'px';
      }
    });
  });

  /* ── Active Nav Link ── */
  var currentPath = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a:not(.nav-cta)').forEach(function (link) {
    var href = link.getAttribute('href');
    if (href === currentPath || (currentPath === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });

  /* ── Dynamic Copyright Year ── */
  var yearEl = document.getElementById('year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  /* ── Nav Scroll Effect ── */
  var nav = document.querySelector('.nav');
  if (nav) {
    var onScroll = function () {
      if (window.scrollY > 50) {
        nav.classList.add('nav-scrolled');
      } else {
        nav.classList.remove('nav-scrolled');
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── Async Contact Form (StaticForms) ──
     Progressive enhancement: form works via normal POST;
     this JS intercepts to provide inline success/error states
     without a page reload. */
  var contactForm = document.getElementById('contact-form');
  var formSuccess = document.getElementById('form-success');
  var formError = document.getElementById('form-error');
  var submitBtn = document.getElementById('submit-btn');

  if (contactForm && formSuccess) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();

      // Validate required fields before sending
      if (!contactForm.checkValidity()) {
        contactForm.reportValidity();
        return;
      }

      // Set loading state
      var btnText = submitBtn.querySelector('.btn-text');
      var btnLoading = submitBtn.querySelector('.btn-loading');
      submitBtn.disabled = true;
      submitBtn.classList.add('is-loading');
      if (btnText) btnText.hidden = true;
      if (btnLoading) btnLoading.hidden = false;
      if (formError) formError.classList.remove('is-visible');

      // Get reCAPTCHA v3 token before submitting
      grecaptcha.ready(function () {
        grecaptcha.execute('6Lc5aIUsAAAAAESKs8pfD4SpGebtwBaHNEYFxsA3', { action: 'submit' }).then(function (token) {
          var recaptchaField = document.getElementById('g-recaptcha-response');
          if (recaptchaField) recaptchaField.value = token;

          var formData = new FormData(contactForm);
          var jsonBody = {};
          formData.forEach(function (value, key) { jsonBody[key] = value; });

          fetch(contactForm.action, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(jsonBody)
          })
      .then(function (response) {
        if (response.ok || response.status === 200) {
          // Success: hide form, show thank-you panel
          contactForm.hidden = true;
          formSuccess.hidden = false;
          formSuccess.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          throw new Error('Submission failed');
        }
      })
      .catch(function () {
        // Error: show inline error message, reset button
        if (formError) formError.classList.add('is-visible');
        submitBtn.disabled = false;
        submitBtn.classList.remove('is-loading');
        if (btnText) btnText.hidden = false;
        if (btnLoading) btnLoading.hidden = true;
      });
        }); // end grecaptcha.execute
      }); // end grecaptcha.ready
    });
  }

});
