# ⬛ DESIGN SYSTEM — Bold Editorial

**This is the canonical design specification. Every UI element, component, page, and visual must follow these rules exactly.**

> **IMPORTANT:** The existing `concierge-landing.html` uses a previous dark ink/gold theme. That theme is now deprecated. This Bold Editorial system replaces it entirely. Do not reference the old color palette, typography, or effects.

> **WORKFLOW NOTE:** This file is the single source of truth for all visual decisions. When making any visual change, re-read this file first. If the design system is ever updated, it will be updated here and then propagated to the Tailwind config and components.

---

## Colors

### Core Surfaces

```
Background (paper):            #f8f5ef
Card / elevated surfaces:      #ffffff
Subtle elevation within cards: #f0ede6
Inverted / contrast sections:  #1a1a1a  (stats bars, CTA blocks, chat headers, dark panels)
```

### Text

```
Primary:                       #1a1a1a
Secondary:                     #3d3d3d
Muted:                         #777777
Ghost / placeholder:           #aaaaaa
```

### Accent (Vermillion Red — Use Sparingly)

```
Primary accent:                #c0392b  (eyebrow labels, editorial pops, hover states, tags — NEVER as large background fill)
Accent soft background:        rgba(192, 57, 43, 0.08)
Accent border:                 rgba(192, 57, 43, 0.2)
```

### Status

```
Success / green:               #1a7a4c  (confirmations, under-budget, positive states)
Success soft background:       rgba(26, 122, 76, 0.08)
```

### Borders

```
Structural borders:            #1a1a1a at 2px  (cards, grids, nav bottom, section dividers, inputs, chat frames)
Internal dividers:             #e0dbd3 at 1px  (within cards, between list items, subtle separators)
```

### CSS Custom Properties (copy into globals)

```css
:root {
  --bg: #f8f5ef;
  --bg-card: #ffffff;
  --bg-contrast: #1a1a1a;
  --bg-elevated: #f0ede6;
  --text: #1a1a1a;
  --text-mid: #3d3d3d;
  --text-muted: #777777;
  --text-ghost: #aaaaaa;
  --accent: #c0392b;
  --accent-soft: rgba(192, 57, 43, 0.08);
  --accent-border: rgba(192, 57, 43, 0.2);
  --green: #1a7a4c;
  --green-soft: rgba(26, 122, 76, 0.08);
  --border: #e0dbd3;
  --border-heavy: #1a1a1a;
}
```

---

## Typography

### Fonts (all Google Fonts)

| Role                        | Font                                                       | Usage                                                    |
|-----------------------------|------------------------------------------------------------|---------------------------------------------------------|
| Headlines / display         | **Playfair Display** (400, 500, 600, 700; italic 400, 500) | Hero text, section titles, card headings, feature names  |
| UI / labels / nav / buttons | **Syne** (400, 500, 600, 700, 800)                         | Navigation, buttons, eyebrow labels, tags, small caps    |
| Body copy                   | **DM Sans** (300, 400, 500)                                | Paragraphs, descriptions, form labels, general body text |
| Testimonial quotes          | **Lora** (400 italic)                                      | Pull quotes and testimonial text only                    |

### Google Fonts Import

```
https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300;1,9..40,400&family=Lora:ital,wght@0,400;1,400&display=swap
```

### Type Scale

| Element                 | Font             | Size                         | Weight     | Notes                                             |
|-------------------------|------------------|------------------------------|------------|---------------------------------------------------|
| Hero headline           | Playfair Display | clamp(3.2rem, 5.8vw, 5.5rem) | 400        | line-height: 1.0, letter-spacing: -0.02em         |
| Section title           | Playfair Display | clamp(2.2rem, 4.2vw, 3.6rem) | 400        | line-height: 1.08                                 |
| Card heading            | Playfair Display | 1.3rem                       | 500        | line-height: 1.2                                  |
| Eyebrow / section label | Syne             | 0.72rem                      | 700        | uppercase, letter-spacing: 0.14em, color: #c0392b |
| Nav links               | Syne             | 0.72rem                      | 600        | uppercase, letter-spacing: 0.08em                 |
| Button text             | Syne             | 0.72rem                      | 700        | uppercase, letter-spacing: 0.1em                  |
| Body copy               | DM Sans          | 0.88–1.05rem                 | 300 or 400 | line-height: 1.65–1.8, color: #777                |
| Tags / small labels     | Syne             | 0.65rem                      | 700        | uppercase, letter-spacing: 0.1em                  |
| Timestamps              | DM Sans          | 0.62rem                      | 400        | color: #aaa                                       |

### Emphasis Pattern

In headlines, the key word or phrase uses `<em>` styled as: `font-style: italic; color: #c0392b;` in Playfair Display italic. Example: "Travel, *handled* for you." where "handled" is italic vermillion.

---

## Shape Language

**Border radius: 0 everywhere.** No rounded corners on ANY element — buttons, cards, inputs, avatars, tags, chat bubbles, modals. This is the single most distinctive visual rule. No exceptions. Not even 2px.

---

## Logo

**Primary lockup (horizontal):** A square mark containing a Playfair Display "C" (weight 500) next to the wordmark "CONCIERGE" in Syne (weight 700, uppercase, letter-spacing 3px).

- Mark: 40×40px square, filled `#1a1a1a`, white "C" inside
- On dark backgrounds: mark fills `#f8f5ef`, dark "C" inside, white wordmark

**Accent variant:** Mark square filled with `#c0392b` instead of black.

**Logomark only (favicons, app icons):** Square "C" mark at 64px, 44px, 32px, 20px.

