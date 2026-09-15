##parameters=month=''
##title=Staff calendar: one month of events and dated announcements
##
# ============================================================================
# Feeds the full staff calendar page (/staff/calendar, template pt_calendar).
#
# Install: ZMI -> /staff -> Add Script (Python), id "get_staff_calendar_month".
# Living in /staff lets /staff/calendar/index_html reach it by acquisition.
#
# Which month: the `month` parameter, else ?month=YYYY-MM on the request, else
# the current month. Anything malformed or out of range also falls back to the
# current month, so a hand-edited URL can never break the page.
#
# One month is built per request, so there is no navigation limit, months can
# be bookmarked, and the back button works.
#
# Returns:
#   {'ok', 'items_ok', 'key', 'heading', 'is_current', 'current_key',
#    'prev_key', 'prev_heading', 'next_key', 'next_heading',
#    'weeks':  [[cell x 7], ...],
#    'agenda': [{iso, heading, today, past, entries}, ...],
#    'empty'}
#   cell  : {'blank': 1} or {blank, num, iso, label, today, past, entries,
#            more, more_label}
#   The list key is 'entries', never 'items': a TAL path like cell/items
#   finds the dict's items() METHOD before the key and iterates tuples.
#   Avoid keys named items, keys, values, get, copy, pop or update.
#   entry : {kind, kind_label, title, url, when, where, intro, ics,
#            date_label, multi, continued, overflow, pop_id, stamp}
#
# Helpers are copied from get_staff_dashboard_data: Script (Python) objects
# cannot import one another. Keep the two in step when fixing either.
#
# Zope 2.13 / Python 2.7 restricted Python. Measured sandbox: sorted, reversed,
# set and type are NOT available. Keep every non-ASCII character escaped - the
# ZMI stores pasted source as Latin-1.
# ============================================================================

DASH = u'\u2013'     # en dash, escaped on purpose (see above)

# Titles shown in a day cell before "+N more". The rest are still rendered, so
# the page works without JavaScript; staff-calendar.js collapses them.
MAX_VISIBLE = 3

# Longest multi-day item expanded, in days. Guards a bad end date.
SPAN_LIMIT = 92

# A multi-day item with no event_end_date in the catalog can only reveal its
# length (event_length) by loading the object. Items starting further back than
# this are not loaded just to find out; nobody enters a quarter-long event.
LOOKBACK_MONTHS = 3

# The dashboard hides an item after its hide_date. On a calendar that would
# empty every past month, so here hide_date is ignored by default and only
# publication status and show_date apply. Set to 1 to honour hide_date too.
RESPECT_HIDE_DATE = 0

PUBLISHED_STATUS = 'published'

# (folder id, kind, label). Announcements appear only when they carry an
# event_date - typically a deadline.
SOURCES = (('calendar', 'event', u'Event'),
           ('announcements', 'announcement', u'Announcement'))

FIELD_TIME     = ('Time',)
FIELD_LOCATION = ('Location', 'Physical Address')
FIELD_ACCESSORS = ('get', 'getValue', 'value', 'getField', 'field',
                   'getFieldValue', 'getItem', 'item')

DIGITS = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
          '5': 5, '6': 6, '7': 7, '8': 8, '9': 9}

MONTH_NAMES = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December')
WEEKDAY_NAMES = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                 'Friday', 'Saturday')
MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
DOW_OFFSETS = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)


# ---------------------------------------------------------------------------
# helpers shared with get_staff_dashboard_data
# ---------------------------------------------------------------------------

def as_text(value):
    if value is None:
        return u''
    try:
        return u'%s' % (value,)
    except Exception:
        pass
    try:
        return value.decode('utf-8', 'replace')
    except Exception:
        return u''


def meta(brain, name, default=None):
    try:
        value = getattr(brain, name, default)
    except Exception:
        return default
    if value is None:
        return default
    if value == '' or value == 'None':
        return default
    return value


def clock_parts(dt):
    try:
        return (u'%s' % dt.h_12(), u'%02d' % dt.minute(), dt.ampm().upper())
    except Exception:
        pass
    try:
        hour = dt.strftime('%I').lstrip('0') or u'12'
        return (u'%s' % hour, dt.strftime('%M'), dt.strftime('%p').upper())
    except Exception:
        return None


