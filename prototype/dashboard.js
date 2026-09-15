/* Staff Hub dashboard behaviour.
   Deployed as the File object /staff/dashboard.js and loaded by pt_homepage.
   Source of truth is this file, as prototype/staff-dashboard.css is for local.css.
   Keep it pure ASCII: Zope may serve it with a Latin-1 charset. */

/* Full-text tooltip for clamped announcement summaries.
   The summary text is the only trigger - the PM removed the "More" control:
     mouse    - hover the text for two seconds;
     touch    - tap the text to toggle (hover does not exist there);
     keyboard - a clipped summary is made focusable, and focus opens it at once;
                Enter or Space toggles, Escape closes.
   The tooltip stays open while the pointer or focus is inside it (WCAG 1.4.13).
   Screen readers already get the whole text: the clamp only hides it visually,
   so the tooltip is a visual aid and carries no ARIA state (aria-expanded is
   not permitted on a plain div, and a button role would announce the whole
   summary as a button label).
   Only summaries that are actually clipped become interactive. */
(function () {
  var OPEN_DELAY = 2000;
  var CLOSE_DELAY = 200;
  var groups = document.querySelectorAll('.staff-news__summary');
  if (!groups.length) { return; }

  var current = null, openTimer = null, closeTimer = null, entries = [];
  /* True between a pointer press and its click, so the focus a click gives the
     summary does not open the tooltip only for the click to close it again. */
  var pointerPress = false;

  function place(tip) {
    tip.style.left = '0px';
    var box = tip.getBoundingClientRect();
    var over = box.right - (window.innerWidth - 8);
    if (over > 0) { tip.style.left = (0 - over) + 'px'; }
    var after = tip.getBoundingClientRect();
    if (after.left > 8) { return; }
    tip.style.left = (parseFloat(tip.style.left || 0) + (8 - after.left)) + 'px';
  }

  function close() {
    window.clearTimeout(openTimer);
    window.clearTimeout(closeTimer);
    if (!current) { return; }
    current.tip.hidden = true;
    if (current.card) { current.card.classList.remove('has-open-tip'); }
    current = null;
  }

  function open(entry) {
    window.clearTimeout(closeTimer);
    if (current) {
      if (current === entry) { return; }
      close();
    }
    entry.tip.hidden = false;
    /* Raise the owning card so later cards cannot paint over the tooltip. */
    if (entry.card) { entry.card.classList.add('has-open-tip'); }
    place(entry.tip);
    current = entry;
  }

  function toggle(entry) {
    window.clearTimeout(openTimer);
    if (current === entry) { close(); } else { open(entry); }
  }

  function scheduleClose() {
    window.clearTimeout(closeTimer);
    closeTimer = window.setTimeout(close, CLOSE_DELAY);
  }

  function measure(entry) {
    var clipped = entry.clamp.scrollHeight > entry.clamp.clientHeight + 1;
    entry.clipped = clipped;
    if (clipped) {
      entry.clamp.classList.add('is-clipped');
      entry.clamp.setAttribute('tabindex', '0');
    } else {
      entry.clamp.classList.remove('is-clipped');
      entry.clamp.removeAttribute('tabindex');
      if (current === entry) { close(); }
    }
  }

  Array.prototype.forEach.call(groups, function (summary) {
    var clamp = summary.querySelector('.staff-news__clamp');
    var tip = summary.querySelector('.staff-news__tip');
    if (!clamp) { return; }
    if (!tip) { return; }
    var entry = { clamp: clamp, tip: tip,
                  card: summary.closest ? summary.closest('.staff-card') : null };
    entries.push(entry);

    clamp.addEventListener('mouseenter', function () {
      if (!entry.clipped) { return; }
      window.clearTimeout(closeTimer);
      window.clearTimeout(openTimer);
      openTimer = window.setTimeout(function () { open(entry); }, OPEN_DELAY);
    });
    clamp.addEventListener('mouseleave', function () {
      window.clearTimeout(openTimer);
      scheduleClose();
    });

    clamp.addEventListener('pointerdown', function () { pointerPress = true; });
    clamp.addEventListener('focus', function () {
      if (!entry.clipped || pointerPress) { return; }
      open(entry);
    });
    clamp.addEventListener('blur', function (ev) {
      pointerPress = false;      /* a press that never became a click */
      if (ev.relatedTarget && tip.contains(ev.relatedTarget)) { return; }
      scheduleClose();
    });

    /* Click covers touch, where hover does not exist. */
    clamp.addEventListener('click', function () {
      pointerPress = false;
      if (!entry.clipped) { return; }
      toggle(entry);
    });
    clamp.addEventListener('keydown', function (ev) {
      if (!entry.clipped) { return; }
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        toggle(entry);
      }
    });

    tip.addEventListener('mouseenter', function () { window.clearTimeout(closeTimer); });
    tip.addEventListener('mouseleave', function () { scheduleClose(); });
    tip.addEventListener('focusout', function (ev) {
      if (ev.relatedTarget) {
        if (tip.contains(ev.relatedTarget)) { return; }
        if (ev.relatedTarget === clamp) { return; }
      }
      scheduleClose();
    });

    measure(entry);
  });

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') { close(); }
  });
  document.addEventListener('click', function (ev) {
    if (!current) { return; }
    if (current.tip.contains(ev.target)) { return; }
    /* The summary toggles itself, so a click on it is not a click outside. */
    if (current.clamp.contains(ev.target)) { return; }
    close();
  });

  var resizeTimer = null;
  window.addEventListener('resize', function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      close();
      entries.forEach(function (e) { measure(e); });
    }, 150);
  });
}());

