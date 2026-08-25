# College of Engineering — Staff Site Redesign

Prototypes for the Purdue College of Engineering staff site refresh.

**Live review link:** enable GitHub Pages (Settings → Pages → Deploy from branch → `main` / `root`),
then the prototypes are at `https://jeremiahd01.github.io/coe-staff-site/`.

## Contents

| Path | What it is |
|---|---|
| `index.html` | Landing page listing the prototypes |
| `prototype/` | MVP dashboard home page (layout review) |
| `current/` | Saved copy of the existing Wrap8 staff site, for reference |

## MVP home page

Dashboard-style layout, not a standard Wrap9 Blocks page. Cards in this build:

- Welcome banner + search
- New & Important
- Quick Links
- Explore
- Upcoming Events
- Have a suggestion?

Hatched blocks mark extension slots where deferred Phase 2 widgets ("How Do I…?",
calendar snapshot) drop in without a relayout. Event and announcement content is
placeholder data pending the content collections.

## Technical notes

- Ships as a sequence of `<section class="block">` elements inside `#page-body`.
  The Wrap9 theme supplies the masthead, main navigation, breadcrumb and footer.
- The prototype links the production Wrap9 stylesheet
  (`/Wraps/wrap09/required/wrap_css.css`), Bootstrap 5.3.2 and the Wrap9
  FontAwesome kit, so what renders is the real theme rather than an approximation.
- `prototype/staff-dashboard.css` becomes an addition to `/staff/local.css`.
  All classes are prefixed `staff-`, and it consumes Wrap9's own custom properties
  (`--boiler-gold`, `--acumin-pro`, …) rather than redeclaring the palette.
- Target platform is Zope 2.13.10 on Python 2.7.18, so TAL `python:` expressions
  must be Python 2 syntax.

## Status

Layout review. Data sourcing and secondary page content come next.
