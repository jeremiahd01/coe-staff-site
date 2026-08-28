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

### Time and Location — resolved

`EventDocument` keeps its template fields in a **mapping keyed by human-readable
labels**, exposed through `keys()`:

```
Hosted By, Time, Location, Contact Name, Contact Phone, Contact Email,
Open To, Priority, School or Program, College Calendar, Physical Address
```

That is why no attribute name ever matched — `Contact Name` cannot be an
attribute id. Note `values()` and `items()` are ObjectManager's and return the
document's **sub-objects** (its image and its .ics), not these field values.

The card reads `Time` for the time line and `Location`, falling back to
`Physical Address`, for the venue. `Time` is free text and is shown verbatim:
the template renders it as `<formatted event_date> at <Time>`, so the stored
value is just the fragment (`5PM`).

Which accessor reads a field by key is not documented, so `field_value()` tries
`get`, `getValue`, `value`, `getField`, `field`, `getFieldValue`, `getItem`,
`item` and `obj[key]`, taking the first usable answer and rejecting object
reprs. Once we know which one this product exposes, that list can collapse to one.

Nine other fields are available and currently unused — `Hosted By`,
`Contact Email`, `Open To`, `School or Program` and the rest — if the calendar
page ever wants them.

### Upcoming Events: linked titles

Each event title links to its document, using the same `url` the card already
resolves - so `redirect_url` is honoured here too, and a title pointing
elsewhere goes where the editor intended rather than to the document.

An event with no resolvable URL renders its title as plain text rather than an
empty `<a href="">`.

Styling matches the announcement titles: black rather than the browser-blue the
theme applies inside a light-gray block, no underline, and a gold underline that
slides in on hover. The link pins its own `line-height`, because wrap9 sets
`body a { line-height: 24px }`, which would otherwise override the heading's
spacing and shift every row.

### Add to Outlook — solved, for free

Each event document **auto-generates its own `.ics` file** as a sub-object:

```
staff-award-nominations-2026/
  staff-awards2-712x400.jpg
  staff-award-nominations-2026.ics     <- BEGIN:VCALENDAR ... DTSTART;TZID=US/Eastern:20261002T170000
```

The DTSTART already reflects the `Time` field. `ics_url()` finds it by scanning
`objectIds()` for a `.ics` suffix, and the card links straight to it — which
works with Outlook desktop, OWA, Apple Calendar and Google. Nothing to generate,
no deep-link fiddling.

The link is wrapped in `tal:condition="event/ics | nothing"`, so an event without
an .ics simply shows no button rather than a dead one. The dummy fallback content
carries no .ics either, so those rows show no button until live data arrives.

Events also carry an image sub-object, if the calendar page ever wants thumbnails.

### New & Important: ordering, featuring and icons

**Order:** the featured item first, then by `priority` **descending**, then
newest by `show_date`. Everything visible is collected before sorting, so a
high-priority item deep in the catalog can still reach position one.

`priority` is a dropdown from **0 (lowest) to 4 (highest)**, stored as strings
like `2 - medium`. Only the leading digit is read, so the wording of the labels
can change without touching the code. A missing or unparseable priority is
treated as **2** — the middle of the range and the dropdown's default — rather
than as lowest, which would bury an announcement whose priority simply was not
set.

**Featured:** an announcement whose `keywords` contains `featured` is pinned to
position one and gets a star. Matched case-insensitively against the **whole**
keyword, so `featured-story` does not count. If several carry it the newest
wins; the others return to normal ordering. The featured item counts toward the
five.

**Icons:** driven by the document's `keywords`, matched against the agreed
vocabulary as **whole keywords** (never substrings), in this order:

| Keyword | Icon | Covers |
|---|---|---|
| `new-staff` | `fa-user-group` | New staff joining soon or recently |
| `benefits` | `fa-shield-check` | Enrollment start/end, new benefits |
| `awards` | `fa-trophy` | Award nominations and award events |
| `deadline` | `fa-calendar-exclamation` | Review deadlines, time-sensitive items |
| `training` | `fa-circle-book-open` | New training resources or opportunities |
| `recording` | `fa-clapperboard-play` | Event, webinar and town hall recordings |
| `documentation` | `fa-file-lines` | New forms, new documentation |
| `high-importance` | `fa-circle-exclamation` | High-stakes announcements |
| `general` *or none* | `fa-newspaper` | Everything else |

Order is precedence: an item tagged both `awards` and `deadline` gets the
trophy. Matching is case-insensitive and tolerates surrounding whitespace, and
`awards-banquet` does **not** match `awards` - only whole keywords count.

Four of these are Font Awesome **Pro** icons (`shield-check`,
`calendar-exclamation`, `circle-book-open`, `clapperboard-play`). Verified
against the site kit: all nine render, so the kit is Pro.

**Featured no longer changes the icon.** The `featured` keyword still pins an
announcement to position one, but its icon comes from whichever category keyword
it also carries. An item tagged only `featured` therefore gets the default
newspaper - worth telling editors to tag a category as well.

### Column count follows the announcement count

With fewer than five announcements the items divide the row rather than leaving
empty tracks (option B, chosen by the PM from `prototype/layout-options.html`).
Columns are `min(count, max-for-breakpoint)`: 5 at xl, 3 at md, 2 at sm, 1 below,
so five items never squeeze at tablet width.

The template emits a `staff-news--N` class from the item count, sliced to five so
an unexpected sixth cannot produce a class with no rule behind it.

Two things to know before editing these rules:

- Each breakpoint **restores every divider before clearing the row-start ones**.
  A narrower breakpoint clears more of them, and without the restore they stay
  cleared as the viewport grows.
