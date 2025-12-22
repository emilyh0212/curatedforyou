from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://beliapp.com")

    print("Log in manually, then close the browser window.")

    page.wait_for_timeout(5 * 60 * 1000)

    context.storage_state(path="scripts/storage_state.json")
    browser.close()
