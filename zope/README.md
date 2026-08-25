# Zope deliverable — Staff Hub dashboard

`dashboard_home.pt` is the TAL page template for the MVP dashboard home page.

## Installing it

1. **Create the template.** In the ZMI, in the `/staff` folder, add a
   **Page Template** and paste the contents of `dashboard_home.pt` into it.
   The id is up to you — currently `pt_homepage`.
2. **Point the block at it.** On `/staff/index_html?action=edit_blocks`, add a
   **Page Template Embed** block and give it the template's *name only*. The
   block resolves it from the same folder; it does not take a path, and it does
   not take pasted template source.
3. **Add the styles.** Append `../prototype/staff-dashboard.css` to
   `/staff/local.css` (see below).
4. **Remove the existing banner block.** `index_html` already carries a
   `banner_2025-01-01-00-00-00-000` block. This template renders its own banner
   (the approved design puts the search field inside it), so leaving both in
   place shows two banners.

### The stylesheet

Wrap9 already links `/staff/local.css` on every page — there is no `<link>` tag
to add. The load order is:

```html
<link rel="stylesheet" href="/Wraps/wrap09/required/wrap_css.css">
<link rel="stylesheet" href="/staff/local.css">
```

**That order matters.** Several rules in `staff-dashboard.css` beat the theme on
an equal-specificity tie and only win because `local.css` loads second — the
`--bg-light-gray` blue-link override and the focus-ring colours among them. Do
not move our CSS anywhere that loads earlier.

If `/staff/local.css` already exists, **append** to it rather than replacing it,
so any existing site styles survive. If it does not exist, add a **File** object
with the id `local.css`.

Our stylesheet is ~22 KB / 766 lines and contains no DTML syntax, so it is safe
in either a File or a DTML object.

**If the styles still do not apply**, open the browser devtools Network tab and
look at the `local.css` request:

| What you see | Meaning |
|---|---|
| 404 | The object is not there, or is not named exactly `local.css` |
| 200 but nothing styled, MIME warning in console | Content-Type is wrong. It must be `text/css` — browsers refuse stylesheets served as `application/octet-stream` or `text/plain` |
| 200, correct type, still unstyled | Stale cache. Hard refresh with Cmd/Ctrl+Shift+R |

## The embed wrapper (resolved)

The Page Template Embed block wraps our output like this:

```html
<section class="block no-pad" id="page_template_embed_2026-08-25-18-18-20-381">
  <div class="page-template-embed">
    <div class="container">
      … our template renders here …
```

That `.container` caps width at 1320px, which trapped the full-bleed bands
(banner, dashboard, feedback) 72px inside each viewport edge at 1440px and lost
the edge-to-edge character of the approved design.

**Handled.** The template renders inside a single `<div class="staff-embed-root">`,
and `staff-dashboard.css` neutralises the wrapping container only when it holds
that root:

```css
.page-template-embed > .container:has(> .staff-embed-root) {
  max-width: none; width: 100%; padding-left: 0; padding-right: 0;
}
```

Scoping it with `:has()` means any *other* Page Template Embed block on the site
is untouched. `:has()` has been baseline since 2023; on a browser without it the
rule is skipped and the dashboard renders inset rather than full-bleed — degraded,
not broken.

If you would rather not depend on `:has()`, swap in an id-scoped rule once the
real block exists (its id is stable after creation):

```css
#page_template_embed_YOUR-ID > .page-template-embed > .container {
  max-width: none; width: 100%; padding-left: 0; padding-right: 0;
}
```

Nesting our `<section class="block --bg-*">` elements inside their
`<section class="block no-pad">` is fine — the outer carries no background
modifier, so our bands paint normally.

## Verify on first paste

- **Banner image path.** The template builds it from `here/absolute_url` plus
  `controls/block_settings/banner_2025-01-01-00-00-00-000/pu-banner-1920x960.jpg`.
  Confirm that resolves, or point `banner_image` at whatever asset is intended.

## How the data is wired

`scripts/get_staff_dashboard_data.py` — a Script (Python) in `/staff` — returns
both lists in one call:

```python
{'announcements': [{icon, title, summary, due, url}, ...],
 'events':        [{month, day, title, when, where, url}, ...]}
```

The template calls it once at the root and each widget uses
`live_x or [ ...dummy... ]`, so **real content wins as soon as the Event Managers
hold documents, and the page still renders the approved dummy content if the
script is missing or the managers are empty.** Delete the dummy literals once
live data is flowing.

