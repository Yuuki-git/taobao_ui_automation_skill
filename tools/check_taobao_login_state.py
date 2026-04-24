import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright


def main() -> None:
    storage_path = PROJECT_ROOT / "storage" / "taobao_storage_state.json"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(storage_path))
        page = context.new_page()

        page.goto("https://www.taobao.com", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        print("URL:", page.url)
        print("TITLE:", page.title())
        print("VISIBLE TEXT PREVIEW:")
        print(page.locator("body").inner_text(timeout=5000)[:1000])

        input("检查浏览器中是否显示已登录状态，按回车退出...")
        browser.close()


if __name__ == "__main__":
    main()