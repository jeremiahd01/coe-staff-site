##parameters=
##title=Discovery: report the Purdue Event Manager / Event Document model
##
# ============================================================================
# Discovery script — run once, paste the output back, then delete.
#
# Install: ZMI -> /staff -> Add Script (Python), id "introspect_event_model",
#          paste this whole file in, save, then visit
#          https://engineering.purdue.edu/staff/introspect_event_model
#
# Reports the meta_types, callables and property names of the announcements
# and calendar managers so the production scripts can target real field names
# instead of guesses. Reads only — changes nothing.
# ============================================================================

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')

out = []


def show(value, limit=70):
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


# RestrictedPython forbids any attribute starting with '_', so __class__
# and __name__ are unavailable here. meta_type is the identifier we
# actually need anyway.
out.append('Purdue Event model discovery')
out.append('container : %s' % context.absolute_url())
out.append('meta_type : %s' % getattr(context, 'meta_type', '?'))

CANDIDATE_METHODS = (
    'objectValues', 'objectIds', 'listFolderContents', 'contentValues',
    'getEvents', 'getItems', 'getDocuments', 'getUpcomingEvents',
    'getEventDocuments', 'searchResults', 'queryCatalog', 'getObjects',
)

for folder_id in ('announcements', 'calendar'):
    out.append('')
    out.append('=' * 72)
    out.append('FOLDER: %s' % folder_id)
    out.append('=' * 72)

    folder = getattr(context, folder_id, None)
    if folder is None:
        out.append('  NOT FOUND in this container.')
        continue

    out.append('  meta_type  : %s' % getattr(folder, 'meta_type', '?'))

    present = []
    for name in CANDIDATE_METHODS:
        if hasattr(folder, name):
            present.append(name)
    out.append('  callables  : %s' % (', '.join(present) or 'none of the usual ones'))

    items = []
    for getter in ('objectValues', 'listFolderContents', 'contentValues'):
        if not hasattr(folder, getter):
            continue
        try:
            items = list(getattr(folder, getter)())
            out.append('  listed via : %s()  -> %d item(s)' % (getter, len(items)))
            break
        except Exception as e:
            out.append('  %s() failed: %s' % (getter, show(e)))

    if not items:
        out.append('  No items to inspect. Add one dummy document and re-run.')
        continue

    # meta_types present in the folder
    kinds = {}
    for obj in items:
        mt = getattr(obj, 'meta_type', '?')
        kinds[mt] = kinds.get(mt, 0) + 1
    out.append('  meta_types : %s' % show(kinds, 200))

    doc = items[0]
    out.append('')
    out.append('  --- first document: %s ---' % show(doc.getId()))
    out.append('  meta_type  : %s' % getattr(doc, 'meta_type', '?'))

    out.append('')
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
            out.append('    %-26s %-10s %s' % (pid, ptype, show(pval)))
    except Exception as e:
        out.append('    propertyIds() failed: %s' % show(e))

    # Distinct Document Type values, so we learn the exact strings to match on
    out.append('')
    out.append('  DOCUMENT TYPE VALUES ACROSS ALL ITEMS')
    seen = {}
    for obj in items:
        try:
            pids = obj.propertyIds()
        except Exception:
            continue
        for pid in pids:
            if 'type' not in pid.lower():
                continue
            try:
                val = show(obj.getProperty(pid), 40)
            except Exception:
                continue
            key = '%s = %s' % (pid, val)
            seen[key] = seen.get(key, 0) + 1
    if seen:
        for key in sorted(seen.keys()):
            out.append('    %-52s x%d' % (key, seen[key]))
    else:
        out.append('    no property with "type" in its name')

    # Common accessor methods worth knowing about
    out.append('')
    out.append('  ACCESSORS PRESENT ON THE DOCUMENT')
    found = []
    for name in ('Title', 'Description', 'getStartDate', 'getEndDate', 'start',
                 'end', 'getLocation', 'getTags', 'Subject', 'getIcsUrl',
                 'getAddToCalendarLinks', 'absolute_url', 'getIntroduction'):
        if hasattr(doc, name):
            found.append(name)
    out.append('    %s' % (', '.join(found) or 'none of the usual ones'))

out.append('')
out.append('End of report.')

return '\n'.join(out)
