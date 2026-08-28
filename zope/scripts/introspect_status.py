##parameters=
##title=Discovery: what does the getStatus index actually hold?
##
# ============================================================================
# Run once, paste the output back, then delete. Reads only.
#
# Install: ZMI -> /staff -> Add Script (Python), id "introspect_status".
#          Visit https://engineering.purdue.edu/staff/introspect_status
#
# Both Purdue Event Managers carry a getStatus index and metadata column. If
# that is the real publication status, a document could be a genuine draft
# while still having a show_date in the past - which the current show_date
# check would let through. This reports the values in use.
# ============================================================================

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')

out = []


def show(value, limit=120):
    try:
        text = str(value)
    except Exception:
        return '<unprintable>'
    text = ' '.join(text.split())
    if len(text) > limit:
        text = text[:limit] + '...'
    return text


for folder_id in ('announcements', 'calendar'):
    out.append('=' * 68)
    out.append('FOLDER: %s' % folder_id)
    out.append('=' * 68)
    folder = getattr(context, folder_id, None)
    if folder is None:
        out.append('  NOT FOUND')
        out.append('')
        continue

    try:
        out.append('  distinct getStatus values: %s'
                   % show(folder.uniqueValuesFor('getStatus'), 300))
    except Exception as e:
        out.append('  uniqueValuesFor(getStatus) failed: %s' % show(e))

    try:
        brains = folder.searchResults()
        out.append('  %s document(s) in the catalog' % len(brains))
        out.append('')
        out.append('  %-34s %-14s %-22s %s' % ('id', 'getStatus', 'show_date', 'title'))
        out.append('  ' + '-' * 92)
        for brain in brains:
            out.append('  %-34s %-14s %-22s %s'
                       % (show(getattr(brain, 'id', '?'), 34),
                          show(getattr(brain, 'getStatus', '?'), 14),
                          show(getattr(brain, 'show_date', '?'), 22),
                          show(getattr(brain, 'title', '?'), 40)))
    except Exception as e:
        out.append('  searchResults() failed: %s' % show(e))
    out.append('')

out.append('If getStatus separates published from draft, say so and the widgets')
out.append('can filter on it directly instead of inferring from show_date.')
out.append('')
out.append('End of report.')

return '\n'.join(out)
