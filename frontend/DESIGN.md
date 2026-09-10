---
name: KAIROS
description: Plataforma interna del semillero de ML — el estándar de la categoría, jugado en serio, con neutros entintados de violeta y bordes de un pelo en vez de sombras.
colors:
  ground: "#fbfafc"
  surface: "#ffffff"
  sunken: "#f5f3f8"
  line: "#e7e4ee"
  line-strong: "#d3cedd"
  ink: "#1f1b24"
  ink-muted: "#6b6470"
  ink-placeholder: "#746c7c"
  ink-faint: "#948d99"
  accent: "#4b34e0"
  accent-hover: "#3d28c4"
  accent-soft: "#efecfd"
  accent-line: "#d9d2fa"
  danger: "#c2255c"
  danger-hover: "#a41d4d"
  danger-soft: "#fdeef3"
  danger-line: "#f6ccdb"
  success: "#1f7a4d"
  success-soft: "#eaf6ef"
  success-line: "#c3e5d2"
  notice: "#8a5a10"
  notice-soft: "#fdf3e3"
  notice-line: "#f0dcb8"
typography:
  title:
    fontFamily: "Figtree, ui-sans-serif, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Figtree, ui-sans-serif, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  subtitle:
    fontFamily: "Figtree, ui-sans-serif, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  body:
    fontFamily: "Figtree, ui-sans-serif, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.625
    letterSpacing: "normal"
  label:
    fontFamily: "Figtree, ui-sans-serif, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
  meta:
    fontFamily: "Figtree, ui-sans-serif, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
  wordmark:
    fontFamily: "Figtree, ui-sans-serif, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.22em"
rounded:
  control: "0.5rem"
  panel: "0.75rem"
  focus: "0.25rem"
  pill: "9999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
  "12": "48px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.sunken}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "36px"
  button-ghost-hover:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.ink}"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "44px"
  button-danger-hover:
    backgroundColor: "{colors.danger-hover}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "44px"
    width: "100%"
  input-disabled:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.ink-muted}"
  badge-neutral:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  badge-accent:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  badge-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  badge-danger:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  badge-notice:
    backgroundColor: "{colors.notice-soft}"
    textColor: "{colors.notice}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  alert-error:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
  alert-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
  alert-notice:
    backgroundColor: "{colors.notice-soft}"
    textColor: "{colors.notice}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
  alert-info:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "44px"
  nav-item-active:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    typography: "{typography.label}"
  list-row-hover:
    backgroundColor: "{colors.sunken}"
    rounded: "{rounded.control}"
    padding: "16px 12px"
---

# Design System: KAIROS

## Overview

**Creative North Star: "The Quiet Desk"**

KAIROS is the category standard played straight, without irony and without a metaphor world. It owns calm: there is nothing to learn before you can work. The finish bar is Notion — generous air, friendly type, low density, no ornament competing with content. A student who opens this on a phone between classes should find the answer to "what do I owe and when" without decoding anything.

The surface is a near-white violet-tinted paper (`ground`), and structure is drawn with hairline rules rather than shadows. There is exactly one accent — the violet end of the brand mark — and exactly one alarm color, a carmine-shifted magenta reserved for destruction and errors. Everything neutral is tinted toward that violet, so the whole app reads as one family instead of a template with a brand color dropped in. The type is a single family, Figtree, in a compressed ramp: the interface says almost everything at 14px and earns attention with weight and space, not size.

Depth is spent, not sprinkled. One shadow token exists and it belongs to things that genuinely float above content. Everything else — panels, list rows, active navigation, the cold-start band — separates with a hairline or a tonal shift.

**Key Characteristics:**
- Violet-tinted neutrals; never a pure gray, never a warm cream
- Hairline borders in place of shadows; one shadow token, for floating layers only
- One accent (violet), one alarm (carmine-magenta), one green, one amber
- Single type family, compressed ramp, tabular numerals everywhere
- 44px touch targets gated on `any-pointer-coarse`, from 360px up
- One motion gesture: a 240ms rise with exponential ease-out, no bounce

