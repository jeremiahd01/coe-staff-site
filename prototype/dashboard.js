/* Staff Hub dashboard behaviour.
   Deployed as the File object /staff/dashboard.js and loaded by pt_homepage.
   Source of truth is this file, as prototype/staff-dashboard.css is for local.css.
   Keep it pure ASCII: Zope may serve it with a Latin-1 charset. */

/* Full-text tooltip for clamped announcement summaries.
   The summary text is the hover and tap target. The small "More" control stays
   as the keyboard affordance and as a visible hint that there is more to read.
   Hover opens after a delay; keyboard focus opens at once; Escape closes; the
   tooltip stays open while the pointer or focus is inside it (WCAG 1.4.13).
   The trigger is revealed only when the text is actually clipped.
   Originally inline in the template, which is why it avoids ampersand and
   less-than characters; that constraint no longer applies here. */
(function () {
  var OPEN_DELAY = 1000;
  var groups = document.querySelectorAll('.staff-news__summary');
  if (!groups.length) { return; }

  var current = null, openTimer = null, closeTimer = null, entries = [];

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
    current.btn.setAttribute('aria-expanded', 'false');
    if (current.card) { current.card.classList.remove('has-open-tip'); }
    current = null;
  }

  function open(entry) {
    if (current) {
      if (current === entry) { return; }
      close();
    }
    entry.tip.hidden = false;
    entry.btn.setAttribute('aria-expanded', 'true');
    /* Raise the owning card so later cards cannot paint over the tooltip. */
    if (entry.card) { entry.card.classList.add('has-open-tip'); }
    place(entry.tip);
    current = entry;
  }

  function scheduleClose() {
    window.clearTimeout(closeTimer);
    closeTimer = window.setTimeout(close, 200);
  }

  function measure(entry) {
    var clipped = entry.clamp.scrollHeight > entry.clamp.clientHeight + 1;
    entry.clipped = clipped;
    entry.btn.hidden = !clipped;
    if (clipped) {
      entry.clamp.classList.add('is-clipped');
    } else {
      entry.clamp.classList.remove('is-clipped');
      if (current === entry) { close(); }
    }
  }

  Array.prototype.forEach.call(groups, function (summary) {
    var clamp = summary.querySelector('.staff-news__clamp');
    var btn = summary.querySelector('.staff-news__more');
    var tip = summary.querySelector('.staff-news__tip');
    if (!clamp) { return; }
    if (!btn) { return; }
    if (!tip) { return; }
    var entry = { clamp: clamp, btn: btn, tip: tip,
                  card: summary.closest ? summary.closest('.staff-card') : null };
    entries.push(entry);

    btn.addEventListener('mouseenter', function () {
      window.clearTimeout(closeTimer);
      window.clearTimeout(openTimer);
      openTimer = window.setTimeout(function () { open(entry); }, OPEN_DELAY);
    });
    btn.addEventListener('mouseleave', function () {
      window.clearTimeout(openTimer);
      scheduleClose();
    });
    /* Keyboard users get it immediately: a one second wait on focus would
       feel broken. */
    btn.addEventListener('focus', function () { open(entry); });
    btn.addEventListener('blur', function (ev) {
      if (ev.relatedTarget) {
        if (tip.contains(ev.relatedTarget)) { return; }
      }
      scheduleClose();
    });
    /* Click covers touch, where hover does not exist. */
    btn.addEventListener('click', function (ev) {
      ev.preventDefault();
      window.clearTimeout(openTimer);
      if (current === entry) { close(); } else { open(entry); }
    });

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
    clamp.addEventListener('click', function () {
      if (!entry.clipped) { return; }
      window.clearTimeout(openTimer);
      if (current === entry) { close(); } else { open(entry); }
    });

    tip.addEventListener('mouseenter', function () { window.clearTimeout(closeTimer); });
    tip.addEventListener('mouseleave', function () { scheduleClose(); });
    tip.addEventListener('focusout', function (ev) {
      if (ev.relatedTarget) {
        if (tip.contains(ev.relatedTarget)) { return; }
        if (ev.relatedTarget === btn) { return; }
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
    if (current.btn.contains(ev.target)) { return; }
    /* The summary text opens the tooltip, so a click on it must not also be
       treated as a click outside - that closed it again immediately. */
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
