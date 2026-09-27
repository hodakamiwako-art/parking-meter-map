# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Drivers who are already out on the road in a Japanese city. They open the map on their phone as they near where they're going, to find an on-street parking meter or parking-ticket section (パーキング・メーター／パーキング・チケット) they can use right now, then head there.

## Product Purpose

パーキング・メーター・マップ shows every published on-street parking meter and ticket section in Tokyo, Osaka, Sapporo and Kyoto (808 sections: Tokyo 752, Osaka 41, Sapporo 10, Kyoto 5) on one map. Results are sorted by distance and can be filtered by area, day, time, time limit and vehicle type. It succeeds when a driver gets from "I need to park near here" to directions to a usable section in a few taps.

## Positioning

- **One map, four cities.** Each prefectural police force publishes its own data in its own format: open data and a map in Tokyo, tables in Osaka, lists of landmarks in Sapporo and Kyoto. This is the only place they are combined into one searchable map.
- **Quick on a phone.** The map comes first, sections are listed nearest first, and directions (Google Maps / Apple Maps) open in one tap. It is meant to be faster to use while out than the official police sites.

## Operating Context

- Used mostly on a phone, often at a glance, near the destination. The details panel opens as a bottom sheet on phones, and the selected section is kept visible above it.
- Filter order: prefecture → ward/city → town → day → time (usable now / usable at a given hour) → time limit → vehicle type.
- "Usable now" accounts for the day of the week, national holidays (`data/holidays.json`, 2026–2027), the New Year period, and Sapporo's winter closure (general sections run April 1 – November 30 only).
- Place and station search uses the GSI (国土地理院) place-name search.

## Capabilities and Constraints

- A static site hosted on GitHub Pages, built with vanilla JS and Leaflet 1.9.4 (in `vendor/`). There is no build step and no backend; keep it that way. After changing `*.css` / `*.js`, run `python3 build/stamp.py` so the version stamps in `index.html` update.
- **Japanese only.** No English UI is planned.
- Supports light and dark themes. Map tiles come from CARTO when `config.js` has a key; otherwise OpenStreetMap, which is light only.
- Line colour shows the days a section can be used: green = usable on weekends and holidays too; blue = closed on Sundays and holidays. Solid lines are meters and dashed lines are tickets.
- Terms in use: 区間 (section), パーキング・メーター, パーキング・チケット, 制限時間, 手数料, 利用時間, 除く日, 車種.

## Brand Commitments

- The name is パーキング・メーター・マップ, with the sub-label "ON-STREET PARKING · JAPAN". The voice is plain, factual Japanese, as used in the UI and README.
- **The data warnings always stay visible.** Signs and meters on the street take priority over the map. Osaka lines are traced from the police maps and don't show the exact side of the road or the gaps at intersections. The ends of Sapporo and Kyoto lines can be tens of metres off.
- Sources must always be credited: 警視庁 (CC BY 4.0), 大阪府警察, 北海道警察, 京都府警察, OpenStreetMap contributors (ODbL), 国土地理院, 内閣府, CARTO.

## Evidence on Hand

- Section data: `data/zones.geojson`. Source data and build scripts are in `build/`, and provenance is written up in `README.md`.
- There are no user testimonials, usage numbers or press. Don't make any up.

## Product Principles

1. The fastest route from "near here" to a usable section wins. Every screen is judged by taps and seconds while on the road.
2. Be honest about accuracy. Keep the caveats about approximate lines and signs taking priority; never make the data look more precise than it is.
3. Treat all four cities the same way, while stating each city's rules (winter closure, freight-only sections, ticket-only Osaka).
4. Stay light and static: no accounts, no backend, no framework.
