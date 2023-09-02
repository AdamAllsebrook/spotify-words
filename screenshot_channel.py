from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import argparse


def screenshot_youtube_channel(url, path, options=None):
    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, 5)
        driver.get(url)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
        cookies_reject = driver.find_element(
            By.XPATH, "//button[@aria-label='Reject all']")
        cookies_reject.click()
        time.sleep(6)

        driver.save_screenshot(path)
        print(f"Screenshot saved to {path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, required=True)
    parser.add_argument('--path', type=str, required=True)
    args = parser.parse_args()

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=2560,1440')
    options.add_argument("--mute-audio")

    for _ in range(3):
        try:
            screenshot_youtube_channel(args.url, args.path, options=options)
            break
        except Exception:
            print(f'Failed to take screenshot, retrying... ({args.path})')
