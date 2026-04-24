from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> None:
    storage_dir = Path("storage")
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / "taobao_storage_state.json"

    user_data_dir = Path("storage") / "taobao_user_data"

    with sync_playwright() as p:
        # 用 persistent context，比普通 new_context 更接近真实浏览器用户环境
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1366, "height": 900},
        )

        page = context.new_page()
        page.goto("https://www.taobao.com", wait_until="domcontentloaded", timeout=30000)

        print("请在打开的浏览器中手动登录淘宝。")
        print("登录成功后，确认页面右上角/首页显示已登录状态。")
        input("确认已登录后，回到这里按回车保存登录态... ")

        page.wait_for_timeout(3000)

        print("当前 URL:", page.url)
        try:
            print("当前标题:", page.title())
        except Exception:
            print("当前标题读取失败，但会继续保存。")

        context.storage_state(path=str(storage_path))
        print(f"已保存登录态到: {storage_path.resolve()}")

        context.close()


if __name__ == "__main__":
    main()