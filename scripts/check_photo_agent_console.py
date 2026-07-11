"""Headless browser smoke test for the local Photo Agent console."""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> None:
    screenshot = Path("/tmp/photomate-photo-agent-console.png")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Persistent SSE/MJPEG connections never become network-idle; replace only those
        # streams in this UI smoke test. Their backend behavior is covered by API tests.
        await page.add_init_script(
            "window.EventSource = class { constructor() { this.close = () => {}; } };"
        )
        await page.route(
            "**/api/photo-agent/preview.mjpg",
            lambda route: route.fulfill(status=204, body=b""),
        )

        await page.goto("http://127.0.0.1:8000/photo-agent", wait_until="networkidle")
        await page.locator(".state-card").nth(1).click()
        await page.locator('[data-prompt-key="action.S2.ask_initial"]').wait_for()
        assert await page.locator(".state-card").count() == 6
        assert "S2" in await page.locator("#activeStateTitle").inner_text()

        field = page.locator('[data-prompt-key="action.S2.ask_initial"]')
        original = await field.input_value()
        await field.fill(original + "（浏览器验收）")
        assert await page.locator("#savePrompts").is_enabled()
        await page.locator("#savePrompts").click()
        await page.get_by_text("Prompt 已保存；下一轮对话生效").wait_for()

        page.once("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
        await page.locator("#historyButton").click()
        rollback = page.locator("[data-rollback]").first
        await rollback.wait_for()
        await rollback.click()
        await page.locator("#historyDialog").wait_for(state="hidden")
        await page.locator('[data-prompt-key="action.S2.ask_initial"]').wait_for()
        assert await page.locator('[data-prompt-key="action.S2.ask_initial"]').input_value() == original

        await page.screenshot(path=str(screenshot), full_page=True)
        assert not errors, errors
        await browser.close()
    print(f"browser smoke test passed; screenshot={screenshot}")


if __name__ == "__main__":
    asyncio.run(main())
