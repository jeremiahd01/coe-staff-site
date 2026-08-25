# Zope deliverable — Staff Hub dashboard

`dashboard_home.pt` is the TAL page template for the MVP dashboard home page.

## Installing it

1. **Create the template.** In the ZMI, in the `/staff` folder, add a
   **Page Template** with the id `dashboard_home`. Paste the full contents of
   `dashboard_home.pt` into it and save.
2. **Add the styles.** Append the contents of `../prototype/staff-dashboard.css`
   to `/staff/local.css`. It consumes Wrap9's own custom properties, so it needs
   no edits.
3. **Embed it.** On `/staff/index_html?action=edit_blocks`, add a
   **Page Template Embed** block pointing at `dashboard_home`.
4. **Remove the existing banner block.** `index_html` already carries a
   `banner_2025-01-01-00-00-00-000` block. This template renders its own banner
   (the approved design puts the search field inside it), so leaving both in
   place shows two banners.

## Verify on first paste

- **No double-wrapping.** This template emits its own
  `<section class="block --bg-light-gray">` / `--bg-black` wrappers, because the
  CSS depends on those classes for link colours and focus rings. If the Page
  Template Embed block adds its own `.block` wrapper around the embedded output,
  we will need to drop ours. This is the one thing I could not determine without
  access to the block's settings.
- **Banner image path.** The template builds it from `here/absolute_url` plus
  `controls/block_settings/banner_2025-01-01-00-00-00-000/pu-banner-1920x960.jpg`.
  Confirm that resolves, or point `banner_image` at whatever asset is intended.

## How the data is wired

Every widget draws from a list defined in a single `tal:define` at the top of its
section, currently holding the approved dummy content. Going live means replacing
one define per widget — the markup underneath does not change.

| Widget | Define | Intended source |
|---|---|---|
| New & Important | `announcements` | `announcements` Purdue Event Manager, Document Type `News Item` |
| Upcoming Events | `events` | `calendar` Purdue Event Manager, Document Type `Event/Function` |
| Quick Links | `quick_links` | Static. Add a dict to add a link. |
| Explore | `explore` | Static. Add a dict to add a tile. |

Keys the templates expect:

- **announcements**: `icon`, `title`, `summary`, `due` (may be empty), `url`
- **events**: `month`, `day`, `title`, `when`, `where` (may be empty), `url`

Sort order, tag filtering and the date formatting that produces `month` / `day`
are the next piece of work, along with wiring `Add to Outlook` to the event
system's native calendar export.

## Platform notes

Written for **Zope 2.13.10 / Python 2.7.18**. Restricted Python only — no
f-strings, `%` formatting throughout, and expressions kept traversal-safe.

Two escaping traps worth knowing, both already handled:

- The XML parser unescapes entities *before* TALES evaluates an expression, so
  `&#39;` inside a single-quoted Python string terminates it early and raises a
  SyntaxError. Strings containing apostrophes use `&quot;` delimiters instead.
- A multi-line `python:` expression that is not bracketed raises
  "unexpected indent". Keep such expressions on one line or wrap them in parens.

## Verification performed

Rendered through `zope.pagetemplate` (the actual Zope engine) and checked against
the approved prototype: 3 block sections, 5 announcements, 6 quick links, 3
explore tiles, 5 events, 5 add-to-calendar links, 5 motion headings, 2 extension
slots. Visually identical. axe-core reports 0 violations across wcag2a/aa,
wcag21aa, wcag22aa and best-practice, with heading order H1 → H2×4 → H3×5.
