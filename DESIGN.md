---
name: パーキング・メーター・マップ
description: On-street parking meters and tickets in four Japanese cities, on one map a driver can read at a glance.
colors:
  meter-plate-blue: "#1E4E8C"
  meter-plate-wash: "#DDE7F3"
  weekend-green: "#1B8A4B"
  weekday-blue: "#1F63C6"
  caution-amber: "#8A5A12"
  caution-wash: "#F6ECDB"
  here-orange: "#F28C28"
  search-pin-red: "#D1452E"
  asphalt-ink: "#141B24"
  kerb-grey: "#3B4756"
  faded-paint: "#667384"
  overcast-ground: "#EEF1F4"
  signboard-white: "#FBFCFD"
  pavement-grey: "#E4E9EF"
  lane-line: "#CBD3DC"
typography:
  display:
    fontFamily: "Zen Kaku Gothic New, Hiragino Sans, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.2
  headline:
    fontFamily: "Zen Kaku Gothic New, Hiragino Sans, system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 700
    lineHeight: 1.35
  title:
    fontFamily: "Zen Kaku Gothic New, Hiragino Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.55
  body:
    fontFamily: "Zen Kaku Gothic New, Hiragino Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Zen Kaku Gothic New, Hiragino Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
  caption:
    fontFamily: "Zen Kaku Gothic New, Hiragino Sans, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.55
  overline:
    fontFamily: "Zen Kaku Gothic New, Hiragino Sans, system-ui, sans-serif"
    fontSize: "10px"
    fontWeight: 500
    letterSpacing: "0.14em"
rounded:
  tag: "4px"
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "14px"
  sheet: "18px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
components:
  button-primary:
    backgroundColor: "{colors.meter-plate-blue}"
    textColor: "{colors.signboard-white}"
    rounded: "{rounded.pill}"
    padding: "9px 16px"
    typography: "{typography.title}"
  button-secondary:
    backgroundColor: "{colors.signboard-white}"
    textColor: "{colors.asphalt-ink}"
    rounded: "{rounded.pill}"
    padding: "9px 16px"
  filter-toggle:
    backgroundColor: "{colors.signboard-white}"
    textColor: "{colors.asphalt-ink}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
  filter-toggle-open:
    backgroundColor: "{colors.meter-plate-blue}"
    textColor: "{colors.signboard-white}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
  search-field:
    backgroundColor: "{colors.signboard-white}"
    textColor: "{colors.asphalt-ink}"
    rounded: "{rounded.lg}"
    padding: "0 14px"
    height: "44px"
  map-button:
    backgroundColor: "{colors.signboard-white}"
    textColor: "{colors.asphalt-ink}"
    rounded: "{rounded.lg}"
    size: "46px"
  floating-panel:
    backgroundColor: "{colors.signboard-white}"
    textColor: "{colors.asphalt-ink}"
    rounded: "{rounded.xl}"
    padding: "20px"
  bottom-sheet:
    backgroundColor: "{colors.signboard-white}"
    textColor: "{colors.asphalt-ink}"
    rounded: "{rounded.sheet}"
    padding: "18px"
  badge-daily:
    backgroundColor: "{colors.weekend-green}"
    textColor: "{colors.signboard-white}"
    rounded: "{rounded.pill}"
    padding: "3px 9px"
  badge-closed:
    backgroundColor: "{colors.weekday-blue}"
    textColor: "{colors.signboard-white}"
    rounded: "{rounded.pill}"
    padding: "3px 9px"
  list-row:
    backgroundColor: "{colors.signboard-white}"
    textColor: "{colors.asphalt-ink}"
    padding: "11px 16px"
  list-row-selected:
    backgroundColor: "{colors.meter-plate-wash}"
    textColor: "{colors.asphalt-ink}"
    padding: "11px 16px"
  caution-note:
    backgroundColor: "{colors.caution-wash}"
    textColor: "{colors.caution-amber}"
    rounded: "{rounded.sm}"
    padding: "8px 10px"
---

# Design System: パーキング・メーター・マップ

## Overview

**Creative North Star: "The Kerbside Signboard"**

