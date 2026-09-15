##parameters=announcement_limit=5, event_limit=5
##title=Dashboard data: announcements and upcoming events
##
# ============================================================================
# Feeds the Staff Hub dashboard.
#
# Install: ZMI -> /staff -> Add Script (Python), id "get_staff_dashboard_data".
#
# Returns:
#   {'announcements': [ {icon, title, summary, due, url}, ... ],
#    'events':        [ {month, day, title, when, where, url}, ... ]}
#
# Those keys are exactly what pt_homepage iterates.
#
# Reads through each Purdue Event Manager's own ZCatalog rather than walking
# objects. The catalog already indexes documents inside the year subfolders
# (calendar/2026/...), sorts on event_date, and returns metadata without waking
# each object. Only the handful of documents actually displayed get loaded, and
# only to read redirect_url, which is not in the catalog metadata.
#
# Confirmed catalog schema on both managers:
#   indexes  : event_date, event_end_date, getStatus, hide_date, id, keywords,
#              kwKeywords, path, position, priority, show_date, sort_index,
#              title, type
#   metadata : the above plus intro, tags, meta_type
#
# Zope 2.13 / Python 2.7 restricted Python. Measured sandbox: sorted, reversed,
# set and type are NOT available; int, range, callable and isinstance are. See
# scripts/introspect_sandbox.py and the README.
# ============================================================================

import json

DASH = u'\u2013'       # en dash. Written as an escape, NOT as a literal:
                       # the ZMI stores pasted source as Latin-1, which turns
                       # a literal en dash into mojibake ('Oct 27 a Nov 10').
                       # Keep every non-ASCII character in this file escaped.
# Icon vocabulary, agreed with the PM. Matched against whole keywords, in this
# order - so an item tagged both "awards" and "deadline" gets the trophy.
# Verified against the site kit: all nine render, including the four that are
# Font Awesome Pro only (shield-check, calendar-exclamation, circle-book-open,
# clapperboard-play).
ICON_BY_KEYWORD = (
    ('new-staff',       'fa-user-group'),
    ('staff-event',     'fa-calendar-star'),
    ('benefits',        'fa-shield-check'),
    ('awards',          'fa-trophy'),
    ('event',           'fa-calendar-days'),
    ('deadline',        'fa-calendar-exclamation'),
    ('training',        'fa-circle-book-open'),
    ('recording',       'fa-clapperboard-play'),
    ('documentation',   'fa-file-lines'),
    ('high-importance', 'fa-circle-exclamation'),
    ('general',         'fa-newspaper'),
)

# No keyword, or none from the vocabulary above.
DEFAULT_ICON = 'fa-newspaper'

# An announcement keyed with this in `keywords` is pinned to position one.
# Matched case-insensitively as a whole keyword, so "featured-story" does not
# count. If several carry it, the newest wins.
FEATURED_KEYWORD = 'featured'

# The catalog's getStatus index holds 'draft' or 'published'. It is the real
# publication state; show_date only schedules when a published item appears.
# A draft can carry no show_date at all, which the date check alone reads as
# "publish immediately" - so both checks are needed.
PUBLISHED_STATUS = 'published'

# priority is a dropdown from 0 (lowest) to 4 (highest), rendered as strings
# like "2 - medium". The leading digit is the rank and sorts DESCENDING, so 4
# comes first. Parsing the digit rather than matching the whole label means the
# wording can change without touching this.
#
# A missing or unparseable priority is treated as 2, the middle of the range
# and what the dropdown defaults to -- rather than as lowest, which would bury
# an announcement whose priority simply was not set.
PRIORITY_DEFAULT = 2
DIGITS = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
          '5': 5, '6': 6, '7': 7, '8': 8, '9': 9}

# EventDocument keeps its template fields in a mapping keyed by human-readable
# labels, exposed through keys():
#   Hosted By, Time, Location, Contact Name, Contact Phone, Contact Email,
#   Open To, Priority, School or Program, College Calendar, Physical Address
# That is why no attribute name ever matched -- "Contact Name" cannot be one.
# Note values()/items() are ObjectManager's and return the document's
# sub-objects (its image and .ics), not these field values.
FIELD_TIME     = ('Time',)
FIELD_LOCATION = ('Location', 'Physical Address')

