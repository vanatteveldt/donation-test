import argparse
import logging
import time
from pathlib import Path

from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright


def run_test(url: str, file: Path, headless: bool = False, close_page: bool = False, sleep: int = 0):
    with sync_playwright() as p:

        browser = p.firefox.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        # 1. Navigate to the URL
        page.goto(url)

        # 2. Open the upload dialog by clicking 'Verder', YouTube, and 'Doorgaan'
        # This had errors with timing, so we add waits
        try:
            btn = page.locator("div.prism-btn").filter(has_text="Verder")
            btn.wait_for(state="visible", timeout=3000)
            time.sleep(1)
            btn.click()
        except TimeoutError:
            logging.info("No consent screen detected, continuing...")
        btn = page.get_by_text("YouTube", exact=True)
        btn.wait_for(state="visible", timeout=120000)
        btn.click()

        btn = page.get_by_text("Doorgaan", exact=True)
        btn.wait_for(state="visible", timeout=120000)
        btn.click()
        logging.info("Waiting for file uploader to load")

        # 3. File Upload Procedure
        # This is inside an iframe, so open that first and then upload the file
        target_frame = page.frame_locator('iframe[src*="amazonaws.com"]')
        with page.expect_file_chooser() as fc_info:
            btn = target_frame.get_by_text("Kies bestand")
            btn.wait_for(state="visible", timeout=120000)
            btn.click()

        fc_info.value.set_files(file)
        logging.info(f"Uploading file {file}")
        btn = target_frame.get_by_text("Verder", exact=True)
        btn.wait_for(state="visible", timeout=120000)
        btn.click()

        # 4. Give consent
        target_frame = page.frame_locator('iframe[src*="amazonaws.com"]')
        confirm_btn = target_frame.locator("#confirm-button").filter(has_text="Ja, deel voor onderzoek")
        logging.info("Waiting for upload to complete and consent button to appear...")
        confirm_btn.wait_for(state="visible", timeout=120000)
        confirm_btn.scroll_into_view_if_needed()
        logging.info("Confirming upload")
        confirm_btn.click()

        # 5. We're done, but let's click the buttons and check the process is done
        finish_btn = page.locator("div.prism-btn").filter(has_text="Volgende, ik ben klaar")
        finish_btn.click()

        klaar_header = page.get_by_test_id("finished-title")
        klaar_header.wait_for(state="visible")
        logging.info(f"Upload to {url} complete!")
        if close_page:
            logging.info("Closing page (but not browser)")
            page.close()
        if sleep:
            logging.info(f"Sleeping for {sleep} minutes!")
        time.sleep(sleep * 60)
        logging.info(f"Closing browser")
        browser.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Donation File Upload Test Script")

    # Mandatory arguments (positional)
    parser.add_argument("testfile", help="Path to the file you want to upload", type=Path)
    parser.add_argument(
        "url_prefix",
        help="The eyra participant url prefix, e.g. https://next.eyra.co/a/XXXXX?p=test_playwright",
    )

    # Optional arguments (with defaults)
    parser.add_argument("-i", "--iterations", type=int, default=3, help="Number of times to run the test (default: 3)")
    parser.add_argument(
        "-s", "--sleep", type=int, default=0, help="Number of minutes to sleep before closing browser (default: 0)"
    )
    parser.add_argument("--headless", action="store_true", help="Run the browser in headless mode")
    parser.add_argument(
        "-c", "--close-page", action="store_true", help="Close the page (but not the browser) immediately after upload"
    )
    args = parser.parse_args()

    if not args.testfile.exists():
        raise FileNotFoundError(f"Test file {args.testfile} does not exist")

    for i in range(args.iterations):
        url = f"{args.url_prefix}_{i}"
        logging.info(f"**** Running test {i}: {url} ****")
        while True:
            try:
                run_test(url, args.testfile, headless=args.headless, close_page=args.close_page, sleep=args.sleep)
                break
            except Exception as e:
                logging.exception(f"Test {i} failed with exception: {e}, retrying")