## Colors

A near-white violet-tinted paper carrying one saturated accent and three status hues, all of them muted enough to sit beside text without shouting.

### Primary
- **Brand Violet** (`accent`): The violet end of the logo gradient, as a flat color. Primary buttons, links inside authenticated content, the focus ring, the text caret, the active navigation item, and `info` alerts. Nothing else.
- **Violet Pressed** (`accent-hover`): Hover and active state of anything filled with the accent.
- **Violet Wash** (`accent-soft`) and **Violet Hairline** (`accent-line`): The tinted background and border for accent badges, `info` alerts, active navigation, and text selection.

### Secondary
- **Carmine Alarm** (`danger`): The magenta end of the mark, pushed toward carmine so it reads as alarm rather than decoration. Destructive buttons, field error text, invalid field borders, error alerts and badges.
- **Carmine Pressed** (`danger-hover`), **Carmine Wash** (`danger-soft`), **Carmine Hairline** (`danger-line`): The filled-hover, tinted background and border of the same family.

### Tertiary
- **Field Green** (`success`, with `success-soft` / `success-line`): The only green in the system. Confirmations, active-account badges, server-up state.
- **Amber Wait** (`notice`, with `notice-soft` / `notice-line`): Waiting and long-delay states. Its home is the cold-start band and the expired-session notice.

### Neutral
- **Violet Paper** (`ground`): The application background. Every screen sits on it directly; signed-out screens have no floating card because there is nothing to lift away from.
- **Panel White** (`surface`): Only for what must detach from the paper — the sidebar, the mobile top bar, input fields.
- **Sunken Violet** (`sunken`): Row hover, secondary-button hover, disabled field fill.
- **Hairline** (`line`) and **Hairline Strong** (`line-strong`): Section rules, row separators and panel edges; the stronger value carries control borders and the scrollbar thumb.
- **Ink** (`ink`): Primary text. **Ink Muted** (`ink-muted`): secondary text and metadata, at 4.5:1 on paper. **Ink Placeholder** (`ink-placeholder`): placeholders only, also at 4.5:1. **Ink Faint** (`ink-faint`): disabled text and the disabled select chevron.

### Named Rules
**The Tinted Neutral Rule.** Every neutral is violet-tinted — blue is the highest channel in each. No pure black, no pure gray, and no warm cream: a neutral whose red channel leads has left the system, however small the drift.

**The Gradient Stays In The Mark Rule.** The blue-to-magenta gradient exists only inside the logo raster. No UI surface reproduces it. In the interface the two ends of the mark appear as separate flat colors: violet for the accent, carmine for the destructive.

**The Placeholder Ink Rule.** Placeholder text uses `ink-placeholder`, never `ink-faint`. `ink-faint` is disabled-only; a placeholder set in it reads as a dead field.

**The Color Is Never Alone Rule.** Every tone carries the words that say what happened. Badges and alerts always contain text; hue confirms the message, it is never the message.

## Typography

**Body / Display Font:** Figtree (with `ui-sans-serif`, `sans-serif`), loaded at 400/500/600/700 plus 400 italic.
**Label/Mono Font:** none — numerals are handled by `font-variant-numeric: tabular-nums` on `body`, so dates, counters and table columns align without a second family.

**Character:** One friendly geometric sans doing every job. Warmth comes from its round bowls and open apertures rather than from a display face; hierarchy comes from weight and whitespace rather than from size jumps.

### Hierarchy
- **Title** (600, 24px, tight tracking): The screen title in the page header, once per authenticated screen.
- **Headline** (600, 20px): The single heading on screens without a page header — signed-out screens and not-found.
- **Subtitle** (500, 16px): The heading line of an empty state. The only place 16px appears.
- **Body** (400, 14px, 1.625 line-height): Everything else — form values, list rows, descriptions, alert text. Prose blocks cap at `max-w-prose`; empty-state copy at 28rem.
- **Label** (500, 14px): Field labels, button text, in-screen section headings (`h2`), active navigation.
- **Meta** (500, 12px): Badge text and secondary row metadata such as join dates. Never for something the user must read in order to act.
- **Wordmark** (600, 14px, 0.22em tracking, all caps): The word KAIROS beside the monogram in the horizontal lockup. The only tracked-out uppercase text in the system, and it exists only inside the brand component.

