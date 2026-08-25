##parameters=announcement_limit=5, event_limit=5
##title=Dashboard data: announcements and upcoming events
##
# ============================================================================
# Feeds the Staff Hub dashboard.
#
# Install: ZMI -> /staff -> Add Script (Python), id "get_staff_dashboard_data",
#          paste this whole file in, save.
#
# Returns:
#   {'announcements': [ {icon, title, summary, due, url}, ... ],
#    'events':        [ {month, day, title, when, where, url}, ... ]}
#
# Those keys are exactly what pt_homepage already iterates, so wiring it up is
# one tal:define change per widget.
#
# Sources, both resolved from the same container as index_html:
#   announcements/  Purdue Event Manager, Document Type "News Item"
#   calendar/       Purdue Event Manager, Document Type "Event/Function"
#
# Zope 2.13 / Python 2.7, restricted Python only.
# ============================================================================

# ---------------------------------------------------------------------------
# FIELD MAP
# Each entry lists candidate property names, tried in order, first non-empty
# wins. Run introspect_event_model once and prune each tuple to the single
# real name — the tolerance is scaffolding, not a permanent design.
# ---------------------------------------------------------------------------
F_TITLE    = ('title', 'Title')
F_SUMMARY  = ('introduction', 'intro', 'summary', 'description', 'Description')
F_START    = ('start_date', 'startDate', 'event_date', 'start')
F_END      = ('end_date', 'endDate', 'end')
F_LOCATION = ('location', 'event_location', 'place', 'room')
F_ALLDAY   = ('all_day', 'allDay', 'is_all_day')
F_DOCTYPE  = ('document_type', 'documentType', 'doc_type', 'type')
F_TAGS     = ('tags', 'Subject', 'keywords', 'categories')

DOCTYPE_NEWS  = 'news'          # matched loosely against "News Item"
DOCTYPE_EVENT = 'event'         # matched loosely against "Event/Function"

# Announcement icons. The native documents carry no icon field, so we map from
# the document's tags and fall back to a neutral glyph.
ICON_BY_TAG = {
    'award':       'fa-trophy',
    'awards':      'fa-trophy',
    'recognition': 'fa-trophy',
    'bravo':       'fa-trophy',
    'pesla':       'fa-medal',
    'leadership':  'fa-medal',
    'ai':          'fa-wand-magic-sparkles',
    'technology':  'fa-wand-magic-sparkles',
    'benefits':    'fa-shield-halved',
    'hr':          'fa-shield-halved',
    'policy':      'fa-shield-halved',
    'people':      'fa-user-group',
    'staff':       'fa-user-group',
    'welcome':     'fa-user-group',
    'training':    'fa-chart-line',
}
DEFAULT_ICON = 'fa-circle-info'

DASH = u'–'   # en dash, matches the approved design


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def prop(obj, names, default=''):
    """First non-empty property from a list of candidate names."""
    for name in names:
        try:
            value = obj.getProperty(name, None)
        except Exception:
            value = None
        if value is None:
            value = getattr(obj, name, None)
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = None
        if value not in (None, '', ()):
            return value
    return default


def as_text(value):
    """Safe unicode, never raises. Handles text, bytes and numbers alike."""
    if value is None:
        return u''
    if isinstance(value, unicode):
        return value
    if isinstance(value, str):
        try:
            return value.decode('utf-8', 'replace')
        except Exception:
            return u''
    try:
        return unicode(value)
    except Exception:
        return u''


def clock_parts(dt):
    """(hour12, minute, AM/PM) from a Zope DateTime or a datetime."""
    try:
        return int(dt.h_12()), int(dt.minute()), dt.ampm().upper()
    except Exception:
        pass
    try:
        return int(dt.strftime('%I')), int(dt.strftime('%M')), dt.strftime('%p').upper()
    except Exception:
        return None


def fmt_when(start, end, all_day):
    """'10:00-11:00 AM', '11:30 AM-1:00 PM', or 'All day'."""
    if all_day or start is None:
        return u'All day'
    a = clock_parts(start)
    if not a:
        return u'All day'
    ah, am, ap = a
    b = clock_parts(end) if end is not None else None
    if not b:
        return u'%d:%02d %s' % (ah, am, ap)
    bh, bm, bp = b
    if ap == bp:
        # same meridiem reads better with it stated once, at the end
        return u'%d:%02d%s%d:%02d %s' % (ah, am, DASH, bh, bm, bp)
    return u'%d:%02d %s%s%d:%02d %s' % (ah, am, ap, DASH, bh, bm, bp)


def month_abbr(dt):
    try:
        return as_text(dt.strftime('%b'))
    except Exception:
        return u''


def day_number(dt):
    try:
        return as_text(int(dt.day()))
    except Exception:
        pass
    try:
        return as_text(int(dt.strftime('%d')))
    except Exception:
        return u''


def doctype_matches(obj, wanted):
    """Loose match so 'News Item' and 'news_item' both work."""
    raw = as_text(prop(obj, F_DOCTYPE)).lower()
    return wanted in raw


def pick_icon(obj):
    tags = prop(obj, F_TAGS, ())
    if isinstance(tags, basestring):
        tags = [tags]
    try:
        for tag in tags:
            key = as_text(tag).strip().lower()
            if key in ICON_BY_TAG:
                return ICON_BY_TAG[key]
    except Exception:
        pass
    return DEFAULT_ICON


def sort_key(pair):
    return pair[0]


def contents(folder_id):
    folder = getattr(context, folder_id, None)
    if folder is None:
        return []
    for getter in ('objectValues', 'listFolderContents', 'contentValues'):
        if hasattr(folder, getter):
            try:
                return list(getattr(folder, getter)())
            except Exception:
                continue
    return []


now = context.ZopeTime()


# ---------------------------------------------------------------------------
# Upcoming events: future only, soonest first
# ---------------------------------------------------------------------------
dated = []
for obj in contents('calendar'):
    if not doctype_matches(obj, DOCTYPE_EVENT):
        continue
    start = prop(obj, F_START, None)
    if start is None:
        continue
    try:
        # keep anything that has not finished yet
        finish = prop(obj, F_END, None) or start
        if finish < now:
            continue
    except Exception:
        pass          # incomparable dates: fail open rather than hide an event
    dated.append((start, obj))

dated.sort(key=sort_key)

events = []
for start, obj in dated[:event_limit]:
    end = prop(obj, F_END, None)
    events.append({
        'month': month_abbr(start),
        'day':   day_number(start),
        'title': as_text(prop(obj, F_TITLE)),
        'when':  fmt_when(start, end, prop(obj, F_ALLDAY, 0)),
        'where': as_text(prop(obj, F_LOCATION)),
        'url':   obj.absolute_url(),
    })


# ---------------------------------------------------------------------------
# Announcements: newest first
# ---------------------------------------------------------------------------
dated = []
for obj in contents('announcements'):
    if not doctype_matches(obj, DOCTYPE_NEWS):
        continue
    dated.append((prop(obj, F_START, None), obj))

dated.sort(key=sort_key)
dated.reverse()

announcements = []
for start, obj in dated[:announcement_limit]:
    closes = prop(obj, F_END, None)
    due = u''
    if closes is not None:
        month = month_abbr(closes)
        day = day_number(closes)
        if month and day:
            due = u'Closes %s %s' % (month, day)
    announcements.append({
        'icon':    pick_icon(obj),
        'title':   as_text(prop(obj, F_TITLE)),
        'summary': as_text(prop(obj, F_SUMMARY)),
        'due':     due,
        'url':     obj.absolute_url(),
    })


return {'announcements': announcements, 'events': events}
