from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import argparse
from database import Artist, get_db


def find_youtube_channel(artist_name, options=None):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', type=str)
    parser.add_argument('--artist-name', type=str)
    parser.add_argument('--spotify-uri', type=str)
    parser.add_argument('--max-retries', type=int, default=3)

    args = parser.parse_args()

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=2560,1440')

    con, cur = get_db(args.db_path)
    artists = Artist.get_by_spotify(cur, args.spotify_uri)
    if artists.shape[0] > 0 and artists[Artist.YOUTUBE].iloc[0] is not None:
        print(f'{args.artist_name} already in database')
    else:
        for n in range(args.max_retries):
            try:
                url = find_youtube_channel(args.artist_name, options=options)
                break
            except Exception:
                url = None

        if url is None:
            print(
                f'Could not find channel for {args.artist_name}', file=sys.stderr)
        else:
            Artist.save(cur, args.artist_name, args.spotify_uri, url)
            con.commit()
            print(f'Found channel for {args.artist_name}: {url}')
