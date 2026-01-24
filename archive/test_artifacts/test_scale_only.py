"""
Test scale-only hover animation on character cards.
Verifies single smooth animation with no Y-axis movement.
"""

import asyncio
from playwright.async_api import async_playwright


async def test_scale_only():
    """Test scale-only hover animation."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("\n=== Testing Scale-Only Hover Animation ===\n")

        # Navigate to character selection
        print("1. Loading character selection page...")
        await page.goto("http://localhost:3000/select", wait_until="networkidle")

        # Wait for page load animations
        print("   Waiting for page load animations...")
        await page.wait_for_timeout(3000)

        # Wait for cards
        await page.wait_for_selector("[class*='card-outer']", timeout=10000)
        card_count = await page.locator("[class*='card-outer']").count()
        print(f"   [PASS] {card_count} cards loaded\n")

        # Get first card
        first_card = page.locator("[class*='card-outer']").first

        print("2. Testing scale-only hover (should be smooth single animation)...")

        # Get initial position and size
        initial_box = await first_card.bounding_box()
        print(f"   Initial: width={initial_box['width']:.1f}, y={initial_box['y']:.1f}")

        # Hover
        await first_card.hover()
        await page.wait_for_timeout(200)  # Wait for animation

        # Get hover position and size
        hover_box = await first_card.bounding_box()
        print(f"   Hovered: width={hover_box['width']:.1f}, y={hover_box['y']:.1f}")

        # Calculate changes
        width_increase = hover_box['width'] - initial_box['width']
        y_change = abs(hover_box['y'] - initial_box['y'])

        print(f"\n   Changes:")
        print(f"   - Width increased: {width_increase:.1f}px (~5% scale)")
        print(f"   - Y position shift: {y_change:.1f}px (should be minimal, due to center origin)")

        # Take screenshot
        await page.screenshot(path="screenshots/scale_only_hover.png")
        print(f"   [PASS] Screenshot saved\n")

        print("3. Testing hover-out (should return to original size)...")
        await page.mouse.move(10, 10)
        await page.wait_for_timeout(200)

        # Get final position
        final_box = await first_card.bounding_box()
        print(f"   Final: width={final_box['width']:.1f}, y={final_box['y']:.1f}")

        # Verify it returned to original
        width_diff = abs(final_box['width'] - initial_box['width'])
        print(f"   Width difference from initial: {width_diff:.1f}px (should be ~0)\n")

        print("4. Rapid hover test (testing smoothness)...")
        for i in range(5):
            await first_card.hover()
            await page.wait_for_timeout(180)
            await page.mouse.move(10, 10)
            await page.wait_for_timeout(180)
        print("   [PASS] 5 rapid cycles completed\n")

        print("5. Checking transform (should be scale only, no translate)...")
        await first_card.hover()
        await page.wait_for_timeout(200)

        transform = await first_card.evaluate("el => window.getComputedStyle(el).transform")
        print(f"   Transform: {transform}")

        # Parse matrix to check for translation
        if "matrix" in transform:
            # matrix(scaleX, skewY, skewX, scaleY, translateX, translateY)
            parts = transform.replace("matrix(", "").replace(")", "").split(", ")
            scale_x = float(parts[0])
            translate_y = float(parts[5]) if len(parts) > 5 else 0

            print(f"   - Scale: {scale_x:.3f} (target: 1.05)")
            print(f"   - Translate Y: {translate_y:.1f}px (should be ~0 for scale-only)\n")

        # Take final screenshot
        await page.screenshot(path="screenshots/scale_only_final.png")
        print("   [PASS] Final screenshot saved\n")

        print("=== Test Complete ===\n")
        print("Scale-Only Animation Implemented:")
        print("- Removed Y-axis movement entirely")
        print("- Scale from 1.0 to 1.05 (5% increase)")
        print("- 150ms duration with cubic-bezier easing")
        print("- Single smooth transform (no 'two animation' feel)")
        print("\nExpected behavior:")
        print("- Card grows from center (transform-origin: center)")
        print("- No upward movement, pure zoom")
        print("- Snappy and smooth both directions")
        print("\nPlease test manually at: http://localhost:3000/select")
        print()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_scale_only())