| Widget | Source | Filter | Order |
|---|---|---|---|
| New & Important | `announcements/` | Document Type contains `news` | Newest first, 5 |
| Upcoming Events | `calendar/` | Document Type contains `event` | Soonest first, 5, unfinished only |
| Quick Links / Explore | Static in the template | — | — |

### The confirmed content model

A **Purdue Event Manager** is its own ZCatalog. Documents live in year
subfolders (`calendar/2026/...`) and the catalog indexes them all, so the script
queries `searchResults()` rather than walking objects — the catalog sorts on
`event_date`, returns metadata without waking each object, and finds the nested
folders for free. Only the handful of documents actually displayed get loaded,
and only to read `redirect_url`, which is not catalog metadata.

**Purdue Event Document properties:**

| Property | Used for |
|---|---|
| `title` | Card title |
| `intro` | Summary line |
| `event_date` | Event date; on announcements it is the deadline, giving "Closes Oct 2" |
| `event_end_date` | Catalog metadata only; used for a time range when present |
| `show_date` / `hide_date` | Publication window, honoured by both widgets |
| `keywords` | Drives the announcement icon via substring match |
| `redirect_url` | Overrides the card link when set |
| `event_length`, `priority`, `people`, `author`, `source` | Available, unused so far |

Announcements sort on `show_date` descending, because `event_date` is empty on
news items. Events sort on `event_date` ascending and drop anything before today.

**On Document Type:** the `type` index reads `eventOrFunction` in `calendar` and
empty string in `announcements`, so filtering on it would return no
announcements at all. The script does not filter by type — `announcements` and
`calendar` are separate managers, so the folder already is the filter.

### Time and Location

`eventOrFunction` documents in `calendar` carry **`Time` and `Location` as
free-text string properties**. They are displayed **verbatim** — `10:00 - 11:00 AM`
is the admin's wording, and reformatting it would only create ways to be wrong.

**They are not registered OFS properties.** They appear on the document's Edit
tab but not its Properties tab, because the edit form stores them as plain
instance attributes. `getProperty()` cannot see them and `propertyIds()` never
mentions them — which is why they were missing from the discovery output.

The script therefore falls back to `getattr`, reading through **`aq_base`**. A
bare `getattr` would find the value but would also inherit a same-named value
from a parent folder through acquisition, which would quietly attach the wrong
location to an event. `aq_base` pins the lookup to the document itself, with a
graceful fallback if restricted Python will not expose it.

Names are case-sensitive, so `Time`/`time`/`event_time` and `Location`/
`location`/`event_location` are each tried in turn. Neither is catalog metadata,
so both come off the object already being loaded for `redirect_url`.

The discovery script now probes these names directly and reports which are set,
so you can confirm the exact spelling in one run.

Order of preference for the time line:

1. the `Time` string, used exactly as written
2. failing that, a range derived from `event_date` / `event_end_date`, if a real
   time has been entered rather than the default midnight
3. otherwise `All day`

Announcements have no Location, which is correct — the design does not show one.
They do carry `event_length` (int, `1` meaning one day); it is available but
currently unused, since the announcement card shows no duration.

**Worth checking:** neither of the two calendar documents sampled during
discovery had `Time` or `Location` set, so they will render as "All day" with no
location until someone fills them in. Existing content may need a backfill pass.

**One consistency note:** an admin-authored `Time` of `10:00 - 11:00 AM` keeps
its spaced hyphen, while a derived range renders with the design's en dash
(`2:30-4:00 PM`). If that matters, it is a content-style decision rather than a
code one.

### Two things needing your input

- **Announcement icons.** Native Event Documents have no icon field, so the
  script maps from the document's tags via `ICON_BY_TAG`, falling back to
  `fa-circle-info`. Either confirm the tag vocabulary or tell me you would rather
  drive icons another way.
- **Sort and tag rules.** Currently newest-first for announcements and
  soonest-first for unfinished events. You mentioned wanting to work through
  ascending/tags properly — this is the place.

### Verified

Run against mock Event Documents covering same-meridiem and cross-meridiem time
ranges, all-day events, past events, untagged items, and documents filed under
the wrong Document Type:

```
Sep 3   Staff Council Meeting                  10:00-11:00 AM   ARMS 1010
Sep 12  Lunch & Learn                          11:30 AM-1:00 PM PMU 118
Sep 15  Performance Review Self-Assessment Due All day
Sep 30  College of Engineering Town Hall       9:00-10:00 AM    Fowler Hall
```

