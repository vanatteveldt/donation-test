import argparse
import logging
import time
from pathlib import Path

from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright


def run_test(url: str, file: Path):
    with sync_playwright() as p:

        browser = p.firefox.launch(headless=False)
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
        btn.wait_for(state="visible")
        btn.click()

        btn = page.get_by_text("Doorgaan", exact=True)
        btn.wait_for(state="visible")
        btn.click()
        logging.info("Waiting for file uploader to load")

        # 3. File Upload Procedure
        # This is inside an iframe, so open that first and then upload the file
        target_frame = page.frame_locator('iframe[src*="amazonaws.com"]')
        with page.expect_file_chooser() as fc_info:
            target_frame.get_by_text("Kies bestand").click()
        fc_info.value.set_files(file)
        logging.info("Uploading file {file}")
        target_frame.get_by_text("Verder", exact=True).click()

        # 4. Give consent
        target_frame = page.frame_locator('iframe[src*="amazonaws.com"]')
        confirm_btn = target_frame.locator("#confirm-button").filter(has_text="Ja, deel voor onderzoek")
        logging.info("Waiting for upload to complete and consent button to appear...")
        confirm_btn.wait_for(state="visible", timeout=120000)
        confirm_btn.scroll_into_view_if_needed()
        logging.info("Confirming upload")
        confirm_btn.click()

        # 5. We're done, but let's click the buttons to finish the process
        finish_btn = page.locator("div.prism-btn").filter(has_text="Volgende, ik ben klaar")
        finish_btn.click()

        final_doorgaan = page.locator("div.prism-btn").filter(has_text="Doorgaan")
        final_doorgaan.click()
        logging.info("Clicked final 'Doorgaan'. Waiting for redirect...")

        # 6. Wait for the redirect to the final URL and close the browser
        # This ensures the test doesn't close until the target site actually loads
        page.wait_for_url("https://what-if-horizon.eu/**", timeout=15000)

        logging.info(f"Upload {id}:{url} complete, closing browser!")
        browser.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser(description="Donation File Upload Test Script")

    # Mandatory arguments (positional)
    parser.add_argument("testfile", help="Path to the file you want to upload", type=Path)
    parser.add_argument("task", help="The task ID for the test, e.g. H35Ghq")

    # Optional arguments (with defaults)
    parser.add_argument("-i", "--iterations", type=int, default=10, help="Number of times to run the test (default: 10)")
    parser.add_argument(
        "-p", "--id_prefix", default="test_playwright", help="Prefix for the URL parameter (default: test_playwright)"
    )

    args = parser.parse_args()
    if not args.testfile.exists():
        raise FileNotFoundError(f"Test file {args.testfile} does not exist")

    for i in range(args.iterations):
        url = f"https://next.eyra.co/a/{args.task}?p={args.id_prefix}_{i}"
        logging.info(f"**** Running test {i}: {url} ****")
        try:
            run_test(url, args.testfile)
        except Exception as e:
            logging.exception(f"Test {i} failed with exception: {e}, continuing")
