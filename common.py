"""Common functions for all scrapers."""
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=2560,1440')
options.add_argument('--mute-audio')
options.add_argument('--disable-gpu')


def find_all_in_scrollable(driver, selector, max_wait_time, max_elements=None):
    """Find all elements matching selector in a scrollable page."""
    last_len = None
    last_different_len_time = time.time()
    while True:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if max_elements is not None and len(elements) >= max_elements:
            break
        if len(elements) == last_len:
            if time.time() - last_different_len_time > max_wait_time:
                break
        else:
            last_different_len_time = time.time()
        last_len = len(elements)

        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(0.1)
    return elements