Past events and mis-filed documents are excluded, time ranges state the meridiem
once when both ends share it, and `Closes Sep 30` is derived from the end date.
Both template paths were rendered through `zope.pagetemplate`: script absent
yields the 5 dummy items, script present yields live data only.

## Troubleshooting

### "Security Validation Failed: CSRF token is missing or invalid."

This is the CMS rejecting the *save request*, not a problem with the template
itself — nothing in TAL can produce this message. Wrap9 puts a per-session token
in a page-level `<meta name="csrf-token">` and its JavaScript attaches that token
to save requests, so the usual causes are:

1. **Stale token.** The edit page sat open long enough for the session to roll,
   or you logged in again in another tab. Reload the edit page and save again.
2. **Truncated POST.** If the payload exceeds a size limit at the server or a
   proxy, the request can arrive without the token field, which reads as
   "missing". `dashboard_home.pt` is ~14.5 KB.
3. **A filter objecting to the payload.** Some Zope setups refuse
   `python:` expressions submitted through the web.

To tell them apart, in order — each takes under a minute:

| Test | Paste | If it fails | If it works |
|---|---|---|---|
| A | `<p>hello</p>` on a freshly reloaded edit page | Session/token issue, unrelated to our code | Go to B |
| B | Just the banner `<section>` (~40 lines) | Content pattern, go to C | Size limit — go to C anyway to confirm |
| C | `dashboard_home_static.html` | Size limit confirmed | `python:` expressions were the blocker |

**Do not disable CSRF protection to work around this.** It guards every editing
form on the site.

### Static fallback

`dashboard_home_static.html` is the same markup with every `tal:` attribute and
`python:` expression already resolved — plain HTML, no template features. If test
C is the one that succeeds, use it to get the design live, and we move the data
logic into a Python Script instead. It costs portability (URLs are hard-coded to
`/staff`) and the single-`tal:define`-per-widget swap point.

## Platform notes

Written for **Zope 2.13.10 / Python 2.7.18**. Restricted Python only — no
f-strings, `%` formatting throughout, and expressions kept traversal-safe.

**Restricted Python** applies to Script (Python) objects, and it is stricter than
the TAL sandbox. Traps hit so far, all now avoided in these scripts:

- **No attribute starting with `_`.** `obj.__class__.__name__` raises
  *"__name__ is an invalid attribute name because it starts with _"*. Use
  `meta_type`, which is the Zope type identifier you actually want.
- **Do not assume a builtin is exposed.** Which of `unicode`, `basestring` and
  friends restricted Python offers varies by instance, and a NameError takes down
  the whole page. `as_text()` formats through a unicode literal instead, and the
  tag check duck-types with `hasattr(x, 'strip')` rather than `isinstance`.
- **`sorted()` is not available on this instance.** `list.sort()` is a method
  rather than a builtin and works fine. This one bit us in the ZMI.

Observed on this instance, from what actually ran before failing:

| Builtin | Status |
|---|---|
| `getattr`, `hasattr`, `list`, `len`, `str`, `Exception` | Available — these executed successfully |
| `sorted` | **Not available** — raised `global name 'sorted' is not defined` |
| `callable`, `int`, `unicode`, `basestring`, `isinstance` | Untested; avoided on purpose |

Given how tight this safe-builtins list turned out to be, these scripts now run
using nothing beyond what they define themselves. Worth keeping to that bar for
anything new: a missing builtin is a NameError at request time, and because the
template calls the data script at its root, that would take the whole page down
rather than degrade one widget.

Two escaping traps worth knowing, both already handled:

- The XML parser unescapes entities *before* TALES evaluates an expression, so
  `&#39;` inside a single-quoted Python string terminates it early and raises a
  SyntaxError. Strings containing apostrophes use `&quot;` delimiters instead.
- A multi-line `python:` expression that is not bracketed raises
  "unexpected indent". Keep such expressions on one line or wrap them in parens.

## Verification performed

Rendered through `zope.pagetemplate` (the actual Zope engine), placed inside a
byte-exact copy of the embed wrapper above, and checked against the approved
prototype: 3 block sections, 5 announcements, 6 quick links, 3
explore tiles, 5 events, 5 add-to-calendar links, 5 motion headings, 2 extension
slots. Visually identical. axe-core reports 0 violations across wcag2a/aa,
wcag21aa, wcag22aa and best-practice, with heading order H1 → H2×4 → H3×5.
