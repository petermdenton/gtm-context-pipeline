# Interface system

The GTM portal's design system provides semantic tokens, framework-free HTML/CSS
components, and a working component library. Version 0.1 refines the current
studio interface with quiet neutral surfaces, a restrained green accent,
readable controls, and explicit evidence and review states.

Open `/design-system` on a running portal server. The library is a public static
page containing only clearly labeled synthetic examples. It makes no API calls
and does not read or write a client workspace. It also works at
`/design-system.html`. All files ship through the existing package-data rules.

## Source files

| File in `gtm_pipeline/portal_static/` | Responsibility |
| --- | --- |
| `design-tokens.css` | Shared colors, typography, spacing, radius, elevation, controls and motion |
| `components.css` | Reusable `.ui-*` primitives with responsive and interaction states |
| `portal-theme.css` | Adopts the tokens in existing studio portal selectors |
| `design-system.html` | Overview, foundations, component specimens and an account-list pattern |
| `design-system.css` | Layout and presentation belonging only to the library |
| `design-system.js` | Demo behavior, live token values and contrast calculations |

The existing portal loads tokens before its legacy styles, then components and
the adoption stylesheet afterward. Existing page layouts and application logic
remain in their current files. The classic view retains its original theme.
This is incremental adoption, not a complete rewrite of the legacy CSS.

## Principles

1. Give the work room. Use one primary action per context and let content set
   the hierarchy. Separate information with space and borders before adding cards.
2. Keep the source close. Pair metrics with the date, denominator and provenance
   needed to interpret them. Missing information is not zero.
3. Say what happened. Use specific event labels and retain unknown, pending and
   failure states. A successful import does not mean its records are reviewed.
4. Make clarity accessible. Use real labels, visible focus, native controls,
   keyboard navigation and text alongside status colors.

## Foundations

Use semantic custom properties instead of copying a hex value into a component.
Tokens are the source of truth; the Foundations page reads their current values.

| Role | Token | Initial value |
| --- | --- | --- |
| Page canvas | `--ds-color-canvas` | `#fcfcfb` |
| Raised surface | `--ds-color-surface` | `#ffffff` |
| Quiet surface | `--ds-color-surface-subtle` | `#f5f6f3` |
| Primary text | `--ds-color-text` | `#252923` |
| Supporting text | `--ds-color-text-muted` | `#686f62` |
| Primary action | `--ds-color-action` | `#293126` |
| Accent surface | `--ds-color-accent` | `#dbe7c8` |
| Focus / links | `--ds-color-focus`, `--ds-color-link` | `#345f9d` |

Status colors have dedicated foreground/background pairs for success, warning,
danger and information. They communicate meaning only when accompanied by a
visible label. A selected navigation item is not a successful outcome.

Typography uses Inter when locally available and otherwise native system sans.
There are no font downloads. The component scale is 12, 13, 14, 16, 20, 28 and
36px. Use weights 400, 500 and 600. Monospace is reserved for token names, IDs and
technical values. Numeric comparisons use tabular numbers.

Spacing follows 4, 8, 12, 16, 20, 24, 32, 40, 48 and 64px. Radii are 6px for
compact elements, 8px for controls, 12px for cards and 20px for dialogs. The
default control height is 40px; small controls are 32px. Touch buttons grow to
44px. A 140ms transition handles hover changes. Reduced-motion settings disable
decorative motion.

## Components

| Building block | Class | Behavior / usage |
| --- | --- | --- |
| Button | `.ui-button` | Primary, secondary, quiet, danger, small, icon, disabled and busy states |
| Text input | `.ui-input` | Use a persistent label; tie hints and errors through `aria-describedby` |
| Select | `.ui-select` | Prefer native selection for a short, fixed option list |
| Textarea | `.ui-textarea` | Resizable multiline input with a persistent label |
| Checkbox | `.ui-checkbox` | Independent, optional choices |
| Switch | `.ui-switch` | A clearly named binary setting; retain native input semantics |
| Badge | `.ui-badge` | Compact text state with optional semantic tone |
| Card | `.ui-card` | A self-contained group of related information |
| Alert | `.ui-alert` | Explain an issue and the recovery step; use `role="alert"` for new urgent errors |
| Tabs | `.ui-tabs` | One selected panel; arrow keys, Home/End and roving tab focus |
| Table | `.ui-table` | Native table semantics, scoped headers, horizontal overflow and optional compact density |
| Empty state | `.ui-empty` | Explain the space and offer one useful next action |
| Dialog | `.ui-dialog` | Native modal, labeled title, Escape dismissal and return of focus |
| Toast | `.ui-toast` | Announce an actual transient outcome through a polite live region |

Field wrappers (`.ui-field`), hints, validation messages, loading indicators and
skeletons support these primitives. Icon-only buttons always need an accessible
name. Decorative SVGs are hidden from assistive technology. Dialog and tab
behavior in the demo is a reference implementation; CSS alone does not supply
those interactions to another page.

```html
<link rel="stylesheet" href="/design-tokens.css">
<link rel="stylesheet" href="/components.css">

<div class="ui-field">
  <label class="ui-label" for="project-name">Project name</label>
  <input class="ui-input" id="project-name" aria-describedby="project-name-hint">
  <span class="ui-hint" id="project-name-hint">Choose a name your team recognizes.</span>
</div>
<button class="ui-button ui-button--primary" type="submit">Save draft</button>
<span class="ui-badge ui-badge--warning">Needs review</span>
```

## Product state vocabulary

| State | Meaning |
| --- | --- |
| Draft | Work has been saved for further editing or review |
| Reviewed | A review has been explicitly recorded |
| Published | The destination reports the artifact as published |
| Enrolled | Membership in a specific program or sequence has been recorded |
| Sent | The platform reports a message as sent; this does not imply a reply or receipt |
| Verified | An observed effect was checked against the expected result and dated evidence |
| Unknown | The relevant evidence is missing or inconclusive |

These states are separate facts, not an automatic progression or permission to
perform the next action. Badges should describe the relevant record or operation,
not imply the entire account is ready for activation.

## Patterns and responsive behavior

The account-list pattern demonstrates search, review-state filtering, density
control, empty results and recovery. It preserves the difference between account
review state and source evidence. A source count is never a fit score.

The library uses a fixed sidebar on desktop and horizontal section navigation on
small screens. Component grids collapse to one column, toolbars wrap and tables
scroll inside their container. Long labels wrap rather than overflowing the page.
The library supports a light theme in this version.

## Validation and maintenance

Validated the live demo at desktop and 390px phone width: navigation, dialog
validation and save feedback, focus return, keyboard tabs, combined search and
filters, empty results, density control, and page overflow. Core text token pairs
are checked in the Foundations page against a 4.5:1 contrast threshold. This is
not a full WCAG or screen-reader audit of the existing portal.

Run the repository test suite for the current result; historical interface checks do not replace release validation. Static routes return the
expected MIME types under the portal's existing content security policy. The
library has no inline script, inline styling, CDN or framework dependency.

For a new component, start with an existing token, include normal/hover/focus/
disabled/error behavior where applicable, add a synthetic specimen and verify
its narrow layout. Change a token once rather than overriding the same value in
several components. Keep product-specific behavior in the portal and library-only
layout in `design-system.css`.
