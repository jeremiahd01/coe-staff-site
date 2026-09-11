##parameters=
##title=One-time setup: create the dashboard_settings folder and seed it
##
# ============================================================================
# Run ONCE, then delete. This one WRITES - everything else in this folder only
# reads. It needs Manager rights.
#
# Install: ZMI -> /staff -> Add Script (Python), id "setup_dashboard_settings".
#          Visit https://engineering.purdue.edu/staff/setup_dashboard_settings
#
# Creates /staff/dashboard_settings and seeds three text properties with the
# link lists currently written into pt_homepage, as JSON. After this the lists
# are editable from the ZMI Properties tab, and later from an admin page, with
# no template change.
#
# Idempotent: an existing folder is reused and an existing non-empty property is
# left alone, so re-running cannot overwrite edits.
# ============================================================================

import json

SETTINGS_FOLDER = 'dashboard_settings'

SEED = {
    'quick_links': [
        {'label': 'Purdue Directory', 'icon': 'fa-address-book',
         'url': 'https://engineering.purdue.edu/Engr/People/ptDirectory'},
        {'label': 'IT Help', 'icon': 'fa-headset',
         'url': 'https://service.purdue.edu/TDClient/32/Purdue/Home/'},
        {'label': 'HR Request', 'icon': 'fa-id-card',
         'url': 'https://service.purdue.edu/TDClient/32/Purdue/Requests/Service/84/Human-Resources-Service-Center/Request'},
        {'label': 'Purchasing Resources', 'icon': 'fa-cart-shopping',
         'url': 'https://www.purdue.edu/operations/procurement/supplier-resources/'},
        {'label': 'Travel Resources', 'icon': 'fa-plane',
         'url': 'https://www.purdue.edu/operations/travel/'},
        {'label': 'Engineering Forms', 'icon': 'fa-clipboard-list',
         'url': 'resources/forms'},
    ],
    'explore': [
        {'label': 'AI Resources', 'icon': 'fa-microchip', 'url': 'resources/ai',
         'summary': 'Find trainings, policies and tools related to AI.'},
        {'label': 'Recognize Great Work', 'icon': 'fa-trophy', 'url': 'recognition',
         'summary': 'Celebrate achievements and recognize great work of our staff.'},
        {'label': 'Grow Your Career', 'icon': 'fa-chart-line', 'url': 'training',
         'summary': 'Explore professional development programs and training opportunities.'},
    ],
    'how_do_i': [
        {'label': 'Hire someone', 'url': '#'},
        {'label': 'Post a position', 'url': '#'},
        {'label': 'Hire a student', 'url': '#'},
        {'label': 'Reserve a room', 'url': '#'},
        {'label': 'Host an event', 'url': '#'},
        {'label': 'Reserve a vehicle', 'url': '#'},
        {'label': 'Travel internationally', 'url': '#'},
        {'label': 'Purchase software', 'url': '#'},
        {'label': 'Buy supplies', 'url': '#'},
        {'label': 'Request furniture', 'url': '#'},
        {'label': 'Order business cards', 'url': '#'},
        {'label': 'Add someone to Teams', 'url': '#'},
        {'label': 'Order catering', 'url': '#'},
        {'label': 'Request marketing', 'url': '#'},
    ],
}

# Order matters for display, so write them in a fixed order rather than relying
# on dict ordering, which Python 2.7 does not guarantee.
ORDER = ('quick_links', 'explore', 'how_do_i')

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')

out = []
out.append('Dashboard settings setup')
out.append('')

folder = getattr(context, SETTINGS_FOLDER, None)
if folder is None:
    try:
        context.manage_addFolder(SETTINGS_FOLDER, 'Dashboard settings')
        folder = getattr(context, SETTINGS_FOLDER, None)
        out.append('created folder: %s' % SETTINGS_FOLDER)
    except Exception as e:
        out.append('could not create %s: %s' % (SETTINGS_FOLDER, e))
else:
    out.append('folder already exists: %s (reusing)' % SETTINGS_FOLDER)

if folder is None:
    out.append('')
    out.append('Nothing further to do. Check that this script runs as a Manager.')
    return '\n'.join(out)

out.append('')
for name in ORDER:
    payload = json.dumps(SEED[name], indent=2)
    try:
        existing = folder.getProperty(name, None)
    except Exception:
        existing = None

    if existing is None:
        try:
            folder.manage_addProperty(name, payload, 'text')
            out.append('  %-12s created  (%s entries)' % (name, len(SEED[name])))
        except Exception as e:
            out.append('  %-12s FAILED to create: %s' % (name, e))
        continue

    if str(existing).strip():
        out.append('  %-12s already set, left untouched' % name)
        continue

    try:
        folder.manage_changeProperties(**{name: payload})
        out.append('  %-12s was empty, seeded  (%s entries)' % (name, len(SEED[name])))
    except Exception as e:
        out.append('  %-12s FAILED to seed: %s' % (name, e))

out.append('')
out.append('Edit these from the ZMI: %s/%s -> Properties.' % (context.absolute_url(), SETTINGS_FOLDER))
out.append('Each is a JSON array of objects with label, url, and optionally')
out.append('icon and summary. A malformed array makes the dashboard fall back')
out.append('to the lists held in the template, so a bad save is recoverable.')
out.append('')
out.append('Delete this script once you are done - it is the only one that writes.')

return '\n'.join(out)
