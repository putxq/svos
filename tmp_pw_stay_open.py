from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('http://127.0.0.1:9000', wait_until='domcontentloaded', timeout=90000)
    print('Browser opened at http://127.0.0.1:9000 and will stay open. Press Ctrl+C here to stop.')
    page.wait_for_timeout(3600000)