The interface works like a well-made Japanese road sign. It is calm, plainly worded, legible from arm's length, and it never competes with the street it describes. The map is the street. The coloured lines drawn on it (green, blue, solid, dashed) are the only loud things on screen, and every piece of chrome exists to point at them. Everything else is navy, near-white and grey, set in one plain Japanese gothic typeface.

The design is dense but not crowded. Panels float over the map as white signboards with thin grey rules, and they never cover more of the map than the task needs. On a phone the details panel opens as a sheet from the bottom, and the selected section is kept visible above it. There are light and dark themes. Dark is a night-road version with the same roles, not a different identity.

The direction is **crisp and utilitarian**. The incumbent system uses soft floating shadows and pill-shaped buttons. Future work should push toward flatter, tool-like surfaces: 1px lines before shadows, tighter radii before rounder ones, and no decoration that doesn't carry information.

**Key Characteristics:**
- The map is the hero; the chrome is signage around it.
- Colour means data. Green and blue say which days a section can be used; solid and dashed say meter or ticket.
- One typeface, Zen Kaku Gothic New, in three weights.
- Thin grey rules structure every panel.
- Tap targets of 44px or more, because people use it on the road with one hand.
- Warnings stay visible, in amber, at the point of use.

## Colors

A cool, near-monochrome road palette of navy, overcast grey and signboard white. Three data colours (green, blue, amber) carry meaning and are never used as decoration.