# Which accessor the product exposes for reading a field by key is not known,
# so each is tried in turn and the first usable answer wins.
FIELD_ACCESSORS = ('get', 'getValue', 'value', 'getField', 'field',
                   'getFieldValue', 'getItem', 'item')

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def as_text(value):
    """Safe text, never raises. Avoids unicode/basestring/isinstance, which
    restricted Python may withhold."""
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
    """Catalog metadata off a brain, tolerant of a missing column."""
    try:
        value = getattr(brain, name, default)
    except Exception:
        return default
    if value is None:
        return default
    # Missing DateIndex values come back as the string 'None'
    if value == '' or value == 'None':
        return default
    return value


def clock_parts(dt):
    """(hour, minute, MERIDIEM) as strings, or None."""
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
    hour, minute, ampm = parts
    return (hour == u'12' and minute == u'00' and ampm == u'AM')


def fmt_when(start, end):
    """'10:00-11:00 AM', '9:05 AM-4:30 PM', or empty.

    Returns nothing rather than "All day" when no time is known. event_date is
    stored at midnight unless someone enters a time, so "All day" would have
    been asserted for every event whether or not it ran all day - a claim the
    data does not support. The card simply omits the time line instead.
    """
    if start is None:
        return u''
    if is_midnight(start):
        return u''
    a = clock_parts(start)
    if not a:
        return u''
    ah, am, ap = a
    b = None
    if end is not None and not is_midnight(end):
        b = clock_parts(end)
    if not b:
        return u'%s:%s %s' % (ah, am, ap)
    bh, bm, bp = b
    if ap == bp:
        return u'%s:%s%s%s:%s %s' % (ah, am, DASH, bh, bm, bp)
    return u'%s:%s %s%s%s:%s %s' % (ah, am, ap, DASH, bh, bm, bp)


def month_abbr(dt):
    try:
        return as_text(dt.strftime('%b'))
    except Exception:
        return u''


def day_number(dt):
    try:
        return as_text(dt.day())
    except Exception:
        pass
    try:
        return as_text(dt.strftime('%d').lstrip('0'))
    except Exception:
        return u''


def keyword_list(keywords):
    """Normalised whole keywords: trimmed and lowercased, one per entry.

    Deliberately does NOT split on punctuation. Tokenising would make
    "featured-story" match "featured", which is not what the pinning rule
    means. `keywords` may also be a bare string, and iterating a string would
    yield characters, so a string is wrapped first.
    """
    items = keywords
    if items is None:
        return []
    if hasattr(items, 'strip'):
        items = [items]
    out = []
    try:
        for entry in items:
            text = as_text(entry).strip().lower()
            if text:
                out.append(text)
    except Exception:
        pass
    return out


def is_featured(keywords):
    for keyword in keyword_list(keywords):
        if keyword == FEATURED_KEYWORD:
            return 1
    return 0


def pick_icon(keywords):
    """Whole-keyword match against the vocabulary, in chart order.

    Substring matching is deliberately not used: an earlier version matched
    "ai" inside "training" and gave a training announcement the AI icon.
    """
    words = keyword_list(keywords)
    for pair in ICON_BY_KEYWORD:
        if pair[0] in words:
            return pair[1]
    return DEFAULT_ICON


def count_of(value):
    """Leading integer from an int or a string, or None.

    event_length arrives as an int property, but going through text avoids
    comparing a str to an int, which in Python 2 succeeds and gives nonsense.
    """
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


def day_key(dt):
    """Comparable YYYY/MM/DD string, for deciding whether two dates differ."""
    try:
        return as_text(dt.Date())
    except Exception:
        pass
    try:
        return as_text(dt.strftime('%Y-%m-%d'))
    except Exception:
        return u''


def span_end(brain, obj, start):
    """Last day of a multi-day item, or None when it is a single day.

    Prefers event_end_date, which is catalog metadata. event_length is not, so
    it is only read off the object as a fallback -- and it counts days
    inclusively, so a length of 3 starting Sep 3 ends Sep 5.
    """
    end = meta(brain, 'event_end_date')
    if end is not None:
        start_key = day_key(start)
        end_key = day_key(end)
        if end_key and start_key:
            if end_key > start_key:
                return end
        return None

    length = None
    if obj is not None:
        try:
            length = obj.getProperty('event_length', None)
        except Exception:
            length = None
    days = count_of(length)
    if days is None:
        return None
    if days < 2:
        return None
    try:
        return start + (days - 1)
    except Exception:
        return None


