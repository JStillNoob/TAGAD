# TAGAD UI Visual Restyle Plan

> The restyle described here has been implemented. Use `docs/UI_STYLE_GUIDE.md` as the canonical reference for future UI changes.

## Scope for this pass

Restyle the existing frontend to reflect the pastel SaaS reference. Keep every existing element, route, control, label, chart, data point, interaction, and screen in its current place and order. Change only colors, font families and weights, spacing, radius, shadows, and visual states. Adjust control padding and height where needed to reach a 44px target without changing the workflow.

Do not edit backend code, API contracts, frontend data logic, or navigation behavior. Do not add a notification button, calendar, camera feed, progress indicator, chart, card, tab, or other UI that does not already exist. The reference image guides styling, not content or structure.

Apply the UX principles visually: Aesthetic-Usability through consistent polish; Von Restorff through one visually dominant filled action per screen; Fitts through usable control dimensions; Miller through spacing that groups existing content; Zeigarnik through clearer styling of progress that already exists.

## System admin reference refinement

The later system admin dashboard request explicitly calls for the supplied image's missing visual details. For that dashboard only, add the four metric icons, a decorative hero illustration, and illustrations with checkmarked capability lists in the two existing management cards. Keep the original routes, data, and actions. Other screens remain under the visual-only scope above.

## Sidebar and dashboard interaction refinement

When the sidebar is collapsed, retain a compact rail with the TAGAD logo and the existing navigation icons; keep each icon's destination and provide a tooltip. The four system admin KPI cards open the relevant Organizations or Organization Admins page. The two illustrated management cards show an explicit open-page indicator while remaining whole-card links.

The top bar no longer includes the global search field. Show the current page title as plain text in its place, and keep the sidebar toggle, theme toggle, and account menu.

## Platform management page refinement

Use the supplied Organizations dashboard image as inspiration for the system admin Organizations and Organization Administrators pages. Match the platform overview's pastel hero, one white rounded panel containing both filters and results, blue accents, illustrations, and outlined row actions. Keep the existing fields, filters, data, pagination, and create/edit/archive/deactivate workflows. On narrow screens, show each table row as a labeled card so every action remains visible without horizontal scrolling.

## Teacher dashboard refinement

Use the supplied Teacher Dashboard Overview image as inspiration for the teacher dashboard. Give teacher pages the shared pastel shell. On the dashboard, pair the greeting and Start New Session action with a teacher illustration, show icon-led KPI cards, and style recent sessions, engagement, and quick actions as matching panels. Keep existing counts, session rows, engagement data, alerts, and destinations. Use illustrated empty states only when the corresponding data is absent.

## Teacher Live Session refinement

Use the supplied Modern Live Session Teacher Dashboard image as inspiration for the setup screen. Reuse the teacher illustration in a pastel hero with the single dominant Prepare Session action; place the session details and preview alongside separate upload, presentation library, and recent-session cards. Keep the existing subject, presentation, camera, upload, and session workflows. Preserve the top bar's plain Live Session label without restoring global search. Show pagination only when a list spans more than one page; keep all prepared and active presentation controls intact.

## Design tokens

Use these values as the starting light-theme tokens in `frontend/src/assets/main.css`, mapped into Tailwind utilities where useful:

```css
:root {
  --bg: #ECEEF0;
  --border: #CCD4DE;
  --text-muted: #323958;
  --text: #08112F;
  --primary-dark: #3E53A0;
  --primary: #5A77DF;
  --card: #FFFFFF;
  --radius: 20px;
  --shadow: 0 8px 24px rgba(50, 57, 88, 0.08);
}
```

- Keep Inter as the only font family. Change the existing Google Fonts request in `frontend/index.html` from weights 300/400/500/600/700 to 400/600; do not load the font twice.
- Use 400 for body copy and 600 for headings, statistics, table headers, buttons, and emphasis. Replace existing visual uses of other weights.
- Use an 8px spacing scale, about 24px between existing cards, and about 16px between related controls or content. Retain current grid and DOM order.
- Use white cards with 20px radius, the shared soft shadow, and 24px padding where the current content fits. Avoid hard card borders; retain borders where they communicate separation or input boundaries.
- Keep a dark-theme token set so the existing theme toggle remains legible and coherent. The light theme is the visual reference.

## Element styling checklist

