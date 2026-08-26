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
# Zope 2.13 / Python 2.7 restricted Python: no sorted(), int(), callable(),
# isinstance(), unicode(), basestring, and no attribute starting with '_'.
# ============================================================================

DASH = u'–'          # en dash, matches the approved design
# One icon for every announcement, and a star for the featured one. Keyword-
# derived icons were dropped: the mapping was invisible to editors, and
# substring matching meant a "training" keyword picked up the AI icon because
# "tr-ai-ning" contains "ai".
ICON_STANDARD = 'fa-circle'
ICON_FEATURED = 'fa-star'

# An announcement keyed with this in `keywords` is pinned to position one.
# Matched case-insensitively as a whole keyword, so "featured-story" does not
# count. If several carry it, the newest wins.
FEATURED_KEYWORD = 'featured'

# priority is a dropdown from 0 (lowest) to 4 (highest), rendered as strings
# like "2 - medium". The leading digit is the rank and sorts DESCENDING, so 4
# comes first. Parsing the digit rather than matching the whole label means the
# wording can change without touching this.
#
# A missing or unparseable priority is treated as 2, the middle of the range
# and what the dropdown defaults to — rather than as lowest, which would bury
# an announcement whose priority simply was not set.
PRIORITY_DEFAULT = 2
DIGITS = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
          '5': 5, '6': 6, '7': 7, '8': 8, '9': 9}

# EventDocument keeps its template fields in a mapping keyed by human-readable
# labels, exposed through keys():
#   Hosted By, Time, Location, Contact Name, Contact Phone, Contact Email,
#   Open To, Priority, School or Program, College Calendar, Physical Address
# That is why no attribute name ever matched — "Contact Name" cannot be one.
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
    """'10:00-11:00 AM', '9:05 AM-4:30 PM', or 'All day'.

    Purdue Event Documents store event_date at midnight when no time has been
    entered, which is currently every event. Those render as 'All day'; the
    moment real times are entered this starts formatting them.
    """
    if start is None or is_midnight(start):
        return u'All day'
    a = clock_parts(start)
    if not a:
        return u'All day'
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
    it is only read off the object as a fallback — and it counts days
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
    """Respect the show_date / hide_date publication window."""
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
    object is loaded — but only for the few documents actually displayed."""
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
# "| nothing" only catches a failed *lookup* — the script not existing — and
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
# Upcoming events — /calendar, soonest first
# ---------------------------------------------------------------------------
events = []
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
        # entered one — in which case this reads "All day".
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


# ---------------------------------------------------------------------------
# Announcements — /announcements
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
            'icon':     is_first_featured and ICON_FEATURED or ICON_STANDARD,
            'featured': is_first_featured and 1 or 0,
            'title':    title,
            'summary':  as_text(meta(brain, 'intro', u'')),
            'due':      due,
            'url':      url,
        })
except Exception:
    # one widget failing must not take the page down; see note above
    announcements = []


return {'announcements': announcements, 'events': events}