### Named Rules
**The One Family Rule.** Figtree ships with the app and does every job; the operating system's default face never appears. No Inter, no Arial, no system stack in a component class.

**The Fourteen-Pixel Floor Rule.** Body text is 14px. The 12px step is for badges and non-essential metadata only; nothing a user must read to complete a task drops below 14px.

**The Weight-Not-Size Rule.** The ramp has four steps across 12–24px. Emphasis is bought with weight (500/600) and whitespace, never by inventing a new size.

## Layout

The app is a two-region shell: a fixed 240px sidebar from 768px up, and below that a top bar with a collapsible menu, because a sidebar eats the usable width of a 360px phone. The sidebar is sticky at full viewport height; the main region is the only scrolling column.

Content is a single centered column with a per-screen maximum: 64rem for dense administration lists, 56rem for the dashboard, and a hard 380px for every signed-out screen. Container padding is 20px on phones and 32px from 640px up; vertical padding is 32px rising to 48px. Signed-out screens take 56px of top air rising to 80px and center their column on the flat background with no card.

Rhythm is an 8-point scale with 4px half-steps: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 48. Fields in a stack separate by 20px, a label sits 6px above its control, a section heading sits 12px above its content, and sections separate with a hairline plus 32–40px of air — never with a box.

Responsive behavior is stack-then-row: filter groups, page headers and list rows are column-stacked on phones and become rows at 640px. The only breakpoints in use are 640px and 768px. The floor is 360px wide.

Touch targets are 44×44px minimum, expressed as `min-h-11` (plus `min-w-11` for icon-only controls). Compact controls declare `min-h-9 any-pointer-coarse:min-h-11`.

### Named Rules
**The Any-Pointer Rule.** Touch sizing is gated on `any-pointer-coarse:`, never `pointer-coarse:`. A touchscreen laptop reports a fine *primary* pointer and would keep the 36px control while a finger is aiming at it.

**The Single Column Rule.** One centered column per screen with an explicit max width. No two-column content layouts, no sidebars inside the content region.

## Elevation & Depth

The system is flat by conviction. Structure comes from hairline rules and tonal shifts between `ground`, `surface` and `sunken`: a panel is distinguished from the page by a 1px border and a lighter fill, not by a shadow. Exactly one shadow token exists, reserved for layers that genuinely float over content — menus, dialogs, popovers. Nothing that is part of the page's own structure casts a shadow.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 8px 24px -6px rgb(31 27 36 / 0.14), 0 2px 6px -2px rgb(31 27 36 / 0.08)`): The only shadow. Two soft layers, both in ink tint. For menus, dialogs, and anything overlaying content it does not belong to.

### Named Rules
**The Hairline Before Shadow Rule.** If a thing sits *in* the page, it separates with `line`. If it sits *over* the page, it gets the float shadow. There is no third option and no second shadow value.

**The Ink-Tinted Shadow Rule.** Shadows are cast in the ink violet (`rgb(31 27 36 / …)`), never in black. A pure-black shadow on violet paper reads as dirt.

## Shapes

Two radii carry the whole system: gently rounded controls (8px) on everything a user touches or reads inside — buttons, inputs, selects, alerts, list-row hover surfaces, navigation items — and softer panels (12px) on larger containers. Badges are the single exception: fully rounded pills, which is what makes a status read as a status at a glance. The keyboard focus ring rounds at 4px so it hugs text and irregular targets closely.

Borders are 1px, always. Icons are line-drawn at 1.75 stroke weight with round caps and joins on a 24-unit grid, inlined as SVG and inheriting `currentColor`: the select chevron, the menu and close glyphs, the spinner. The interface draws its own marks rather than borrowing OS widgets or font glyphs.

