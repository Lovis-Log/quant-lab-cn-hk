"""Generate Quant Lab's original multi-resolution Windows icon."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SIZE = 512


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((16, 16, 496, 496), radius=104, fill="#0B1320")
    draw.rounded_rectangle((29, 29, 483, 483), radius=92, outline="#294051", width=9)

    # Three rising candlesticks and a low-contrast price baseline.
    draw.line((94, 411, 420, 411), fill="#324757", width=13)
    candles = (
        (147, 190, 385, 295, 353, "#4F8CFF"),
        (256, 125, 322, 183, 271, "#24D6A0"),
        (365, 74, 260, 117, 209, "#24D6A0"),
    )
    for x, wick_top, wick_bottom, body_top, body_bottom, color in candles:
        draw.line((x, wick_top, x, wick_bottom), fill=color, width=19)
        draw.rounded_rectangle(
            (x - 31, body_top, x + 31, body_bottom), radius=10, fill=color
        )
    image.save(ASSETS / "quantlab.png")
    image.save(
        ASSETS / "quantlab.ico", format="ICO",
        sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)],
    )


if __name__ == "__main__":
    main()