- That restore carries a redundant-looking `:nth-child(n)` purely for
  specificity. The clear rules are (0,3,0) because a pseudo-class counts as a
  class, so a plain (0,2,0) restore loses to an earlier breakpoint's clear no
  matter how late it appears in the file.

Consequence worth knowing: at one or two announcements the summary no longer
exceeds four lines, so the clamp does not engage and the "more" trigger does not
appear. That is correct - there is nothing hidden to reveal - but it does mean
the affordance comes and goes with the number of announcements published.

### Summary text: four-line clamp with a full-text tooltip

`intro` is rendered with `tal:content="structure"`, so admin-authored HTML comes
through as markup. Note this is the opposite of sanitising — a `<script>` in an
intro would run. That is acceptable while only trusted editors can create Event
Documents.

The preview is clamped to four lines. Block elements inside the clamp are
flattened to inline, because each one would otherwise start a new line and blow
the height; the tooltip renders them normally.

**The summary text itself is the target.** Hovering it opens the tooltip after a
second; clicking or tapping it toggles, which is what makes this work on touch
where hover does not exist. Only clipped summaries are interactive - the state is
measured at runtime and re-measured on resize.

A small borderless "More" control sits below the text. It is a real `<button>`,
so it stays in the tab order and opens the tooltip immediately on keyboard focus;
it also doubles as the visible hint that there is more to read. It carries a
`min-height` of 24px to satisfy WCAG 2.5.8 without drawing a box - the bordered
chip it replaced was what the PM disliked.

Escape closes, and the tooltip stays open while the pointer or focus is inside it
(WCAG 1.4.13). The title link wraps the title only, because a `<button>` cannot
live inside an `<a>`.

Note the clamp renders its own trailing ellipsis, so truncation is signalled even
before the "More" control is noticed.

Two things worth knowing:

- The tooltip is not clipped by anything, but it **was** being occluded: cards
  later in the DOM painted over it, because the tooltip's own card establishes
  no stacking context and `z-index` alone cannot escape one. The script raises
  the owning card while a tooltip is open.
- Without JavaScript the clamp still applies and no trigger appears, so long
  summaries are truncated with no way to expand them in place. The title links
  to the full announcement, so nothing is unreachable.

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

## Smaller decisions worth recording

- **No time means no time line.** `event_date` is stored at midnight unless
  someone enters a time, so defaulting to "All day" asserted something the data
  does not support - every timeless event claimed to run all day. The card now
  omits the time and shows only the location, with no leftover separator.
- **The feedback band is Aged gold**, not black. That is a mid-tone, so the
  sub-line moved from Steam to white (Steam on Aged is 2.7:1 and fails) and the
  button switched to `btn-black` (a gold button on a gold band gives only
  ~2.2:1 boundary contrast). Measured after the change: 4.67:1 for both text
  lines, 4.49:1 for the button against the band.
- **The Phase 2 extension slots are hidden** with `tal:condition="nothing"`.
  The markup stays in the template, so restoring them is deleting one attribute.

## Troubleshooting

### The Page Template Embed renders nothing at all

Almost always the data script raising, not the template.

The template calls `here/get_staff_dashboard_data` from a `tal:define` on its
**root element**. TALES `| nothing` catches a failed *lookup* — the script not
existing — but does **not** catch an exception raised inside the script. So a
script error fails the root define and the whole template renders empty. Before
the script is installed the page looks fine, because `| nothing` catches the
missing name; installing a script that then errors is what turns the page blank.

To see the actual error, request the script on its own:

```
https://engineering.purdue.edu/staff/get_staff_dashboard_data
```

It returns the dict when healthy, and a full traceback when not. Then check the
template on its own, which renders standalone and reports its own errors:

```
https://engineering.purdue.edu/staff/pt_homepage
```

Also confirm the Page Template Embed block still names the template correctly —
`pt_homepage`, the name only, not a path.

The script now guards each widget separately, so this failure mode should not
recur: an exception yields empty lists, the template falls back to its
placeholder content, and one widget cannot take the other down. A widget showing
stale placeholder copy where live content is expected means that widget's block
caught an error — check the script URL above.



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
  **"unexpected indent"**. Keep such expressions on one line or wrap them in
  parens. This bites even when a local render passes: modern `zope.tales`
  collapses newlines before compiling, Zope 2.13 does not, and the ZMI stores
  CRLF line endings which makes it certain.

- **Never put a non-ASCII character in a delivered source file.** The ZMI
  stores pasted source as Latin-1, so a literal en dash in a Python script comes
  back as mojibake: `Oct 27 a Nov 10` instead of `Oct 27 - Nov 10`. The same
  applies to templates, and to CSS, which the wrap serves as `iso-8859-15`.
  Write it as an escape instead:

  | Where | Write |
  |---|---|
  | Python | `u'\u2013'` |
  | Template | `&#8211;` |
  | CSS | `\2013` |

  Every delivered file is pure ASCII, and the checker enforces it.

- `--` is illegal inside an XML comment, so em dashes in template comments
  cannot simply become `--`.

**Run `tools/check_template.py` before pasting a template into the ZMI.** It
compiles every `python:` expression the way Zope 2.13 will, so these get caught
locally instead of at the paste:

```bash
python3 tools/check_template.py zope/dashboard_home.pt
```

## Verification performed

Rendered through `zope.pagetemplate` (the actual Zope engine), placed inside a
byte-exact copy of the embed wrapper above, and checked against the approved
prototype: 3 block sections, 5 announcements, 6 quick links, 3
explore tiles, 5 events, 5 add-to-calendar links, 5 motion headings, 2 extension
slots. Visually identical. axe-core reports 0 violations across wcag2a/aa,
wcag21aa, wcag22aa and best-practice, with heading order H1 → H2×4 → H3×5.
