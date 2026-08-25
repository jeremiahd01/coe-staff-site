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
DEFAULT_ICON = 'fa-circle-info'

# Announcement icons. Purdue Event Documents carry no icon field, so map from
# the `keywords` property. Matching is on substrings, so 'new-staff' hits
# 'staff' and a compound keyword still resolves.
ICON_BY_KEYWORD = (
    ('bravo',       'fa-trophy'),
    ('award',       'fa-trophy'),
    ('recognition', 'fa-trophy'),
    ('pesla',       'fa-medal'),
    ('leadership',  'fa-medal'),
    ('ai',          'fa-wand-magic-sparkles'),
    ('benefit',     'fa-shield-halved'),
    ('enrollment',  'fa-shield-halved'),
    ('policy',      'fa-shield-halved'),
    ('staff',       'fa-user-group'),
    ('welcome',     'fa-user-group'),
    ('people',      'fa-user-group'),
    ('training',    'fa-chart-line'),
    ('career',      'fa-chart-line'),
)

# Location is NOT a field on Purdue Event Document. These are tried in case some
# documents carry one anyway; see the note in README about the content gap.
F_LOCATION = ('location', 'event_location', 'place', 'room', 'building')


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


def pick_icon(keywords):
    text = as_text(keywords).lower()
    for pair in ICON_BY_KEYWORD:
        if pair[0] in text:
            return pair[1]
    return DEFAULT_ICON


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


def location_of(obj):
    if obj is None:
        return u''
    for name in F_LOCATION:
        try:
            value = obj.getProperty(name, None)
        except Exception:
            value = None
        if value:
            return as_text(value)
    return u''


def query(folder_id, sort_on, sort_order):
    folder = getattr(context, folder_id, None)
    if folder is None:
        return []
    try:
        return list(folder.searchResults(sort_on=sort_on, sort_order=sort_order))
    except Exception:
        pass
    try:                       # catalog unhappy: fall back to an unsorted read
        return list(folder.searchResults())
    except Exception:
        return []


now = context.ZopeTime()
try:
    today = now.earliestTime()          # midnight, so today's events still show
except Exception:
    today = now


# ---------------------------------------------------------------------------
# Upcoming events — /calendar, soonest first
# ---------------------------------------------------------------------------
events = []
for brain in query('calendar', 'event_date', 'ascending'):
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
    url, obj = resolve(brain)
    events.append({
        'month': month_abbr(start),
        'day':   day_number(start),
        'title': as_text(meta(brain, 'title', u'')),
        'when':  fmt_when(start, meta(brain, 'event_end_date')),
        'where': location_of(obj),
        'url':   url,
    })


# ---------------------------------------------------------------------------
# Announcements — /announcements, newest first
#
# event_date is empty on news items, so these sort on show_date. When an
# announcement does carry an event_date it is a deadline, and becomes the
# "Closes <date>" line.
# ---------------------------------------------------------------------------
announcements = []
for brain in query('announcements', 'show_date', 'descending'):
    if len(announcements) >= announcement_limit:
        break
    if not visible(brain, now):
        continue
    deadline = meta(brain, 'event_date')
    due = u''
    if deadline is not None:
        month = month_abbr(deadline)
        day = day_number(deadline)
        if month and day:
            due = u'Closes %s %s' % (month, day)
    url, obj = resolve(brain)
    announcements.append({
        'icon':    pick_icon(meta(brain, 'keywords', ())),
        'title':   as_text(meta(brain, 'title', u'')),
        'summary': as_text(meta(brain, 'intro', u'')),
        'due':     due,
        'url':     url,
    })


return {'announcements': announcements, 'events': events}
