"""Export the approved master icon; never redraw or replace its design."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    with Image.open(ASSETS / "quantlab-master.png") as source:
        image = source.convert("RGBA")
        if image.width != image.height or image.width < 256:
            raise ValueError("The icon master must be square and at least 256px.")
        image.resize((256, 256), Image.Resampling.LANCZOS).save(ASSETS / "quantlab.png")
        image.save(ASSETS / "quantlab.ico", format="ICO", sizes=[(size, size) for size in SIZES])


if __name__ == "__main__":
    main()