def date_display(start, end):
    """'Sep 30', 'Sep 3-5' within a month, or 'Sep 30 - Oct 2' across one."""
    if start is None:
        return u''
    start_month = month_abbr(start)
    start_day = day_number(start)
    if not start_month:
        return u''
    if not start_day:
        return u''
    if end is None:
        return u'%s %s' % (start_month, start_day)
    end_month = month_abbr(end)
    end_day = day_number(end)
    if not end_month:
        return u'%s %s' % (start_month, start_day)
    if not end_day:
        return u'%s %s' % (start_month, start_day)
    if end_month == start_month:
        return u'%s %s%s%s' % (start_month, start_day, DASH, end_day)
    return u'%s %s %s %s %s' % (start_month, start_day, DASH, end_month, end_day)


def priority_rank(value):
    """Leading digit of "2 - medium". 0 is lowest, 4 is highest."""
    text = as_text(value).strip()
    if not text:
        return PRIORITY_DEFAULT
    rank = None
    for ch in text:
        if ch in DIGITS:
            if rank is None:
                rank = 0
            rank = rank * 10 + DIGITS[ch]
        else:
            if rank is not None:
                break
    if rank is None:
        return PRIORITY_DEFAULT
    return rank


def stamp(dt):
    """Sortable number from a date, newest highest."""
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


def order_key(row):
    return (row[0], row[1], row[2])


def visible(brain, now):
    """Published, and inside its show_date / hide_date window.

    Status is checked only when the catalog actually reports one. An explicit
    status that is not "published" hides the item, so a future 'archived' or
    'pending' is excluded too. But a missing or unreadable status is treated as
    visible rather than hidden: requiring the field outright would empty both
    widgets if the metadata column were ever absent, and a blank dashboard is a
    worse failure than showing an item whose state we cannot read.
    """
    status = as_text(meta(brain, 'getStatus', u'')).strip().lower()
    if status:
        if status != PUBLISHED_STATUS:
            return 0

    show = meta(brain, 'show_date')
    hide = meta(brain, 'hide_date')
    if show is not None:
        try:
            if show > now:
                return 0
        except Exception:
            pass
    if hide is not None:
        try:
            if hide < now:
                return 0
        except Exception:
            pass
    return 1


def resolve(brain):
    """(url, object-or-None). redirect_url is not catalog metadata, so the
    object is loaded -- but only for the few documents actually displayed."""
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
    """Read a template field by its label, e.g. 'Time' or 'Location'."""
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
            # reject object reprs: a mis-hit can return a sub-object
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
    """Each event document auto-generates its own .ics file as a sub-object,
    which is what Add to Outlook links to. No calendar file to build."""
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


def query(folder_id, sort_on, sort_order):
    """(folder, brains). The folder comes back so it can guard against values
    acquired from the manager."""
    folder = getattr(context, folder_id, None)
    if folder is None:
        return (None, [])
    try:
        return (folder, list(folder.searchResults(sort_on=sort_on,
                                                  sort_order=sort_order)))
    except Exception:
        pass
    try:                       # catalog unhappy: fall back to an unsorted read
        return (folder, list(folder.searchResults()))
    except Exception:
        return (folder, [])


# ---------------------------------------------------------------------------
# Why the two blocks below are wrapped in try/except
#
# The template calls this script from a tal:define on its ROOT element. TALES
# "| nothing" only catches a failed *lookup* -- the script not existing -- and
# does NOT catch an exception raised inside it. So an error here would fail the
# root define and the whole template would render nothing at all.
#
# Returning empty lists instead lets the template fall back to its placeholder
# content, so a broken widget shows stale copy rather than blanking the page,
# and one widget cannot take the other down with it.
# ---------------------------------------------------------------------------

now = context.ZopeTime()
try:
    today = now.earliestTime()          # midnight, so today's events still show
except Exception:
    today = now


