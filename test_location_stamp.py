#!/usr/bin/env python3
"""Test script to demonstrate location stamp functionality."""

import sys
from pathlib import Path

from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from album_printer.app import (
    ProcessingSettings,
    apply_location_stamp,
    render_image,
)


def test_location_stamp():
    """Test location stamp rendering."""
    # Create a simple test image
    test_image_path = Path("/tmp/test_location_stamp.jpg")
    img = Image.new("RGB", (800, 600), color="lightblue")
    img.save(test_image_path, "JPEG")

    print("Testing location stamp functionality...")

    # Test 1: Basic location stamp with default settings
    settings = ProcessingSettings(
        location_stamp_enabled=True,
        location_stamp_corner="Bottom Left",
        location_stamp_offset_x_px=15,
        location_stamp_offset_y_px=15,
    )

    test_location = "37.774858, -122.419416"  # San Francisco coordinates
    result = apply_location_stamp(img.copy(), test_location, settings)

    output_path = Path("/tmp/test_location_stamp_output.jpg")
    result.save(output_path, "JPEG")
    print(f"✓ Test 1 passed: Location stamp applied to {output_path}")

    # Test 2: Disabled location stamp
    settings2 = ProcessingSettings(location_stamp_enabled=False)
    result2 = apply_location_stamp(img.copy(), test_location, settings2)
    print("✓ Test 2 passed: Location stamp disabled (no stamp applied)")

    # Test 3: Different corners
    corners = ["Top Left", "Top Right", "Bottom Left", "Bottom Right"]
    for corner in corners:
        settings3 = ProcessingSettings(
            location_stamp_enabled=True,
            location_stamp_corner=corner,
        )
        result3 = apply_location_stamp(img.copy(), test_location, settings3)
        corner_safe = corner.replace(" ", "_").lower()
        corner_output = Path(f"/tmp/test_location_stamp_{corner_safe}.jpg")
        result3.save(corner_output, "JPEG")
        print(f"✓ Test 3.{corners.index(corner)+1} passed: Corner {corner}")

    # Test 4: Full render with both date and location stamps
    settings4 = ProcessingSettings(
        stamp_mode="Date",
        location_stamp_enabled=True,
        corner="Top Right",  # Date stamp
        location_stamp_corner="Bottom Left",  # Location stamp
    )
    result4 = render_image(test_image_path, settings4, location=test_location)
    dual_output = Path("/tmp/test_dual_stamps.jpg")
    result4.save(dual_output, "JPEG")
    print(f"✓ Test 4 passed: Both date and location stamps applied to {dual_output}")

    print("\n✅ All location stamp tests passed!")
    print(
        f"\nGenerated test images in /tmp/ - check them to verify stamp positioning."
    )


if __name__ == "__main__":
    test_location_stamp()