def is_midnight(dt):
    parts = clock_parts(dt)
    if not parts:
        return 1
    return (parts[0] == u'12' and parts[1] == u'00' and parts[2] == u'AM')


def fmt_when(start, end):
    """'10:00-11:00 AM', '9:05 AM-4:30 PM', or empty when no time is known."""
    if start is None:
        return u''
    if is_midnight(start):
        return u''
    a = clock_parts(start)
    if not a:
        return u''
    b = None
    if end is not None and not is_midnight(end):
        b = clock_parts(end)
    if not b:
        return u'%s:%s %s' % (a[0], a[1], a[2])
    if a[2] == b[2]:
        return u'%s:%s%s%s:%s %s' % (a[0], a[1], DASH, b[0], b[1], b[2])
    return u'%s:%s %s%s%s:%s %s' % (a[0], a[1], a[2], DASH, b[0], b[1], b[2])


def count_of(value):
    text = as_text(value).strip()
    if not text:
        return None
    total = None
    for ch in text:
        if ch in DIGITS:
            if total is None:
                total = 0
            total = total * 10 + DIGITS[ch]
        else:
            if total is not None:
                break
    return total


def stamp(dt):
    if dt is None:
        return 0
    try:
        return dt.timeTime()
    except Exception:
        pass
    try:
        return dt.millis()
    except Exception:
        return 0


def visible(brain, now):
    """Published and already announced. See RESPECT_HIDE_DATE."""
    status = as_text(meta(brain, 'getStatus', u'')).strip().lower()
    if status:
        if status != PUBLISHED_STATUS:
            return 0
    show = meta(brain, 'show_date')
    if show is not None:
        try:
            if show > now:
                return 0
        except Exception:
            pass
    if RESPECT_HIDE_DATE:
        hide = meta(brain, 'hide_date')
        if hide is not None:
            try:
                if hide < now:
                    return 0
            except Exception:
                pass
    return 1


def resolve(brain):
    url = u''
    try:
        url = as_text(brain.getURL())
    except Exception:
        pass
    obj = None
    try:
        obj = brain.getObject()
    except Exception:
        return (url, None)
    try:
        target = obj.getProperty('redirect_url', '')
        if target:
            url = as_text(target)
    except Exception:
        pass
    return (url, obj)


def field_value(obj, keys):
    if obj is None:
        return u''
    for key in keys:
        for name in FIELD_ACCESSORS:
            try:
                method = getattr(obj, name, None)
                if method is None:
                    continue
                result = method(key)
            except Exception:
                continue
            text = as_text(result).strip()
            if text and text[:1] != '<':
                return text
        try:
            text = as_text(obj[key]).strip()
            if text and text[:1] != '<':
                return text
        except Exception:
            pass
    return u''


def ics_url(obj):
    if obj is None:
        return u''
    try:
        for sub_id in obj.objectIds():
            name = as_text(sub_id)
            if name[-4:].lower() == '.ics':
                return u'%s/%s' % (as_text(obj.absolute_url()), name)
    except Exception:
        pass
    return u''


def query(folder_id):
    folder = getattr(context, folder_id, None)
    if folder is None:
        return []
    try:
        return list(folder.searchResults(sort_on='event_date',
                                         sort_order='ascending'))
    except Exception:
        pass
    try:
        return list(folder.searchResults())
    except Exception:
        return []


# ---------------------------------------------------------------------------
# date arithmetic - plain numbers, never DateTime addition, which adds 24-hour
# periods and lands on the wrong day across a daylight-saving change
# ---------------------------------------------------------------------------

def is_leap(year):
    if year % 400 == 0:
        return 1
    if year % 100 == 0:
        return 0
    return year % 4 == 0 and 1 or 0


def month_length(year, month):
    if month == 2 and is_leap(year):
        return 29
    return MONTH_LENGTHS[month - 1]


