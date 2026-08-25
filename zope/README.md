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

Rendered through `zope.pagetemplate` (the actual Zope engine), placed inside a
byte-exact copy of the embed wrapper above, and checked against the approved
prototype: 3 block sections, 5 announcements, 6 quick links, 3
explore tiles, 5 events, 5 add-to-calendar links, 5 motion headings, 2 extension
slots. Visually identical. axe-core reports 0 violations across wcag2a/aa,
wcag21aa, wcag22aa and best-practice, with heading order H1 → H2×4 → H3×5.
