"""Generate icon files for Briefcase packaging from source PNG."""

from pathlib import Path

from PIL import Image

SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]
SRC = Path("assets/icons/png/app-icon-1024.png")
OUT_DIR = Path("assets/icons/png")


def main() -> None:
    img = Image.open(SRC).convert("RGBA")
    for size in SIZES:
        resized = img.resize((size, size), Image.LANCZOS)
        out = OUT_DIR / f"app-icon-{size}.png"
        resized.save(out, "PNG")
        print(f"  {out}")

    # Windows .ico (multi-size: 16, 32, 48, 256)
    ico_sizes = [256, 48, 32, 16]
    ico_images = [img.resize((s, s), Image.LANCZOS) for s in ico_sizes]
    ico_path = Path("assets/icons/app-icon.ico")
    ico_images[0].save(
        ico_path,
        format="ICO",
        append_images=ico_images[1:],
    )
    print(f"  {ico_path}")


if __name__ == "__main__":
    main()
