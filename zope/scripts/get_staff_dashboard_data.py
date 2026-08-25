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

# Confirmed by discovery: the manager's `available_templates` property is
# ('Event/Function', 'News Item'), matched loosely so casing/punctuation drift
# does not break it.
DOCTYPE_NEWS  = 'news'
DOCTYPE_EVENT = 'event'

DOC_META = 'Purdue Event Document'
MGR_META = 'Purdue Event Manager'

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
            if value is not None:
                # Might be an accessor method rather than a plain attribute.
                # Just try it: callable() is not exposed here, and calling a
                # non-callable simply raises and leaves the value untouched.
                try:
                    value = value()
                except Exception:
                    pass
        if value not in (None, '', ()):
            return value
    return default


def as_text(value):
    """Safe text, never raises.

    Deliberately avoids the unicode / basestring / isinstance builtins: which of
    those restricted Python exposes varies by instance, and a NameError here
    would take down the whole dashboard. Formatting through a unicode literal
    handles text, byte strings and numbers alike.
    """
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


def clock_parts(dt):
    """(hour, minute, MERIDIEM) as strings, from a Zope DateTime or datetime.

    Returns strings rather than ints so no int() call is needed — this instance
    keeps a tight safe-builtins list and int() is not worth relying on.
    """
    try:
        return (u'%s' % dt.h_12(), u'%02d' % dt.minute(), dt.ampm().upper())
    except Exception:
        pass
    try:
        hour = dt.strftime('%I').lstrip('0') or u'12'
        return (u'%s' % hour, dt.strftime('%M'), dt.strftime('%p').upper())
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
        return u'%s:%s %s' % (ah, am, ap)
    bh, bm, bp = b
    if ap == bp:
        # same meridiem reads better with it stated once, at the end
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


def doctype_matches(obj, wanted):
    """Loose match so 'News Item' and 'news_item' both work."""
    raw = as_text(prop(obj, F_DOCTYPE)).lower()
    return wanted in raw


def pick_icon(obj):
    tags = prop(obj, F_TAGS, ())
    if hasattr(tags, 'strip'):
        tags = [tags]          # a bare string, not a sequence of them
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


def collect_docs(folder, depth):
    """Every Purdue Event Document at or below this folder.

    A Purdue Event Manager is its own ZCatalog, so objectValues() also returns
    a ZCTextIndex Lexicon and a Page Template. Filtering on meta_type keeps
    those out — relying on the Document Type check alone is unsafe, because
    acquisition can make an unrelated object appear to carry the property.
    The calendar manager also contains a nested manager, so recurse.
    """
    found = []
    try:
        children = folder.objectValues()
    except Exception:
        return found
    for child in children:
        kind = getattr(child, 'meta_type', '')
        if kind == DOC_META:
            found.append(child)
        elif kind == MGR_META and depth > 0:
            for nested in collect_docs(child, depth - 1):
                found.append(nested)
    return found


def documents(folder_id):
    folder = getattr(context, folder_id, None)
    if folder is None:
        return []
    return collect_docs(folder, 2)


now = context.ZopeTime()


# ---------------------------------------------------------------------------
# Upcoming events: future only, soonest first
# ---------------------------------------------------------------------------
dated = []
for obj in documents('calendar'):
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
for obj in documents('announcements'):
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
