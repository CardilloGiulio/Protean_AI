# Supplied asset audit

The 0.3 visual foundation uses the supplied production assets and keeps the supplied moodboards under `design/references/` rather than shipping them as runtime static assets.

## Branding

- `protean-workspace-logo.svg` — primary Protean wordmark.
- `protean-icon.svg` — favicon/app mark.

## Character portraits

Current-use portraits are available for:

- Tom Riddle;
- Hermione Granger;
- Makoto Niijima;
- Ann Takamaki;
- Misato Katsuragi;
- Gendo Ikari;


The retained supplied portraits support the card/header treatment. Sherlock Holmes has been removed from the built-in library and runtime asset set. Primary portraits are **not** treated as complete expression packs for Immersion.

## Backgrounds

- Protean default;
- Old Study;
- Wizard Archive;
- Tokyo Rain;
- Geofront.

Void remains CSS-generated.

The supplied raster backgrounds are sufficient for the current patch. Higher-resolution replacements may improve very large displays later but are not blockers.

## Frame textures

- Notebook paper;
- Parchment.

`frame-notebook-edge.webp` was marked ready in the workbook but was not present in the supplied ZIP. Version 0.3 therefore renders the notebook edge in CSS.

## Moodboards

The three supplied references are retained in `design/references/`:

1. structural skeleton / utility density;
2. optional interactive/stat modules;
3. future background character-expression sprite mode.

The third reference defines the intended direction for Sprite Mode but that mode is deliberately deferred to 0.4.
