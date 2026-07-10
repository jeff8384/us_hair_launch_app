# Design System

## Atmosphere
Local copy-differentiation lab for US hair-care launch work. The interface should feel like an editorial strategy desk: light, focused, comparative, and built around the draft-copy review workflow from `CopyDiffLab.jsx`. Competitor ingestion remains present, but the first-class experience is comparing Sephora/Ulta saturation against the user's product copy.

## Color Tokens
- `--bg`: #f7f3ef
- `--paper`: #fffdfa
- `--ink`: #241b22
- `--muted`: #796d75
- `--line`: #e2d9d3
- `--berry`: #a62e5c
- `--copper`: #da6a2c
- `--sage`: #2e7d5b
- `--amber`: #c58a22
- `--danger`: #b23a44

## Typography
Use a serif display face only for the main title. Operational labels, controls, charts, and cards use system sans fonts. Keep letter spacing at zero except compact uppercase section labels where CSS explicitly uses wider tracking.

## Spacing
Use an 8px grid. Primary page padding is 24px desktop and 14px mobile. Cards use 20px internal spacing and 8px radius. The main workspace is a two-column grid on desktop and single-column on mobile.

## Components
Buttons are compact, squared, and action-oriented. Source/profile cards encode retailer separation. The draft form owns the product/category/copy inputs. The result area uses a radar, coverage bars, differentiation/crowded/gap lists, compliance flags, and two explicit rewrite variants: `marketing` and `compliance_safe`.

## Motion
Use only quick hover/focus transitions under 160ms. No decorative animation is needed for this workflow.

## Depth
Use borders before shadows. Keep the surface quiet enough for repeated copy review. Avoid nested cards and decorative background effects.
