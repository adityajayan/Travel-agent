# Front End Design Skill

## When to Use
Activate this skill when creating, modifying, or reviewing any frontend UI component, page, or style in this project. This includes writing JSX/TSX, Tailwind classes, CSS, or making any visual changes.

## Stack
- **Framework:** Next.js 14 (App Router) with React 18, TypeScript
- **Styling:** Tailwind CSS 3.4 with custom theme + CSS custom properties in `globals.css`
- **Fonts:** Playfair Display (headlines), Syne (UI/labels/buttons), DM Sans (body), Lora (quotes only)
- **No component library** — all components are custom-built with Tailwind utilities

## Design System: Bold Editorial

**Single source of truth:** `docs/DESIGN_SYSTEM.md` — re-read before any visual change.

### Critical Rules

1. **Border radius: 0 everywhere.** No rounded corners on ANY element. No exceptions. Not even 2px.
2. **No gradients anywhere.**
3. **No drop shadows** — use hard offset (`8px 8px 0 #1a1a1a`) or no shadow.
4. **Accent color (#c0392b)** is for small pops only — NEVER as large background fill.
5. **No generic fonts** (Inter, Roboto, Arial) — only Playfair Display, Syne, DM Sans, Lora.

### Color Tokens (use Tailwind classes)

| Token | Hex | Tailwind Class |
|-------|-----|----------------|
| Paper background | #f8f5ef | `bg-paper` |
| Card/elevated | #ffffff / #f0ede6 | `bg-white` / `bg-paper-elevated` |
| Contrast/inverted | #1a1a1a | `bg-contrast` |
| Accent | #c0392b | `text-accent`, `border-accent` |
| Accent soft | rgba(192,57,43,0.08) | `bg-accent-soft` |
| Success | #1a7a4c | `text-success` |
| Text primary | #1a1a1a | `text-text-primary` |
| Text secondary | #3d3d3d | `text-text-mid` |
| Text muted | #777777 | `text-text-muted` |
| Text ghost | #aaaaaa | `text-text-ghost` |
| Border heavy | #1a1a1a 2px | `border-2 border-border-heavy` |
| Border light | #e0dbd3 1px | `border border-border-light` |

### Typography Patterns

```
Headlines:     font-display (Playfair Display)
UI/buttons:    font-ui (Syne) — uppercase, tracking-wide, font-bold, text-xs
Body copy:     font-body (DM Sans) — font-light, leading-relaxed
Quotes:        font-quote (Lora) — italic only
```

**Eyebrow labels:** `font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-accent` with a 24px red bar before.

**Headline emphasis:** Key word wrapped in `<em>` styled italic vermillion (`italic text-accent`) using Playfair Display.

### Component Patterns

**Buttons (primary):**
```
bg-contrast text-paper font-ui text-[0.72rem] font-bold uppercase tracking-[0.1em] px-6 py-3 hover:bg-accent hover:text-white transition-colors duration-250
```

**Cards:**
```
bg-white border-2 border-border-heavy p-6
```
Optional hover accent bar using `.card-hover-bar` CSS class.

**Tags:**
```
border-[1.5px] border-accent-border text-accent font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] px-3 py-1
```

**Inputs:**
```
border-2 border-border-heavy bg-paper px-3 py-2 font-body text-text-primary placeholder:text-text-ghost
```

### Animations (use Tailwind classes)

- `animate-fade-up` through `animate-fade-up-delay-4` for staggered entrance
- `animate-slide-in-right` for alerts
- `animate-shimmer` for loading states
- `.card-hover-bar` CSS class for card hover accent bars

### File Locations

- **Global styles:** `client/src/app/globals.css`
- **Tailwind config:** `client/tailwind.config.ts`
- **Components:** `client/src/components/`
- **Layout:** `client/src/app/layout.tsx`
- **Design spec:** `docs/DESIGN_SYSTEM.md`

### Do / Don't Checklist

**Do:**
- Use 2px black borders as primary structural element
- Use Playfair Display italic in accent color for headline emphasis
- Use `->` arrows (Syne, bold, red) as list markers
- Invert sections to full black for emphasis
- Keep body copy in DM Sans at light weight (300)
- Check `docs/DESIGN_SYSTEM.md` before any visual change

**Don't:**
- Round any corners
- Use gradients
- Use vermillion red as large background fill
- Use generic sans-serif fonts
- Add drop shadows (hard offset or none)
- Over-use bold weight