Motion is a single gesture: a 240ms rise of 4px from 0.4 opacity on `cubic-bezier(0.16, 1, 0.3, 1)`. Color transitions run 150ms. All animation collapses to 0.01ms under `prefers-reduced-motion`.

### Named Rules
**The Two Radii Rule.** 8px for controls, 12px for panels, full round for badges. A new radius value is a new system, not a new component.

**The No Bounce Rule.** Easing is exponential ease-out. Nothing overshoots and nothing springs back.

## Components

The component character is quiet and sturdy: correct hit areas, honest states, no decoration that is not load-bearing.

### Buttons
- **Shape:** Gently rounded (8px), 44px minimum height, centered content with an 8px gap so a spinner can precede the label.
- **Primary:** Accent violet fill, white text, 16px horizontal padding. Disabled drops the fill to 45% opacity rather than turning gray.
- **Secondary:** Panel white with a strong hairline border and ink text; hover fills to `sunken`.
- **Ghost:** No fill, muted ink, 12px padding; hover fills to `sunken` and darkens text to full ink. For tertiary actions such as "retry".
- **Danger:** Carmine fill, white text, same geometry as primary.
- **Hover / Focus:** Color-only transition at 150ms; the global focus ring. Buttons never move on hover.
- **Loading:** The label stays and a 16px spinner appears before it; the button disables itself and sets `aria-busy`. A button never collapses to a bare spinner.
- **Compact:** 36px tall, rising to 44px on any coarse pointer.

### Badges
- **Style:** Pill, 1px tinted border, tinted wash fill, matching saturated text, 12px medium, never wrapping.
- **State:** neutral, accent, success, danger, notice. Always contains a word.

### Alerts
- **Style:** Full-width block, 8px radius, 1px tinted border on the matching wash, saturated text at body size and relaxed line height.
- **Tones:** error, success, notice, info, mapped to carmine, green, amber and violet. Error takes `role="alert"`; the rest take `role="status"`.

### Inputs / Fields
- **Style:** Panel white on a strong hairline border, 8px radius, 44px minimum height, 12px horizontal padding, body-size ink, placeholder in placeholder ink. Hover darkens the border to `ink-faint`.
- **Focus:** The global 2px accent outline at 2px offset; the border itself does not change. The caret is accent violet.
- **Invalid:** Border switches to carmine and the control carries `aria-invalid`.
- **Disabled:** `sunken` fill, muted ink, not-allowed cursor.
- **Field wrapper:** Label 6px above the control; below it exactly one message line — the error replaces the hint when both exist, linked by `aria-describedby`. Optional fields say so beside the label rather than marking the required ones.
- **Select:** The native element styled by the same directive, plus the drawn chevron.
- **Password reveal:** Every password field is wrapped in `ui-password-input`, which projects the native input and lays a 44×44 icon-only toggle over its right edge; the field declares `trailingSlot` so the text never runs under it. The button carries the action as its accessible name — "Mostrar la contraseña" / "Ocultar la contraseña" — and a mouse press on it does not take focus off the field.

### Navigation
- **Sidebar (768px and up):** 240px, panel white, right hairline, sticky at full height. Brand at the top, items in a 2px-gapped list, account block pinned to the bottom behind a top hairline.
- **Item:** Body size, muted ink, 44px tall, 8px radius; hover fills `sunken` and darkens the ink. Active fills `accent-soft` with accent text at medium weight.
- **Mobile (below 768px):** Panel-white top bar with the horizontal lockup and a 44×44 drawn hamburger/close toggle carrying `aria-expanded`; the nav drops below it as a bordered panel and closes on selection.
- Only destinations that actually exist are listed.