# ---------------------------------------------------------------------------
# Upcoming events -- /calendar, soonest first
# ---------------------------------------------------------------------------
events = []
events_ok = 1
cal_brains = []
try:
    cal_folder, cal_brains = query('calendar', 'event_date', 'ascending')
    for brain in cal_brains:
        if len(events) >= event_limit:
            break
        if not visible(brain, now):
            continue
        start = meta(brain, 'event_date')
        if start is None:
            continue
        try:
            if start < today:
                continue
        except Exception:
            pass                            # incomparable: fail open
        title = as_text(meta(brain, 'title', u''))
        if not title:
            continue          # unreadable or untitled: better absent than blank
        url, obj = resolve(brain)
        # The admin-authored Time string wins. Only when it is absent do we derive
        # a time from event_date, which is stored at midnight unless someone has
        # entered one -- in which case this reads "All day".
        when = field_value(obj, FIELD_TIME)
        if not when:
            when = fmt_when(start, meta(brain, 'event_end_date'))
        events.append({
            'month': month_abbr(start),
            'day':   day_number(start),
            'title': title,
            'when':  when,
            'where': field_value(obj, FIELD_LOCATION),
            'ics':   ics_url(obj),
            'url':   url,
        })
except Exception:
    # one widget failing must not take the page down; see note above
    events = []
    events_ok = 0


# ---------------------------------------------------------------------------
# Announcements -- /announcements
#
# Order: the featured item first, then by priority (4 highest down to 0), then
# newest first. event_date is empty on news items, so recency comes from show_date;
# when an announcement does carry an event_date it is a deadline and becomes
# the "Closes <date>" line.
#
# Everything visible is collected before sorting, rather than stopping at the
# limit, because a featured or high-priority item further down the catalog
# result has to be able to reach position one.
# ---------------------------------------------------------------------------
announcements_ok = 1
ann_brains = []
try:
    ann_folder, ann_brains = query('announcements', 'show_date', 'descending')

    rows = []
    for brain in ann_brains:
        if not visible(brain, now):
            continue
        keywords = meta(brain, 'keywords', ())
        featured = is_featured(keywords)
        # negated: the list sorts ascending, and higher priority must come first
        rows.append((0 - priority_rank(meta(brain, 'priority')),
                     -stamp(meta(brain, 'show_date')),
                     as_text(meta(brain, 'id', u'')),   # stable tie-break
                     featured,
                     brain))

    rows.sort(key=order_key)

    # Pin the newest featured item. Sorting by -show_date already put the newest
    # first among equals, so the first featured row encountered is the newest one.
    featured_row = None
    for row in rows:
        if row[3]:
            featured_row = row
            break
    if featured_row is not None:
        ordered = [featured_row]
        for row in rows:
            if row is not featured_row:
                ordered.append(row)
    else:
        ordered = rows

    announcements = []
    for row in ordered[:announcement_limit]:
        brain = row[4]
        is_first_featured = (featured_row is not None and row is featured_row)
        title = as_text(meta(brain, 'title', u''))
        if not title:
            continue          # unreadable or untitled: better absent than blank
        url, obj = resolve(brain)
        # 'due' holds a plain date or date range, not only a deadline: the
        # "Closes" wording is gone and event_length may widen it to a span.
        start = meta(brain, 'event_date')
        due = date_display(start, span_end(brain, obj, start))
        announcements.append({
            'icon':     pick_icon(meta(brain, 'keywords', ())),
            'featured': is_first_featured and 1 or 0,
            'title':    title,
            'summary':  as_text(meta(brain, 'intro', u'')),
            'due':      due,
            'url':      url,
        })
except Exception:
    # one widget failing must not take the page down; see note above
    announcements = []
    announcements_ok = 0


# ---------------------------------------------------------------------------
# Events Calendar - month grids for the current month and the next eleven
#
# Dates are built with plain year/month/day arithmetic, never DateTime
# addition. Adding days to a DateTime adds exact 24-hour periods, so across a
# daylight-saving change a midnight date lands at 23:00 the day before and
# .day() reports the wrong date. Arithmetic on the numbers cannot drift.
#
# Every month in the window is emitted with all but the first hidden, so paging
# needs no request. Only days that have events become buttons; each day's
# events are emitted alongside as a panel for dashboard.js to reveal.
# ---------------------------------------------------------------------------
CALENDAR_MONTHS = 12
SPAN_LIMIT = 92            # longest multi-day event we will expand, in days

