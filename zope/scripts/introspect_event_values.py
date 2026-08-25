##parameters=
##title=Discovery: call values()/body() and locate the stored field values
##
# ============================================================================
# Run once, paste the output back, then delete. Reads only.
#
# Install: ZMI -> /staff -> Add Script (Python), id "introspect_event_values".
#          Visit https://engineering.purdue.edu/staff/introspect_event_values
#
# Previous run showed EventDocument.values and EventDocument.body are METHODS,
# reported un-called. The template at /MasterEventsCatalog/eventOrFunction is
# shared, so it defines the form but cannot hold this document's values. This
# calls those methods and searches everything reachable for the test values.
#
# Restricted Python: no sorted(), int(), callable(), isinstance(), and no
# attribute starting with '_'.
# ============================================================================

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')

DOC_PATH = ('calendar', '2026', 'staff-award-nominations-2026')
NEEDLES = ('test', '5PM', '5pm')

out = []


def show(value, limit=160):
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


def has_needle(text):
    for needle in NEEDLES:
        if needle in text:
            return 1
    return 0


def call_and_dump(obj, name, indent):
    """Call a zero-argument method and describe whatever comes back."""
    try:
        method = getattr(obj, name, None)
    except Exception as e:
        out.append('%s%s: unreachable (%s)' % (indent, name, show(e)))
        return None
    if method is None:
        out.append('%s%s: not present' % (indent, name))
        return None
    try:
        result = method()
    except Exception as e:
        out.append('%s%s(): raised %s' % (indent, name, show(e)))
        return None

    out.append('%s%s() -> %s' % (indent, name, show(result, 200)))

    # mapping?
    try:
        keys = result.keys()
        out.append('%s  it is a mapping with %s key(s):' % (indent, len(keys)))
        for key in keys:
            try:
                val = result[key]
            except Exception:
                val = '<unreadable>'
            text = show(val, 200)
            flag = ''
            if has_needle(text):
                flag = '   <=== HOLDS A TEST VALUE'
            out.append('%s    %-26s %s%s' % (indent, show(key, 26), text, flag))
        return result
    except Exception:
        pass

    # sequence?
    try:
        count = len(result)
        out.append('%s  it is a sequence of %s item(s):' % (indent, count))
        position = 0
        for item in result:
            if position >= 25:
                out.append('%s    ... truncated' % indent)
                break
            text = show(item, 200)
            flag = ''
            if has_needle(text):
                flag = '   <=== HOLDS A TEST VALUE'
            out.append('%s    [%s] %s%s' % (indent, position, text, flag))
            position = position + 1
        return result
    except Exception:
        pass

    # plain scalar
    text = show(result, 4000)
    if has_needle(text):
        out.append('%s  <=== THE TEST VALUES ARE IN HERE' % indent)
    return result


doc = context
for step in DOC_PATH:
    doc = getattr(doc, step, None)
    if doc is None:
        break

if doc is None:
    out.append('Could not resolve %s' % '/'.join(DOC_PATH))
    return '\n'.join(out)

out.append('DOCUMENT: %s' % show(doc.absolute_url()))
out.append('')

out.append('=' * 74)
out.append('CALLING values()')
out.append('=' * 74)
call_and_dump(doc, 'values', '  ')

out.append('')
out.append('=' * 74)
out.append('CALLING body()  (searched for the test values, then truncated)')
out.append('=' * 74)
try:
    body_text = show(doc.body(), 100000)
    out.append('  length: %s characters' % len(body_text))
    hit = 0
    for needle in NEEDLES:
        position = body_text.find(needle)
        if position > -1:
            hit = 1
            start = position - 220
            if start < 0:
                start = 0
            out.append('')
            out.append('  found %s at offset %s, surrounding markup:' % (needle, position))
            out.append('  %s' % body_text[start:position + 220])
    if not hit:
        out.append('  test values are NOT in the body')
        out.append('  first 600 chars: %s' % body_text[:600])
except Exception as e:
    out.append('  body() raised %s' % show(e))

out.append('')
out.append('=' * 74)
out.append('OTHER ZERO-ARGUMENT METHODS WORTH SEEING')
out.append('=' * 74)
for name in ('items', 'keys', 'getEventDetails', 'getDetails', 'getFields',
             'getValues', 'getFieldValues', 'getTemplateValues', 'getData',
             'CookedBody', 'getIcs', 'getIcsUrl', 'getCalendarFile'):
    call_and_dump(doc, name, '  ')

out.append('')
out.append('=' * 74)
out.append('PROPERTY SHEETS')
out.append('=' * 74)
try:
    sheets = doc.propertysheets
    out.append('  propertysheets: %s' % show(sheets))
    try:
        for sheet_id in sheets.objectIds():
            out.append('    --- %s' % show(sheet_id))
            sheet = sheets[sheet_id]
            for pid in sheet.propertyIds():
                out.append('        %-24s %s' % (pid, show(sheet.getProperty(pid))))
    except Exception as e:
        out.append('    could not enumerate: %s' % show(e))
except Exception as e:
    out.append('  none (%s)' % show(e))

out.append('')
out.append('=' * 74)
out.append('SUB-OBJECTS  (the .ics matters for Add to Outlook)')
out.append('=' * 74)
try:
    for sub_id in doc.objectIds():
        try:
            sub = doc[sub_id]
        except Exception:
            continue
        out.append('  %-40s %-18s %s' % (show(sub_id, 40),
                                         getattr(sub, 'meta_type', '?'),
                                         show(sub.absolute_url(), 90)))
except Exception as e:
    out.append('  objectIds() failed: %s' % show(e))

out.append('')
out.append('End of report.')

return '\n'.join(out)