### Primary
- **Meter-Plate Blue** (#1E4E8C): the enamel blue of a parking meter plate. It is the brand colour, used in the app icon, `theme-color`, the primary action (「◯ 区間を表示」), the open state of the filter toggle, the active-filter count and links. In dark mode it lightens to #7FB0F0 so it stays readable on dark surfaces.
- **Meter-Plate Wash** (#DDE7F3): a pale tint of the brand blue that marks the selected row in the list. Dark: #172536.

### Secondary (data colours)
- **Weekend Green** (#1B8A4B): sections usable on weekends and holidays too (土日・祝日も使える). Used for map lines, the legend key and the detail badge. Dark: #4FC983.
- **Weekday Blue** (#1F63C6): sections closed on Sundays and holidays (日曜・祝日は除く). It is deliberately a brighter, more saturated blue than Meter-Plate Blue, so brand and data never blur. Dark: #5C9CFF.

### Tertiary
- **Caution Amber** (#8A5A12) on **Caution Wash** (#F6ECDB): the accuracy warning in the details panel ("the signs on the street take priority"). Dark: #E0B66E on #2A2114.
- **Here Orange** (#F28C28): the current-location dot, with a 3px white ring. It sits above the zone lines.
- **Search-Pin Red** (#D1452E): the marker for a searched place, with a 3px white ring.

### Neutral
- **Asphalt Ink** (#141B24): main text. Dark: #E3E9F0.
- **Kerb Grey** (#3B4756): secondary text, distances, group headers. Dark: #B3BFCC.
- **Faded Paint** (#667384): labels, icons, captions, meta lines. Dark: #8795A5.
- **Overcast Ground** (#EEF1F4): the page background behind the map. Dark: #0C1117.
- **Signboard White** (#FBFCFD): every panel, bar, button and sheet. Dark: #141B23.
- **Pavement Grey** (#E4E9EF): hover fills, sticky group headers, the map background before tiles load. Dark: #1D2630.
- **Lane Line** (#CBD3DC): the 1px border and divider on everything. Dark: #2C3845.

### Named Rules
**The Colour-Is-Data Rule.** Green, Weekday Blue and amber each mean exactly one thing. Never use them for decoration, emphasis or brand. If a new state needs colour, it gets its own documented meaning, or it stays grey.

**The Two-Blues Rule.** Meter-Plate Blue is the brand; Weekday Blue is data. Keep them visibly apart: never put a brand-blue element directly on a map line or next to a legend key where the two could be confused.

**The Line Is the Loudest Thing Rule.** Nothing in the chrome may be more saturated or more prominent than the zone lines on the map.

## Typography

**Display Font:** Zen Kaku Gothic New (with Hiragino Sans, system-ui, sans-serif)
**Body Font:** Zen Kaku Gothic New (same stack)

**Character:** A single plain gothic, modern Japanese signage type in three weights (400, 500, 700). There is no second typeface. Hierarchy comes from weight and size, never from a contrasting family.

### Hierarchy
- **Display** (700, 17px, 1.2): the app name in the header. Drops to 16px on phones.
- **Headline** (700, 19px, 1.35): the section heading in the details panel, usually the address.
- **Title** (700, 15px): list-row names, filter toggle, primary button text. Also used at 17px for the list panel heading.
- **Body** (400, 15px, 1.55): base text, the details list, menu items. Inputs use 16px so iOS doesn't zoom in on focus.
- **Label** (400, 13px): filter labels, result count, sort control, group headers (at 700).
- **Caption** (400, 12px): list meta, distances, warnings, the legend.
- **Overline** (500, 10px, 0.14em tracking, Latin caps): the single 「ON-STREET PARKING · JAPAN」 line above the title. Badges use a relative of this: 700, 11px, 0.04em.

### Named Rules
**The One-Typeface Rule.** Zen Kaku Gothic New only. Numbers that line up in columns (distances) use `font-variant-numeric: tabular-nums`, not a monospace font.

**The Spaced-Latin-Only Rule.** Letter-spacing is for short Latin caps (the overline, badges). Never track Japanese text.

## Layout

The map fills the whole screen below a 56px header bar. All other UI floats over the map at a 12px inset from the edges:

- **Top left:** a stack 400px wide at most (`min(400px, 100% − 24px)`). It holds the search field, then a row with the filter toggle and the result count, then the filter panel when it's open.
- **Bottom left:** the legend, as a 2×2 grid.
- **Bottom right:** the locate button above Leaflet's zoom control.
- **Right side:** the details panel, 380px wide, slides in from the right.
- **Left edge:** the list panel, 400px wide, opens from the menu. On wide screens the search stack and legend move right to make room (`left: 412px`).

There is one breakpoint, at **760px**.
- **Phones:** the list panel covers the full width. The details panel becomes a bottom sheet, at most 58% of the viewport high, and respects `safe-area-inset-bottom`. The legend moves up so it clears the two-line attribution.

Spacing runs 4 / 8 / 12 / 16 / 20px. The inner spacing of panels is 14–20px. List rows are 11px × 16px. Filter rows split into a fixed `5.5em` label column and a flexible control column, with a 1px rule between rows.

**The Map-First Rule.** No panel may open covering the map by default. Filters, list and details all start closed or collapsed, and the map is visible on first load.

## Elevation & Depth

This is a hybrid system. The panels are flat signboards (1px Lane Line border, no gradients). Every element floating over the map also has one shared shadow that separates it from the busy map tiles. Elements anchored in the page (the header, rows inside panels) have no shadow; the header has only a bottom rule.

### Shadow Vocabulary
- **Map float** (`box-shadow: 0 1px 2px rgba(20,27,36,.06), 0 8px 24px rgba(20,27,36,.10)`): the only shadow in the system. It is used on the search field, filter toggle, count pill, filter panel, map buttons, legend, menu, list panel and details panel. Dark: `0 1px 2px rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.4)`.

### Named Rules
**The One-Shadow Rule.** There is exactly one shadow, and it means "this floats over the map". Never add a second, larger or coloured shadow.

**The Rule-Before-Shadow Rule.** This is the "crisp and utilitarian" direction. New surfaces are separated with a 1px Lane Line first. Add the map-float shadow only when the surface actually sits on top of map tiles. Treat reducing the shadow on existing chrome as welcome refinement, not a redesign.

## Shapes

Corners are softly rounded rectangles on a stepped scale, and the radius grows with the size of the element:
- tags: 4px
- inputs and menu items: 8px
- icon buttons and the legend: 10px
- the search field and map buttons: 12px
- panels and cards: 14px
- the bottom sheet's top corners: 18px

Standalone actions (buttons, the filter toggle, badges, the count) are full pills (999px). Icons are 24×24 line icons with a 2px stroke, round caps and joins, and no fill, drawn as inline SVG in `currentColor`. The app icon is a Meter-Plate Blue square with a 14px radius and a white "P" drawn in a single stroke.

On the map, section lines have round caps. Line width follows the zoom level (from 3 to 9px) and is 5px heavier when selected. Tickets are dashed with a gap of about 1.8 × the line width. Single-point sections are 6px circles.

**The No-New-Curves Rule.** Don't add radii beyond this scale, and don't round anything further than it already is. Under the crisp direction, a new element takes the smaller of the two neighbouring steps.

## Components

### Buttons
Plain, sturdy, pill-shaped.
- **Shape:** full pill (999px).
- **Primary:** Meter-Plate Blue fill with Signboard White bold text, 9px × 16px. There is one per view, for the main "show results" action.
- **Secondary:** Signboard White with a 1px Lane Line border and Asphalt Ink text. Used for 「条件をクリア」 and the directions links.
- **Close / icon:** a 40–44px square with a 10px radius, transparent at rest and Pavement Grey on hover.

### Chips (filter toggle, count, badges)
- **Filter toggle:** a white pill with a 1px rule, an 18px icon and bold 14px text. When open it becomes Meter-Plate Blue with white text. It carries a 20px round count showing how many filters are active.
- **Count pill:** 13px Kerb Grey text on white, with the number in Asphalt Ink bold.
- **Day badges:** 11px bold text in Weekend Green or Weekday Blue with white text. The "kind" badge is an outline pill in Kerb Grey.
- **Tag:** a tiny 10px outline label with a 4px radius, placed next to list names.

### Cards / Containers
- **Corner Style:** 14px, or 18px across the top only for the bottom sheet.
- **Background:** Signboard White.
- **Shadow Strategy:** map float, only when over the map (see Elevation).
- **Border:** 1px Lane Line.
- **Internal Padding:** 14–20px.

### Inputs / Fields
- **Search:** a white field 44px tall with a 12px radius, a 1px rule and an 18px Faded Paint magnifier. The text is 16px with no inner border and no focus outline; the field itself is the affordance.
- **Selects:** 1px Lane Line border, 8px radius, 8px padding, 15px text. Disabled selects drop to 45% opacity.

### Navigation
- **Header:** 56px, Signboard White with a bottom rule. It holds the overline and title on the left and a 44px hamburger on the right.
- **Menu:** a 220px dropdown panel, 12px radius, with a 6px inner gutter. Items are 12px-padded rows with a 20px Faded Paint icon and 15px text, and turn Pavement Grey on hover.

### Zone Line (signature component)
The zone line is the product. Its colour comes from the day class (Weekend Green / Weekday Blue) and its dash from the kind (solid for meters, dashed for tickets). It is 85% opaque at rest; selected, it becomes fully opaque, 5px heavier and brought to the front. Hovering shows a sticky tooltip with the section's name. The legend uses the same vocabulary: 18×5px keys with a 3px radius, with dashed keys drawn as a repeating gradient.

### Details Panel / Bottom Sheet (signature component)
It opens with a 0.2s ease slide: from the right on desktop, from the bottom on phones. It shows the heading, the badges, a two-column `dt/dd` list of facts in Faded Paint / Asphalt Ink, two equal-width direction buttons (Google Maps / Apple Maps), then the amber caution note last.

## Do's and Don'ts

### Do:
- **Do** keep the map visible and dominant on first load (the Map-First Rule).
- **Do** use Weekend Green, Weekday Blue and dashed versus solid lines only for their documented meanings, with the same meaning on the map, in the legend and on the badges.
- **Do** separate surfaces with a 1px Lane Line (#CBD3DC) first; reach for the single map-float shadow only over the map.
- **Do** keep tap targets at 44px or more, and inputs at 16px or more so iOS doesn't zoom in.
- **Do** define every colour for both themes through the `:root` custom properties, and keep dark mode a straight re-mapping of the same roles.
- **Do** show the accuracy warning in Caution Amber on Caution Wash wherever section details appear.

### Don't:
- **Don't** use Meter-Plate Blue for data, or Weekday Blue for brand or actions (the Two-Blues Rule).
- **Don't** add a second typeface, a monospace face, or letter-spacing on Japanese text.
- **Don't** introduce new shadows, gradients, glows or coloured shadows. There is one shadow, and it means "floats over the map".
- **Don't** make chrome louder than the zone lines. No saturated fills on panels and no decorative illustration over the map.
- **Don't** round things further than the existing radius scale.
- **Don't** hide or soften the data warnings to make a screen look cleaner.