MONTH_NAMES = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December')
WEEKDAY_NAMES = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                 'Friday', 'Saturday')
MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
DOW_OFFSETS = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)


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
    """0 = Sunday. Sakamoto's method - no DateTime, no timezone."""
    y = year
    if month < 3:
        y = y - 1
    return (y + y // 4 - y // 100 + y // 400 + DOW_OFFSETS[month - 1] + day) % 7


def iso_of(year, month, day):
    return '%04d-%02d-%02d' % (year, month, day)


def next_day(year, month, day):
    if day < month_length(year, month):
        return (year, month, day + 1)
    if month < 12:
        return (year, month + 1, 1)
    return (year + 1, 1, 1)


def entry_order(entry):
    return (entry['stamp'], entry['title'].lower())


def count_phrase(entries):
    """'2 events', '1 announcement', '4 events and 1 announcement'."""
    event_count = 0
    announcement_count = 0
    for entry in entries:
        if entry['kind'] == 'announcement':
            announcement_count = announcement_count + 1
        else:
            event_count = event_count + 1
    parts = []
    if event_count == 1:
        parts.append(u'1 event')
    elif event_count:
        parts.append(u'%d events' % event_count)
    if announcement_count == 1:
        parts.append(u'1 announcement')
    elif announcement_count:
        parts.append(u'%d announcements' % announcement_count)
    return u' and '.join(parts)


def ymd(dt):
    """(year, month, day) as ints from a Zope DateTime or a datetime."""
    if dt is None:
        return None
    try:
        return (int(dt.year()), int(dt.month()), int(dt.day()))
    except Exception:
        pass
    try:
        return (int(dt.strftime('%Y')), int(dt.strftime('%m')), int(dt.strftime('%d')))
    except Exception:
        return None


calendar_months = []
calendar_ok = 1
try:
    today_ymd = ymd(now)
    today_iso = iso_of(today_ymd[0], today_ymd[1], today_ymd[2])

    window = []
    year = today_ymd[0]
    month = today_ymd[1]
    while len(window) < CALENDAR_MONTHS:
        window.append((year, month))
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    first_iso = iso_of(window[0][0], window[0][1], 1)
    last_iso = iso_of(window[-1][0], window[-1][1],
                      month_length(window[-1][0], window[-1][1]))

    # Every event day inside the window, mapped to its entries. Dated
    # announcements (usually deadlines) join the events, on their event_date
    # or across their range. Both lists come from the reads above, so this
    # costs no extra catalog query.
    tagged = []
    for brain in cal_brains:
        tagged.append((brain, 'event'))
    for brain in ann_brains:
        tagged.append((brain, 'announcement'))

    by_day = {}
    for row in tagged:
        brain = row[0]
        if not visible(brain, now):
            continue
        start = meta(brain, 'event_date')
        start_ymd = ymd(start)
        if start_ymd is None:
            continue
        finish = meta(brain, 'event_end_date')
        finish_ymd = ymd(finish) or start_ymd
        start_iso = iso_of(start_ymd[0], start_ymd[1], start_ymd[2])
        finish_iso = iso_of(finish_ymd[0], finish_ymd[1], finish_ymd[2])
        if finish_iso < start_iso:
            finish_iso = start_iso
        if finish_iso < first_iso:
            continue
        if start_iso > last_iso:
            continue
        title = as_text(meta(brain, 'title', u''))
        if not title:
            continue

        url, obj = resolve(brain)
        when = field_value(obj, FIELD_TIME)
        if not when:
            when = fmt_when(start, finish)
        where = field_value(obj, FIELD_LOCATION)
        parts = []
        if when:
            parts.append(when)
        if where:
            parts.append(where)
        entry = {'title': title, 'url': url, 'meta': u' | '.join(parts),
                 'kind': row[1], 'stamp': stamp(start)}

        # a multi-day event is listed on every day it covers
        cursor = start_ymd
        steps = 0
        while steps < SPAN_LIMIT:
            key = iso_of(cursor[0], cursor[1], cursor[2])
            if key > finish_iso:
                break
            if key >= first_iso and key <= last_iso:
                if key not in by_day:
                    by_day[key] = []
                by_day[key].append(entry)
            cursor = next_day(cursor[0], cursor[1], cursor[2])
            steps = steps + 1

    # Two sources were appended one after the other; put each day back in
    # time order so a 9 AM event is not listed after a 5 PM deadline.
    for key in by_day.keys():
        by_day[key].sort(key=entry_order)

    position = 0
    for pair in window:
        year = pair[0]
        month = pair[1]
        length = month_length(year, month)
        lead = weekday_of(year, month, 1)
        month_name = MONTH_NAMES[month - 1]

        # Which event day opens selected: in the current month the first one
        # from today onward, otherwise the month's first.
        event_days = []
        day_num = 1
        while day_num <= length:
            key = iso_of(year, month, day_num)
            if key in by_day:
                event_days.append(key)
            day_num = day_num + 1
        selected_iso = ''
        for key in event_days:
            if position > 0 or key >= today_iso:
                selected_iso = key
                break
        if not selected_iso and event_days:
            selected_iso = event_days[0]

        cells = []
        while len(cells) < lead:
            cells.append({'blank': 1})
        panels = []
        day_num = 1
        while day_num <= length:
            key = iso_of(year, month, day_num)
            entries = by_day.get(key, [])
            count_here = len(entries)
            label = u'%s, %s %d' % (WEEKDAY_NAMES[(lead + day_num - 1) % 7],
                                    month_name, day_num)
            if count_here:
                aria = u'%s, %s' % (label, count_phrase(entries))
            else:
                aria = label
            is_selected = key == selected_iso and 1 or 0
            cells.append({'blank': 0, 'num': u'%d' % day_num, 'iso': key,
                          'today': key == today_iso and 1 or 0,
                          'past': key < today_iso and 1 or 0,
                          'count': count_here, 'selected': is_selected,
                          'aria': aria})
            if count_here:
                panels.append({'iso': key, 'heading': label,
                               'selected': is_selected, 'events': entries})
            day_num = day_num + 1
        while len(cells) % 7:
            cells.append({'blank': 1})

        weeks = []
        index = 0
        while index < len(cells):
            weeks.append(cells[index:index + 7])
            index = index + 7

        calendar_months.append({
            'key': u'%04d-%02d' % (year, month),
            'heading': u'%s %d' % (month_name, year),
            'visible': position == 0 and 1 or 0,
            'weeks': weeks,
            'days': panels,
            'empty': u'No events or announcements in %s.' % month_name,
        })
        position = position + 1
except Exception:
    calendar_months = []
    calendar_ok = 0


# ---------------------------------------------------------------------------
# Admin-managed link lists
#
# Each list is a JSON array of {"label", "url", "icon", "summary"} held in a
# text property on the dashboard_settings folder, so an admin page can rewrite
# one property atomically.
#
# Absent, empty or unparseable settings return an empty list and the template
# falls back to the lists written into the template itself. That means the
# dashboard works before any settings exist, and a bad save degrades to the
# previous design rather than an empty card.
#
# Parsing is per-entry: one malformed row is skipped rather than discarding the
# whole list. JSON fails wholesale where a line-based format fails per-row, so
# the entry-level guard matters more here.
# ---------------------------------------------------------------------------
SETTINGS_FOLDER = 'dashboard_settings'


def link_list(name):
    folder = getattr(context, SETTINGS_FOLDER, None)
    if folder is None:
        return []
    try:
        raw = folder.getProperty(name, '')
    except Exception:
        return []
    text = as_text(raw).strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except Exception:
        return []

    out = []
    try:
        for entry in data:
            try:
                label = as_text(entry.get('label', u'')).strip()
                url = as_text(entry.get('url', u'')).strip()
                if not label:
                    continue        # nothing to render
                if not url:
                    continue        # a link with no destination is not a link
                out.append({
                    'label':   label,
                    'url':     url,
                    'icon':    as_text(entry.get('icon', u'')).strip(),
                    'summary': as_text(entry.get('summary', u'')).strip(),
                })
            except Exception:
                continue            # skip this row, keep the rest
    except Exception:
        return []
    return out


# The *_ok flags let the template tell "nothing to show" apart from "the query
# failed". An empty list with ok=1 is a real empty state and says so; ok=0 means
# we could not look, and the template keeps its placeholder content instead.
return {'announcements': announcements, 'announcements_ok': announcements_ok,
        'events': events, 'events_ok': events_ok,
        'calendar_months': calendar_months, 'calendar_ok': calendar_ok,
        'quick_links': link_list('quick_links'),
        'how_do_i': link_list('how_do_i'),
        'explore': link_list('explore')}