**Type-only variant:** "CONCIERGE" in Syne, weight 800, uppercase, letter-spacing 4px.

---

## Paper Texture

Apply a subtle paper grain overlay to the body:

```css
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 300 300' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='5' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.025'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 9999;
}
```

---

## Animation

- **Scroll reveal:** Fade up (opacity 0→1, translateY 22px→0) over 0.6s ease-out at 10% intersection
- **Card hover accent bar:** 3px top bar in `#c0392b` scales from scaleX(0) to scaleX(1) from left over 0.4s
- **Chat messages:** Fade up individually with staggered delays, 0.45s ease-out
- **Alert cards:** Slide in from right (translateX 20px→0) 0.5s ease-out, staggered 700ms
- **Button hovers:** 0.25s transition on background and color
- **Page load hero:** Staggered fadeUp with animation-delay (0s, 0.08s, 0.16s, 0.24s, 0.35s)

---

## Component Specifications

### Buttons

**Primary:**

- Background: `#1a1a1a`, text: `#f8f5ef`
- Font: Syne, 0.72rem, weight 700, uppercase, letter-spacing 0.1em
- Padding: 0.7rem 1.5rem
- Border-radius: 0
- Hover: background `#c0392b`, text `#fff`

**Outline:**

- Border: 2px solid `#1a1a1a`, background transparent, text `#1a1a1a`
- Same font specs as primary
- Hover: fills `#1a1a1a`, text `#f8f5ef`

**On dark backgrounds:**

- Primary: white background, dark text; hover fills `#c0392b`
- Outline: white border, white text; hover fills white

### Cards

- Background: `#f8f5ef` or `#ffffff`
- Border: 2px solid `#1a1a1a`
- No border radius
- Padding: 2.5–3rem
- Hover: subtle background change, optional 3px top accent bar in `#c0392b` animating in via scaleX

### Tags / Pills

- Border: 1.5px solid `rgba(192, 57, 43, 0.2)`
- Font: Syne, 0.65rem, weight 700, uppercase
- Color: `#c0392b`
- Padding: 0.3rem 0.7rem
- No border radius

### Section Labels (Eyebrows)

- Font: Syne, 0.72rem, weight 700, uppercase, letter-spacing 0.14em
- Color: `#c0392b`
- Preceded by a horizontal bar: 24px wide, 3px tall, `#c0392b`
- Bar and text flex-aligned with 0.6rem gap

### Navigation

- Fixed top, full width
- Background: `rgba(248, 245, 239, 0.9)` with backdrop-filter: blur(16px)
- Bottom border: 2px solid `#1a1a1a`
- Logo: "CONCIERGE" in Syne, 0.9rem, weight 700, uppercase, letter-spacing 0.1em
- Links: Syne, 0.72rem, weight 600, uppercase
- CTA button uses primary button style

### Magazine Grids

For value props, feature grids, step sequences:

- Single outer border: 2px solid `#1a1a1a`
- Internal cell dividers: 1px solid `#e0dbd3`
- No gap between cells — borders do the separation
- Creates magazine-layout grid feel, not a card grid

### Inverted Sections

For high-emphasis blocks (stats, CTA, disruption callouts):

- Background: `#1a1a1a`
- Text: `#ffffff` (headings), `rgba(255,255,255,0.55)` (body), `rgba(255,255,255,0.25)` (ghost)
- Borders: `rgba(255,255,255,0.1)` or `rgba(255,255,255,0.15)`

### Chat / Conversation UI

- Chat window: border 2px solid `#1a1a1a`, box-shadow `8px 8px 0 #1a1a1a` (hard offset shadow)
- Chat header: full `#1a1a1a` background, white text, Syne uppercase
- Chat body: `#f8f5ef` background
- Assistant bubbles: white background, 1.5px border `#e0dbd3`, border-radius 0
- User bubbles: `#1a1a1a` background, `#f8f5ef` text, border-radius 0
- Avatars: square (no border-radius), 24px
- Input field: border-radius 0, 1.5px border

### Confirmation / Success States

- Background: `rgba(26, 122, 76, 0.08)`
- Border: 1.5px solid `rgba(26, 122, 76, 0.2)`
- Text: `#1a7a4c`, weight 600
- No border radius

### Benefit Lists

- No bullet characters
- Each item prefixed with `→` in Syne, weight 700, color `#c0392b`
- Body: DM Sans, 0.88rem, weight 300, color `#3d3d3d`

### Stat Numbers

- Font: Playfair Display, ~2.8rem, weight 400
- Sublabel: Syne, 0.68rem, weight 600, uppercase, letter-spacing 0.1em

---

## Design System Do / Don't

**Do:**

- Use 2px black borders as the primary structural element
- Keep border-radius at 0 on everything — no exceptions
- Use Playfair Display italic in `#c0392b` for headline emphasis words
- Use hard offset box-shadow (`8px 8px 0 #1a1a1a`) on hero-level elements
- Use `→` arrows (Syne, bold, red) as list markers
- Invert sections to full black for emphasis moments
- Keep body copy in DM Sans at light weight (300)

**Don't:**

- Round any corners — not even 2px or 4px
- Use gradients anywhere
- Use vermillion red as a large background fill — accent only
- Use generic sans-serif fonts (Inter, Roboto, Arial)
- Add drop shadows (use hard offset or no shadow)
- Use emoji as decorative elements in production UI
- Over-use bold — Syne at weight 700 in small uppercase labels provides enough emphasis
- Reference the old dark ink/gold theme from concierge-landing.html
- Make visual changes without first re-reading `docs/DESIGN_SYSTEM.md`