| Existing element | Visual change |
| --- | --- |
| Page background | Use `--bg`; a subtle blue-tinted gradient is optional if it does not reduce readability. |
| Sidebar and active navigation | Keep its current structure and labels. Use white surface, softer radius, muted inactive items, and a 12%-tinted primary active state with `--primary-dark` text and icon. |
| Top bar | Show the current page title as plain text; keep the sidebar toggle, theme toggle, and account menu as rounded controls. |
| Cards and panels | Use `--card`, 20px radius, consistent shadow and padding. Preserve their current locations and contents. |
| Headings and large statistics | Use `--text` and weight 600; style existing prominent numbers at 48px or larger where they fit without overflow. Keep their current labels. |
| Primary actions | One filled, visually dominant action per screen: `--primary` fill, white text, 12-14px radius, at least 44px tall; `--primary-dark` hover state. Restyle other existing actions as secondary without changing their function. |
| Secondary and destructive actions | Use white or transparent secondary buttons with `--primary-dark` outline and text. Use an outlined alert accent for existing destructive actions; keep their present positions. |
| Inputs and selects | White fill, 1px `--border`, 12px radius, and a visible 2px `--primary` focus ring. Style existing compact selects as tinted pills where appropriate. |
| Tables | Keep columns and row order. Remove strong vertical rules, use `--border` row dividers, muted weight-600 headers, and a light row hover state. |
| Existing charts | Restyle existing bars with a vertical primary-to-primary-dark gradient and rounded tops where the chart permits it. Use `--border` for tracks and gridlines. Restyle an existing ring only if one already exists. |
| Engagement states | Use the requested five-step blue ramp for fills and chips. Retain visible text labels so color is not the only cue; never use `--border` as text. |
| Alerts and anomalies | Reserve a single amber or red accent for existing alert, error, and destructive states. Do not introduce a new alert surface. |
| Existing progress visuals | Use a `--border` track, `--primary` fill, and rounded ends. Do not create new progress indicators. |
| Chips and badges | Use pill radius, tinted background, and a darker readable label. |
| Interaction states | Use 150-200ms transitions for hover, focus, and active states; honor reduced-motion preferences. |

## Implementation order

1. **Baseline and inventory.** Capture current desktop and mobile screenshots for each existing role and list the filled buttons, chart types, progress visuals, and dark-theme surfaces already present. Record any overflow before styling.
2. **Global foundation.** Update `frontend/index.html`, `frontend/tailwind.config.js`, and `frontend/src/assets/main.css` for the font request, light and dark tokens, shared buttons, cards, chips, focus states, and motion.
3. **Shared shell and controls.** Restyle `frontend/src/layouts/AppLayout.vue` and the existing components under `frontend/src/components/`, including pagination, forms, theme toggle, and pickers. Preserve the remaining controls and navigation behavior.
4. **Existing views.** Apply the same visual system to Dashboard, Session, Analytics, Reports, Classes, Settings, User Management, Organizations, System Logs, and authentication views. Keep their templates' element order, data bindings, and existing role visibility intact. In the live session view, preserve the current focus-mode and camera-status behavior.
5. **Charts and states.** Update existing Chart.js configuration and CSS-only chart visuals. Style loading, empty, error, selected, disabled, and live states consistently. Keep the five engagement labels and current data-quality notices.
6. **Visual and functional review.** Compare before/after screenshots at desktop and mobile widths; verify all three roles, light/dark themes, keyboard focus, text wrapping, and no horizontal overflow. Run the frontend build and existing relevant tests after implementation.

## Completion criteria

- No application elements, routes, controls, labels, data, or interactions were added, removed, moved, or reordered.
- No backend files, API contracts, or frontend data logic were changed.
- Every screen has at most one filled blue action that visually dominates; existing secondary and destructive actions remain usable.
- Existing controls are comfortably usable, with a 44px target for main interactive controls, without overlap or broken layouts.
- Inter 400 and 600 are the only requested font weights; card radius, shadow, spacing, and state styling are consistent.
- Focus indicators are visible; state charts have text labels; `--border` is not used for text; reduced-motion and dark-theme behavior still work.
- Existing frontend build and relevant tests pass, and desktop/mobile screenshots show the same content and structure as before.

## Contrast decision

White text on `--primary` (`#5A77DF`) has approximately **4.09:1** contrast, below the **4.5:1** target for normal-size text. The implementation keeps `--primary` for visual accents and uses `--primary-action: #506BC9` for small filled-button labels (approximately **4.90:1**). Hover uses `--primary-dark` (`#3E53A0`), where white text is approximately **7.12:1**.