### List Rows
The recurring pattern for every collection in the app.
- The row element carries the hover surface: `-mx-3 px-3`, so the `sunken` fill bleeds 12px past the content on both sides and rounds at 8px.
- An inner wrapper carries the `border-b border-line` separator, so the row rule aligns with the section rules above and below instead of inheriting the bleed.
- Content is a one-column grid that becomes `minmax(0,1fr) auto` at 640px: identity on the left (name, then email, then 12px metadata), actions right-aligned and wrapping.
- Long values truncate; identity never wraps to a second line.

### Empty States
Left-aligned on phones, centered from 640px. A 16px medium heading naming what is missing, a muted body line saying why it is empty, and — only when one exists — the action that fills it. No illustration and no apology.

### Cold-Start Band
The system's signature component. When a request passes 3 seconds, an amber band enters with the standard rise at the very top of the document flow: sticky, `role="status"` with `aria-live="polite"`, amber wash on an amber hairline, a 16px spinner and one sentence of plain Spanish. It pushes content down rather than covering it, and stays pinned, because during a 90-second wait a scroll must not remove the only explanation the user has.

### Brand Lockup
Two variants from the same rasters: the stacked lockup (132px on signed-out screens, 96px on not-found) and a horizontal pairing of the 24px monogram with the word KAIROS set in the interface face, because the original lockup is vertical and shrinks to illegibility in a bar. Every shipping raster is derived from the owner's original JPEG by exact un-compositing, documented in `public/brand/PROVENANCE.md`; nothing is redrawn or approximated. Replacing the rasters is a one-file change.

### Named Rules
**The Drawn Chevron Rule.** Every `select` carries `.ui-select`: the OS triangle is turned off and a 1.75-stroke chevron is drawn in its place, with a second rule for the disabled state. Because a data URI cannot read a custom property, the chevron color is written as a literal hex in those two rules — the one sanctioned color duplication in the system. If `ink-muted` or `ink-faint` change, those two hexes change with them.

**The Row Bleed Rule.** Hover bleeds, rules do not. The hover surface goes on the outer row with `-mx-3 px-3`; the hairline goes on the inner wrapper. Swapping them makes the row rule overshoot the section rule, which is visible and wrong.

**The Native Element Rule.** Form controls are styled by a directive on the native element, never wrapped in a component that replaces it. Type, autocomplete and keyboard behavior belong to the user, not to us.

## Do's and Don'ts

### Do:
- **Do** build new screens from the existing primitives — button, input directive plus field, alert, badge, page header, empty state, spinner. A new one-off control is a system change, not a screen detail.
- **Do** keep every neutral violet-tinted, with blue as the highest channel.
- **Do** separate structure with `line` hairlines and reserve the float shadow for layers that overlay content.
- **Do** gate touch sizing on `any-pointer-coarse:` and hold 44×44px.
- **Do** carry the row pattern exactly: hover bleeds via `-mx-3 px-3`, hairline on the inner wrapper.
- **Do** render dates through the Bogotá date pipe and leave tabular numerals in force so columns of numbers align.
- **Do** write user-facing text in Spanish and code identifiers in English.
- **Do** pair every colored state with the words that explain it.
- **Do** let the global `:focus-visible` ring be the only focus treatment.

### Don't:
- **Don't** introduce a second accent, a second green, or any hue outside accent / danger / success / notice.
- **Don't** reproduce the logo's blue-to-magenta gradient on any UI surface — or any gradient, on any surface.
- **Don't** use `ink-faint` for text a user has to read; it is disabled-only, and placeholders have their own token.
- **Don't** put a card inside a card, or wrap a signed-out form in a floating panel; the flat 380px column is the pattern.
- **Don't** add a second shadow value, or a hard offset shadow.
- **Don't** ship a `select` with the operating system's triangle, or an icon from a glyph font; icons are inline SVG at 1.75 stroke.
- **Don't** use bouncy, elastic or overshooting easing, or animate outside the 240ms rise and 150ms color-transition vocabulary.
- **Don't** invent a radius, a font size, or a spacing step outside the recorded scales.
- **Don't** set gray text on a colored background, and never use a pure black or gray.
- **Don't** link to a destination that does not exist yet.
