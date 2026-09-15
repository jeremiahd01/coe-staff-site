/* Staff calendar page behaviour.
   Deployed as the File object /staff/staff-calendar.js and loaded by
   pt_calendar. Keep it pure ASCII: Zope may serve it with a Latin-1 charset.

   The page works without this file: titles are links, busy days list every
   title, and phones get the agenda. This adds the details popups and the
   "+N more" collapse. */
(function () {
  var root = document.querySelector('.staff-fullcal');
  if (!root) { return; }
  root.classList.add('is-enhanced');

  /* ---- "+N more" -------------------------------------------------------
     The overflow titles are already in the page; CSS hides them once the
     root carries is-enhanced, and the button toggles them back. */
  Array.prototype.forEach.call(root.querySelectorAll('.staff-fullcal__more'), function (btn) {
    var cell = btn.closest('.staff-fullcal__cell');
    var text = btn.querySelector('.staff-fullcal__more-text');
    if (!cell || !text) { return; }
    var collapsed = text.textContent;
    btn.hidden = false;
    btn.addEventListener('click', function () {
      var open = !cell.classList.contains('is-expanded');
      cell.classList.toggle('is-expanded', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      text.textContent = open ? 'Show fewer' : collapsed;
    });
  });

  /* ---- Details popups ---------------------------------------------------
     Mouse: opens after a short hover delay, and stays open while the pointer
     is over the link or the popup (WCAG 1.4.13).
     Keyboard: opens on focus; Tab moves into the popup's links because the
     popup follows its link in the DOM. Escape closes.
     Touch: the first tap opens the popup, a second tap follows the link.
     Phones never get here - the agenda shows details inline. */
  var OPEN_DELAY = 250;
  var CLOSE_DELAY = 200;
  var GAP = 6;
  var EDGE = 8;
  var wide = window.matchMedia('(min-width: 768px)');
  var current = null;
  var openTimer = null;
  var closeTimer = null;
  var lastPointer = '';
  /* Set while close() hands focus back to a title, so that focus does not
     immediately reopen the popup Escape just closed. */
  var returningFocus = false;

  function place(entry) {
    var pop = entry.pop;
    pop.style.left = '0px';
    pop.style.top = '0px';
    var rootBox = root.getBoundingClientRect();
    var linkBox = entry.link.getBoundingClientRect();
    var popBox = pop.getBoundingClientRect();

    var left = linkBox.left - rootBox.left;
    var maxLeft = root.clientWidth - popBox.width - EDGE;
    if (left > maxLeft) { left = maxLeft; }
    if (left < EDGE) { left = EDGE; }

    var top = linkBox.bottom - rootBox.top + GAP;
    var roomBelow = window.innerHeight - linkBox.bottom;
    if (roomBelow < popBox.height + GAP && linkBox.top > popBox.height + GAP) {
      top = linkBox.top - rootBox.top - popBox.height - GAP;
    }
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
  }

  function close(returnFocus) {
    window.clearTimeout(openTimer);
    window.clearTimeout(closeTimer);
    if (!current) { return; }
    var closing = current;
    current = null;
    closing.pop.hidden = true;
    closing.link.removeAttribute('aria-expanded');
    if (returnFocus) {
      returningFocus = true;
      closing.link.focus();
      returningFocus = false;
    }
  }

  function open(entry) {
    window.clearTimeout(closeTimer);
    if (current === entry) { return; }
    close(false);
    entry.pop.hidden = false;
    entry.link.setAttribute('aria-expanded', 'true');
    place(entry);
    current = entry;
  }

  function scheduleClose() {
    window.clearTimeout(closeTimer);
    closeTimer = window.setTimeout(function () { close(false); }, CLOSE_DELAY);
  }

  Array.prototype.forEach.call(root.querySelectorAll('a.staff-fullcal__link[data-pop]'), function (link) {
    var pop = document.getElementById(link.getAttribute('data-pop'));
    if (!pop) { return; }
    var entry = { link: link, pop: pop };

    link.addEventListener('pointerdown', function (ev) {
      lastPointer = ev.pointerType || 'mouse';
    });

    link.addEventListener('mouseenter', function () {
      if (!wide.matches) { return; }
      window.clearTimeout(closeTimer);
      window.clearTimeout(openTimer);
      openTimer = window.setTimeout(function () { open(entry); }, OPEN_DELAY);
    });
    link.addEventListener('mouseleave', function () {
      window.clearTimeout(openTimer);
      scheduleClose();
    });

    link.addEventListener('focus', function () {
      if (!wide.matches) { return; }
      if (returningFocus) { return; }
      /* A tap also focuses the link; leave touch to the click handler so the
         first tap opens rather than opening and navigating at once. */
      if (lastPointer === 'touch' || lastPointer === 'pen') { return; }
      open(entry);
    });
    link.addEventListener('blur', function (ev) {
      if (ev.relatedTarget && pop.contains(ev.relatedTarget)) { return; }
      scheduleClose();
    });

    link.addEventListener('click', function (ev) {
      var touch = lastPointer === 'touch' || lastPointer === 'pen';
      lastPointer = '';
      if (!wide.matches || !touch) { return; }
      if (current !== entry) {
        ev.preventDefault();
        open(entry);
      }
    });

    pop.addEventListener('mouseenter', function () { window.clearTimeout(closeTimer); });
    pop.addEventListener('mouseleave', scheduleClose);
    pop.addEventListener('focusout', function (ev) {
      if (ev.relatedTarget) {
        if (pop.contains(ev.relatedTarget)) { return; }
        if (ev.relatedTarget === link) { return; }
      }
      scheduleClose();
    });
  });

  document.addEventListener('keydown', function (ev) {
    lastPointer = '';
    if (ev.key !== 'Escape' || !current) { return; }
    close(current.pop.contains(document.activeElement));
  });

  document.addEventListener('click', function (ev) {
    if (!current) { return; }
    if (current.pop.contains(ev.target)) { return; }
    if (current.link.contains(ev.target)) { return; }
    close(false);
  });

  window.addEventListener('resize', function () { close(false); });
}());