def weekday_of(year, month, day):
    """0 = Sunday. Sakamoto's method."""
    y = year
    if month < 3:
        y = y - 1
    return (y + y // 4 - y // 100 + y // 400 + DOW_OFFSETS[month - 1] + day) % 7


def iso_of(year, month, day):
    return '%04d-%02d-%02d' % (year, month, day)


def iso_t(t):
    return iso_of(t[0], t[1], t[2])


def next_day(t):
    if t[2] < month_length(t[0], t[1]):
        return (t[0], t[1], t[2] + 1)
    if t[1] < 12:
        return (t[0], t[1] + 1, 1)
    return (t[0] + 1, 1, 1)


def add_days(t, days):
    steps = 0
    while steps < days and steps < SPAN_LIMIT:
        t = next_day(t)
        steps = steps + 1
    return t


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return (index // 12, index % 12 + 1)


def ymd(dt):
    if dt is None:
        return None
    try:
        return (int(dt.year()), int(dt.month()), int(dt.day()))
    except Exception:
        pass
    try:
        return (int(dt.strftime('%Y')), int(dt.strftime('%m')),
                int(dt.strftime('%d')))
    except Exception:
        return None


def month_key(year, month):
    return u'%04d-%02d' % (year, month)


def month_heading(year, month):
    return u'%s %d' % (MONTH_NAMES[month - 1], year)


def day_label(t):
    """'Thursday, September 17'"""
    return u'%s, %s %d' % (WEEKDAY_NAMES[weekday_of(t[0], t[1], t[2])],
                           MONTH_NAMES[t[1] - 1], t[2])


def date_label(a, b):
    """'Thursday, September 17, 2026', 'September 17-19, 2026',
    'September 28 - October 9, 2026', or across years with both."""
    if b is None or b == a:
        return u'%s, %d' % (day_label(a), a[0])
    if a[0] != b[0]:
        return u'%s %d, %d %s %s %d, %d' % (MONTH_NAMES[a[1] - 1], a[2], a[0],
                                           DASH, MONTH_NAMES[b[1] - 1], b[2], b[0])
    if a[1] != b[1]:
        return u'%s %d %s %s %d, %d' % (MONTH_NAMES[a[1] - 1], a[2], DASH,
                                        MONTH_NAMES[b[1] - 1], b[2], a[0])
    return u'%s %d%s%d, %d' % (MONTH_NAMES[a[1] - 1], a[2], DASH, b[2], a[0])


def all_digits(text):
    if not text:
        return 0
    for ch in text:
        if ch not in DIGITS:
            return 0
    return 1


def parse_month(value):
    """(year, month) from 'YYYY-MM', or None."""
    text = as_text(value).strip()
    if len(text) != 7:
        return None
    if text[4] != '-':
        return None
    if not all_digits(text[:4]):
        return None
    if not all_digits(text[5:]):
        return None
    year = count_of(text[:4])
    number = count_of(text[5:])
    if number < 1 or number > 12:
        return None
    if year < 1970 or year > 2100:
        return None
    return (year, number)


def by_time(row):
    return (row['stamp'], row['title'].lower())


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
# Wrapped in try/except for the same reason as the dashboard script: an
# exception here would fail the template's root define and blank the page.

try:
    now = context.ZopeTime()
    today = ymd(now)
    today_iso = iso_t(today)

    requested = month
    if not requested:
        try:
            requested = context.REQUEST.form.get('month', '')
        except Exception:
            requested = ''
    picked = parse_month(requested)
    if picked is None:
        picked = (today[0], today[1])
    year = picked[0]
    mon = picked[1]

    length = month_length(year, mon)
    lead = weekday_of(year, mon, 1)
    first_iso = iso_of(year, mon, 1)
    last_iso = iso_of(year, mon, length)
    back = shift_month(year, mon, 0 - LOOKBACK_MONTHS)
    lookback_iso = iso_of(back[0], back[1], 1)
    prev_t = shift_month(year, mon, -1)
    next_t = shift_month(year, mon, 1)

    # ---- items by day -----------------------------------------------------
    by_day = {}
    items_ok = 1
    for source in SOURCES:
        try:
            brains = query(source[0])
        except Exception:
            items_ok = 0
            continue
        for brain in brains:
            # One unreadable document must not cost the whole month.
            try:
                if not visible(brain, now):
                    continue
                start = meta(brain, 'event_date')
                start_t = ymd(start)
                if start_t is None:
                    continue                  # undated announcement
                start_iso = iso_t(start_t)
                if start_iso > last_iso:
                    continue

                end = meta(brain, 'event_end_date')
                end_t = ymd(end)
                if end_t is not None:
                    if iso_t(end_t) <= start_iso:
                        end_t = None
                if end_t is not None:
                    if iso_t(end_t) < first_iso:
                        continue
                else:
                    if start_iso < lookback_iso:
                        continue

                title = as_text(meta(brain, 'title', u''))
                if not title:
                    continue

                url, obj = resolve(brain)
                if end_t is None:
                    try:
                        days = count_of(obj.getProperty('event_length', None))
                    except Exception:
                        days = None
                    if days is not None and days > 1:
                        end_t = add_days(start_t, days - 1)
                finish_t = end_t or start_t
                finish_iso = iso_t(finish_t)
                if finish_iso < first_iso:
                    continue

                when = field_value(obj, FIELD_TIME)
                if not when:
                    when = fmt_when(start, end)
                record = {
                    'kind':       source[1],
                    'kind_label': source[2],
                    'title':      title,
                    'url':        url,
                    'when':       when,
                    'where':      field_value(obj, FIELD_LOCATION),
                    'intro':      as_text(meta(brain, 'intro', u'')).strip(),
                    'ics':        source[1] == 'event' and ics_url(obj) or u'',
                    'date_label': date_label(start_t, end_t),
                    'multi':      finish_iso != start_iso and 1 or 0,
                    'stamp':      stamp(start),
                }

                cursor = start_t
                if start_iso < first_iso:
                    cursor = (year, mon, 1)
                steps = 0
                while steps < SPAN_LIMIT:
                    key = iso_t(cursor)
                    if key > finish_iso or key > last_iso:
                        break
                    occurrence = record.copy()
                    occurrence['continued'] = key > start_iso and 1 or 0
                    if key not in by_day:
                        by_day[key] = []
                    by_day[key].append(occurrence)
                    cursor = next_day(cursor)
                    steps = steps + 1
            except Exception:
                continue

    # ---- grid and agenda --------------------------------------------------
    cells = []
    while len(cells) < lead:
        cells.append({'blank': 1})
    agenda = []
    day_num = 1
    while day_num <= length:
        key = iso_of(year, mon, day_num)
        entries = by_day.get(key, [])
        entries.sort(key=by_time)
        position = 0
        for occurrence in entries:
            occurrence['pop_id'] = u'staff-fc-%s-%d' % (key, position)
            occurrence['overflow'] = position >= MAX_VISIBLE and 1 or 0
            position = position + 1
        more = 0
        if len(entries) > MAX_VISIBLE:
            more = len(entries) - MAX_VISIBLE
        label = day_label((year, mon, day_num))
        is_today = key == today_iso and 1 or 0
        is_past = key < today_iso and 1 or 0
        cells.append({'blank': 0, 'num': u'%d' % day_num, 'iso': key,
                      'label': label, 'today': is_today, 'past': is_past,
                      'entries': entries, 'more': more,
                      'more_label': u'+%d more' % more})
        if entries:
            agenda.append({'iso': key, 'heading': label, 'today': is_today,
                           'past': is_past, 'entries': entries})
        day_num = day_num + 1
    while len(cells) % 7:
        cells.append({'blank': 1})

    weeks = []
    index = 0
    while index < len(cells):
        weeks.append(cells[index:index + 7])
        index = index + 7

    result = {
        'ok': 1,
        'items_ok': items_ok,
        'key': month_key(year, mon),
        'heading': month_heading(year, mon),
        'is_current': (year == today[0] and mon == today[1]) and 1 or 0,
        'current_key': month_key(today[0], today[1]),
        'prev_key': month_key(prev_t[0], prev_t[1]),
        'prev_heading': month_heading(prev_t[0], prev_t[1]),
        'next_key': month_key(next_t[0], next_t[1]),
        'next_heading': month_heading(next_t[0], next_t[1]),
        'weeks': weeks,
        'agenda': agenda,
        'empty': u'No events or announcements in %s.' % MONTH_NAMES[mon - 1],
    }
except Exception:
    result = {'ok': 0}

return result
