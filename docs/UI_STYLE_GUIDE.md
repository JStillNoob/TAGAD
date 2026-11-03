# TAGAD UI Style Guide

This is the reference for all future TAGAD interface changes. The implemented source of truth is `frontend/src/assets/main.css`; this guide explains how to reuse it consistently.

## Product style

TAGAD uses a calm pastel SaaS interface: pale gray-blue page backgrounds, white rounded surfaces, indigo actions, dark navy text, soft shadows, and restrained illustrations. Interfaces should feel clear and spacious rather than dense or decorative.

Keep Inter as the only typeface. Use weight 400 for body text and 600 for headings, labels, statistics, buttons, and table headers.

## Core tokens

Use the CSS variables already declared in `main.css` instead of adding page-specific colors:

| Purpose | Token | Light value |
| --- | --- | --- |
| Page background | `--bg` | `#ECEEF0` |
| Surface | `--card` | `#FFFFFF` |
| Main text | `--text` | `#08112F` |
| Secondary text | `--text-muted` | `#323958` |
| Border | `--border` | `#CCD4DE` |
| Accent | `--primary` | `#5A77DF` |
| Accessible filled action | `--primary-action` | `#506BC9` |
| Dark accent | `--primary-dark` | `#3E53A0` |
| Accent tint | `--primary-tint` | `#E7EBFA` |
| Destructive/error | `--alert` / `--alert-tint` | existing values |
| Card radius | `--radius` | `20px` |
| Card shadow | `--shadow` | existing soft shadow |

The dark-theme variables beside these tokens are part of the same contract. Any new surface must remain readable in both themes.

## Reuse these patterns

- Page surface: `.page-card`
- Page hero: `.app-page-hero` together with the page-specific hero class
- Record table: `.app-data-table` for visible alternating rows, dividers, and hover feedback
- Metric surface: `.stat-card`
- Main action: `.btn-primary`
- Supporting action: `.btn-secondary`
- Destructive action: `.btn-danger`
- Navigation item: `.nav-link`, with `.active` for the current route
- Engagement labels: `.badge-engaged`, `.badge-attentive`, `.badge-confused`, `.badge-bored`, `.badge-disengaged`
- Platform administration pages: existing `.platform-*` patterns
- Teacher dashboard and live-session pages: existing `.teacher-*` patterns

Prefer an existing class or Tailwind composition from a nearby view before adding another shared selector. Put genuinely shared styles in `main.css`; keep one-off layout rules next to the view only when necessary.

## Layout and components

- Use the 8px spacing rhythm. Typical gaps are 16px within a group and 24px between cards.
- Use white cards, a 20px radius, soft shadow, and about 24px padding for primary panels.
- Use `.app-page-hero` for page heroes. On desktop it keeps every hero at the shared Live Session size: 190px fixed height, 24px 32px padding, and a 225px illustration cap. Keep hero copy short enough to fit this fixed height.
- Keep main controls at least 44px tall with a visible focus ring.
- Allow only one visually dominant filled action in a page or modal section. Supporting actions should be outlined.
- Inputs and selects use a white/card surface, `--border`, a 12px radius, and a primary focus state.
- Tables use soft row dividers and hover states. At narrow widths, follow the existing platform table pattern that presents rows as labeled cards rather than adding horizontal overflow.
- Badges must include readable text; color cannot be the only status indicator.
- Use illustrations only when they support an existing hero or empty state. Reuse assets under `frontend/public/illustrations/` before adding new artwork.
- Preserve the existing collapsed sidebar, top bar, light/dark theme, and role-specific navigation behavior.

## Interaction and accessibility

- Use 150–200ms hover/focus transitions and respect `prefers-reduced-motion`.
- Keep semantic labels, keyboard focus, dialog roles, status text, and disabled states intact.
- Maintain readable contrast. Use `--primary-action`, not `--primary`, behind small white button text.
- Do not hide camera, processing, validation, loading, empty, or error states for visual simplicity.
- Do not change API calls, permissions, data logic, routes, or workflows as part of a visual-only task.

## Change checklist

Before finishing a UI change:

1. Compare the surrounding view and reuse its established classes.
2. Check desktop and mobile layouts for clipping or horizontal overflow.
3. Check light and dark themes.
4. Verify hover, keyboard focus, loading, empty, disabled, success, and error states that the edited feature already has.
5. Run the relevant frontend test and `npm run build` from `frontend/`.

For the history and rationale behind the current restyle, see `docs/UI_RESTYLE_PLAN.md`. This style guide takes precedence for ongoing work when that implementation plan describes an earlier intention rather than the interface now in the repository.