/* Events Calendar
   The template pre-renders the current month and the next eleven with all but
   one hidden, so paging is a toggle rather than a request. Only days with
   events are buttons; each controls a panel of that day's events below the
   grid. The month heading is aria-live, so paging is announced. */
(function () {
  var cards = document.querySelectorAll('.staff-cal');
  Array.prototype.forEach.call(cards, function (card) {
    var months = Array.prototype.slice.call(card.querySelectorAll('.staff-cal__month'));
    if (!months.length) { return; }
    var heading = card.querySelector('.staff-cal__heading');
    var prev = card.querySelector('.staff-cal__step[data-step="-1"]');
    var next = card.querySelector('.staff-cal__step[data-step="1"]');
    var current = 0;
    months.forEach(function (month, i) { if (!month.hidden) { current = i; } });

    function show(index) {
      if (index < 0 || index >= months.length) { return; }
      var focused = document.activeElement;
      months.forEach(function (month, i) { month.hidden = i !== index; });
      current = index;
      if (heading) { heading.textContent = months[index].getAttribute('data-heading'); }
      if (prev) { prev.disabled = index === 0; }
      if (next) { next.disabled = index === months.length - 1; }
      // A button that disables itself drops focus to the page; hand it to the
      // other arrow instead so keyboard users are not thrown back to the top.
      if (focused === prev && prev.disabled && next) { next.focus(); }
      if (focused === next && next.disabled && prev) { prev.focus(); }
    }

    if (prev) { prev.addEventListener('click', function () { show(current - 1); }); }
    if (next) { next.addEventListener('click', function () { show(current + 1); }); }

    months.forEach(function (month) {
      var days = Array.prototype.slice.call(month.querySelectorAll('button.staff-cal__day'));
      days.forEach(function (day) {
        day.addEventListener('click', function () {
          days.forEach(function (other) {
            var on = other === day;
            other.setAttribute('aria-pressed', on ? 'true' : 'false');
            var panel = document.getElementById(other.getAttribute('aria-controls'));
            if (panel) { panel.hidden = !on; }
          });
        });
      });
    });

    show(current);
  });
}());
