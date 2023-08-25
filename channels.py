
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent import futures
from tqdm import tqdm
import logging
from database import Artist


def get_yt_channel(artist_name, options=None):
    SEARCH_URL = 'https://www.youtube.com/results?search_query=%s'
    ANCHOR_SELECTOR = 'a.channel-link, .ytd-secondary-search-container-renderer a'

    artist_name = artist_name.replace('&', '%26')
    artist_name += ' music'

    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, 5)
        driver.get(SEARCH_URL % artist_name)

        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ANCHOR_SELECTOR)))
        anchor_tag = driver.find_element(By.CSS_SELECTOR, ANCHOR_SELECTOR)
        return anchor_tag.get_attribute('href')


def get_all_yt_channels(con, cur, artist_df, timeout=20, options=None, max_retries=3, max_workers=5):
    def try_get_all_yt_channels():
        artists_in_db = Artist.get_all(cur)
        with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_urls = []
            for index, row in artist_df.iterrows():
                if row[Artist.NAME] in artists_in_db[Artist.NAME].values:
                    continue
                future_urls.append((
                    index,
                    executor.submit(get_yt_channel, row[Artist.NAME], options)
                ))

            n_exceptions = 0
            for (index, future_url) in tqdm(future_urls):
                try:
                    url = future_url.result(timeout=timeout)
                    row = artist_df.loc[index]
                    Artist.save(cur, row[Artist.NAME],
                                row[Artist.SPOTIFY], url)
                    con.commit()
                except Exception:
                    n_exceptions += 1
                    logging.debug(f'Exception for {index}')

        return len(future_urls) - n_exceptions, n_exceptions

    logging.info('Starting match spotify artists to youtube channels')
    completed = False
    retries = 0
    while not completed and retries < max_retries:
        if retries != 0:
            logging.info(f'Retrying attempt: {retries + 1}/{max_retries}')
        success, fail = try_get_all_yt_channels()
        completed = fail == 0
        retries += 1
        logging.info(f'Found channels for {success} artists, {fail} failures')
