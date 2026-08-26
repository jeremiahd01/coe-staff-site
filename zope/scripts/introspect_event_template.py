##parameters=
##title=Discovery: where an EventTemplate keeps its field values
##
# ============================================================================
# Run once, paste the output back, then delete. Reads only.
#
# Install: ZMI -> /staff -> Add Script (Python), id "introspect_event_template",
#          paste this in, then visit
#          https://engineering.purdue.edu/staff/introspect_event_template
#
# Why: getTemplate() returns <EventTemplate at eventOrFunction>, so an
# EventDocument delegates its field set to a template object. Time and Location
# are therefore neither registered properties nor plain attributes on the
# document -- roughly 180 candidate names came back empty. This inspects the
# template itself, and the sub-objects and containers the document may be using
# to hold per-template values.
#
# Restricted Python: no sorted(), int(), callable(), isinstance(), and no
# attribute starting with '_'.
# ============================================================================

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')

# The document with the test values in it.
DOC_PATH = ('calendar', '2026', 'staff-award-nominations-2026')

# Values you typed in, so we can spot whatever is holding them.
NEEDLES = ('test', '5PM', '5pm')

out = []


def show(value, limit=140):
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


def dump_properties(obj, indent):
    try:
        ids = obj.propertyIds()
    except Exception as e:
        out.append('%spropertyIds() failed: %s' % (indent, show(e)))
        return
    if not ids:
        out.append('%s(no registered properties)' % indent)
        return
    for pid in ids:
        try:
            ptype = obj.getPropertyType(pid)
        except Exception:
            ptype = '?'
        try:
            pval = obj.getProperty(pid)
        except Exception:
            pval = '<unreadable>'
        out.append('%s%-26s %-14s %s' % (indent, pid, ptype, show(pval)))


def probe(obj, names, indent):
    hits = 0
    for name in names:
        try:
            value = getattr(obj, name, None)
        except Exception:
            continue
        if value is None:
            continue
        text = show(value)
        if text[:1] == '<' and 'at' in text:
            out.append('%s%-26s %s   <-- object, worth expanding' % (indent, name, text))
            hits = hits + 1
            continue
        out.append('%s%-26s %s' % (indent, name, text))
        hits = hits + 1
    if not hits:
        out.append('%s(none of the probed names are set)' % indent)


# ---------------------------------------------------------------------------
doc = context
for step in DOC_PATH:
    doc = getattr(doc, step, None)
    if doc is None:
        break

if doc is None:
    out.append('Could not resolve %s' % '/'.join(DOC_PATH))
    return '\n'.join(out)

out.append('DOCUMENT: %s' % show(doc.absolute_url()))
out.append('meta_type: %s' % getattr(doc, 'meta_type', '?'))

# --- is the document itself a container of field objects? ------------------
out.append('')
out.append('DOCUMENT SUB-OBJECTS')
try:
    out.append('  objectIds(): %s' % show(doc.objectIds(), 300))
except Exception as e:
    out.append('  objectIds() failed: %s' % show(e))

# --- containers that might hold per-template values ------------------------
out.append('')
out.append('DOCUMENT: CONTAINER-SHAPED ATTRIBUTES')
probe(doc, ('fields', 'field_values', 'fieldValues', 'values', 'data',
            'template_data', 'templateData', 'extra', 'extras', 'attributes',
            'content', 'body', 'text', 'raw', 'stored', 'form_data',
            'formData', 'properties', 'template', 'event_template'), '  ')

# --- the template object ---------------------------------------------------
out.append('')
out.append('=' * 74)
out.append('TEMPLATE')
out.append('=' * 74)
tmpl = None
try:
    tmpl = doc.getTemplate()
except Exception as e:
    out.append('  getTemplate() failed: %s' % show(e))

if tmpl is None:
    out.append('  no template')
else:
    out.append('  repr      : %s' % show(tmpl))
    out.append('  meta_type : %s' % getattr(tmpl, 'meta_type', '?'))
    try:
        out.append('  id        : %s' % show(tmpl.getId()))
    except Exception:
        pass
    try:
        out.append('  url       : %s' % show(tmpl.absolute_url()))
    except Exception:
        out.append('  url       : (not addressable)')

    out.append('')
    out.append('  TEMPLATE PROPERTIES')
    dump_properties(tmpl, '    ')

    out.append('')
    out.append('  TEMPLATE SUB-OBJECTS')
    try:
        ids = tmpl.objectIds()
        out.append('    objectIds(): %s' % show(ids, 400))
        for sub_id in ids[:12]:
            try:
                sub = tmpl[sub_id]
            except Exception:
                continue
            out.append('    --- %s (%s)' % (show(sub_id), getattr(sub, 'meta_type', '?')))
            dump_properties(sub, '        ')
    except Exception as e:
        out.append('    objectIds() failed: %s' % show(e))

    out.append('')
    out.append('  TEMPLATE: FIELD-DEFINITION ATTRIBUTES')
    probe(tmpl, ('fields', 'field_ids', 'fieldIds', 'field_list', 'fieldList',
                 'getFields', 'get_fields', 'schema', 'elements', 'form_fields',
                 'names', 'field_names', 'fieldNames', 'definition',
                 'field_defs', 'template_fields'), '    ')

# --- hunt the needles ------------------------------------------------------
out.append('')
out.append('=' * 74)
out.append('SEARCHING FOR THE TEST VALUES %s' % show(NEEDLES))
out.append('=' * 74)
out.append('  Any registered property or catalog metadata containing them:')
found = 0
try:
    for pid in doc.propertyIds():
        try:
            text = show(doc.getProperty(pid), 400)
        except Exception:
            continue
        for needle in NEEDLES:
            if needle in text:
                out.append('    property %-24s %s' % (pid, text))
                found = found + 1
                break
except Exception:
    pass
if not found:
    out.append('    not present in any registered property')

out.append('')
out.append('End of report.')

return '\n'.join(out)
