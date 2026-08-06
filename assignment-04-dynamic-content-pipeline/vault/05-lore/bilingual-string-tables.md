# Bilingual String Tables & Localization Rules — Echoes (GDD V2)

## Origin Rule
All user-facing text (environmental lore, UI labels, boss cards, notifications) MUST be generated in English (`text_en`) and Spanish (`text_es`) simultaneously in origin within the same JSON payload. Linear translations after the fact are prohibited.

## UI Overflow Constraint
Spanish text (`text_es`) MUST NOT exceed English text (`text_en`) character length by more than **30%** to prevent UI widget overflow.

## Engine Seam
Lore entries import into Unreal Engine String Tables (`ST_Lore`, `ST_UI`). Hardcoded string literals in Blueprints are strictly forbidden.
