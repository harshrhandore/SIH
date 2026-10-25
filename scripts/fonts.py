from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for family, weights in [("fraunces", [600]), ("instrument-sans", [400, 500, 600]), ("ibm-plex-mono", [400])]:
    folder = ROOT / "apps/web/public/fonts" / family
    folder.mkdir(parents=True, exist_ok=True)
    source = ROOT / "node_modules/@fontsource" / family
    for weight in weights:
        (folder / f"latin-{weight}.woff2").write_bytes(
            (source / "files" / f"{family}-latin-{weight}-normal.woff2").read_bytes()
        )
    (folder / "LICENSE").write_bytes((source / "LICENSE").read_bytes())
css = ROOT / "apps/web/src/app/globals.css"
text = (
    css.read_text()
    .replace("@import url('/fonts/fonts.css');\n", "")
    .replace("'Instrument Sans',Arial,sans-serif", "var(--font-body),Arial,sans-serif")
    .replace("Fraunces,Georgia,serif", "var(--font-heading),Georgia,serif")
    .replace("'IBM Plex Mono',monospace", "var(--font-mono),monospace")
)
css.write_text(text)
