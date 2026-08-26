##parameters=
##title=Discovery v2: report the Purdue Event Document model
##
# ============================================================================
# Discovery script v2 -- run once, paste the output back, then delete.
#
# v1 inspected whatever objectValues() returned first, which was a
# ZCTextIndex Lexicon belonging to the manager's own catalog, so the properties
# it reported were the manager's (acquired), not a document's. This version
# filters on meta_type, recurses into nested managers, and reports the catalog
# schema as well.
#
# Install: ZMI -> /staff -> Add Script (Python), id "introspect_event_model",
#          paste this whole file in, save, then visit
#          https://engineering.purdue.edu/staff/introspect_event_model
#
# Reads only. Restricted Python: no sorted(), int(), callable(), isinstance(),
# and no attribute starting with an underscore.
# ============================================================================

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')

DOC_META = 'Purdue Event Document'
MGR_META = 'Purdue Event Manager'

out = []


def show(value, limit=90):
    """Coerce anything to a short printable string without raising."""
    try:
        text = str(value)
    except Exception:
        try:
            text = value.encode('utf-8', 'replace')
        except Exception:
            return '<unprintable>'
    text = ' '.join(text.split())
    if len(text) > limit:
        text = text[:limit] + '...'
    return text


def sort_list(values):
    items = list(values)
    items.sort()
    return items


def collect_docs(folder, depth):
    """Every Purdue Event Document at or below this folder."""
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


for folder_id in ('announcements', 'calendar'):
    out.append('=' * 74)
    out.append('FOLDER: %s' % folder_id)
    out.append('=' * 74)

    folder = getattr(context, folder_id, None)
    if folder is None:
        out.append('  NOT FOUND')
        out.append('')
        continue

    out.append('  meta_type : %s' % getattr(folder, 'meta_type', '?'))
    try:
        out.append('  contents  : %s' % show(folder.objectIds(), 200))
    except Exception as e:
        out.append('  objectIds() failed: %s' % show(e))

    # ---- the manager is its own ZCatalog; report its schema -------------
    out.append('')
    out.append('  CATALOG')
    index_names = []
    try:
        index_names = list(folder.indexes())
        out.append('    indexes  : %s' % show(sort_list(index_names), 400))
    except Exception as e:
        out.append('    indexes() failed: %s' % show(e))
    try:
        out.append('    metadata : %s' % show(sort_list(folder.schema()), 400))
    except Exception as e:
        out.append('    schema() failed: %s' % show(e))
    try:
        out.append('    searchResults() count: %s' % len(folder.searchResults()))
    except Exception as e:
        out.append('    searchResults() failed: %s' % show(e))

    # Any index that might hold the document type -- show its distinct values
    for name in index_names:
        low = name.lower()
        if ('type' in low) or ('template' in low) or ('tag' in low) or ('subject' in low):
            try:
                out.append('    values of %-22s %s' % (name, show(folder.uniqueValuesFor(name), 220)))
            except Exception as e:
                out.append('    uniqueValuesFor(%s) failed: %s' % (name, show(e)))

    # ---- a real Purdue Event Document -----------------------------------
    docs = collect_docs(folder, 2)
    out.append('')
    out.append('  DOCUMENTS FOUND: %s' % len(docs))
    if not docs:
        out.append('    None. Add one document of each Document Type and re-run.')
        out.append('')
        continue

    for doc in docs[:2]:
        out.append('')
        out.append('  --- %s ---' % show(doc.getId()))
        out.append('  url       : %s' % show(doc.absolute_url()))
        out.append('  meta_type : %s' % getattr(doc, 'meta_type', '?'))
        out.append('  PROPERTIES (id | type | value)')
        try:
            for pid in doc.propertyIds():
                try:
                    ptype = doc.getPropertyType(pid)
                except Exception:
                    ptype = '?'
                try:
                    pval = doc.getProperty(pid)
                except Exception:
                    pval = '<unreadable>'
                out.append('    %-26s %-20s %s' % (pid, ptype, show(pval)))
        except Exception as e:
            out.append('    propertyIds() failed: %s' % show(e))

        # Time and Location live on the Edit tab, not the Properties tab: the
        # edit form stores them as plain instance attributes, so propertyIds()
        # never mentions them. Probe candidate names directly, through aq_base
        # so an inherited value from the parent folder cannot masquerade as the
        # document's own.
        out.append('  INSTANCE ATTRIBUTES (not registered properties)')
        # aq_base is not exposed to restricted Python on this instance, so
        # acquired values are flagged by comparison instead.
        base_obj = doc
        # Build candidates systematically rather than guessing one at a time:
        # every prefix x base combination, plus a few one-offs. The rendered
        # markup shows .event-location-name and .event-date-time, and the time
        # renders as "<formatted date> at <Time>", so the stored value is just
        # the time fragment.
        prefixes = ('', 'event_', 'Event', 'event', 'evt_', 'the_')
        bases = ('time', 'Time', 'time_text', 'timeText', 'date_time',
                 'dateTime', 'times', 'start_time', 'startTime',
                 'location', 'Location', 'location_name', 'locationName',
                 'LocationName', 'place', 'Place', 'venue', 'room',
                 'address', 'Address', 'physical_address', 'physicalAddress',
                 'map_embed', 'contact_email', 'contact', 'cost', 'sponsor',
                 'audience', 'college_calendar', 'registration_url')
        names = []
        seen_names = {}
        for prefix in prefixes:
            for base in bases:
                candidate = prefix + base
                if candidate not in seen_names:
                    seen_names[candidate] = 1
                    names.append(candidate)
        hits = 0
        for name in names:
            try:
                value = getattr(base_obj, name, None)
            except Exception:
                continue
            if value is None:
                continue
            text = show(value)
            if text[:1] == '<':
                continue          # bound method or object repr, not a field
            # Flag anything inherited from the manager rather than set here
            marker = ''
            try:
                if getattr(folder, name, None) is value:
                    marker = '   [ACQUIRED from manager, not this document]'
            except Exception:
                pass
            hits = hits + 1
            out.append('    %-28s %s%s' % (name, text, marker))
        if not hits:
            out.append('    none of the probed names are set on this document')

        # getTemplate is the one accessor these documents expose; its value
        # should name the document's template variant.
        try:
            out.append('  getTemplate() -> %s' % show(doc.getTemplate()))
        except Exception as e:
            out.append('  getTemplate() failed: %s' % show(e))

        out.append('  ACCESSORS PRESENT')
        present = []
        for name in ('Title', 'Description', 'getStartDate', 'getEndDate',
                     'start', 'end', 'getLocation', 'getTags', 'Subject',
                     'getIcsUrl', 'getAddToCalendarLinks', 'getIntroduction',
                     'getDocumentType', 'getTemplate', 'getEventDate',
                     'CookedBody', 'getIcon', 'getImage'):
            if hasattr(doc, name):
                present.append(name)
        out.append('    %s' % (', '.join(present) or 'none of the usual ones'))

    out.append('')

out.append('End of report.')

return '\n'.join(out)
