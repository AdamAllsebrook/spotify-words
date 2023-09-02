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
    # selector for right sidebar channel link
    MUSIC_CHANNEL_SELECTOR = '.ytd-secondary-search-container-renderer a'
    # selector for top search result channel link
    CHANNEL_SELECTOR = 'a.channel-link'

    artist_name = artist_name.replace('&', '%26')
    artist_name += ' music'

    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, 5)
        driver.get(SEARCH_URL % artist_name)

        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR,
             ','.join([CHANNEL_SELECTOR, MUSIC_CHANNEL_SELECTOR]))
        ))

        music_channel_anchor = driver.find_element(
            By.CSS_SELECTOR, MUSIC_CHANNEL_SELECTOR)
        if music_channel_anchor is not None:
            return music_channel_anchor.get_attribute('href')

        channel_anchor = driver.find_element(By.CSS_SELECTOR, CHANNEL_SELECTOR)
        return channel_anchor.get_attribute('href')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', type=str)
    parser.add_argument('--artist-name', type=str)
    parser.add_argument('--spotify-uri', type=str)
    parser.add_argument('--max-retries', type=int, default=3)
    parser.add_argument('--overwrite', action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=2560,1440')

    con, cur = get_db(args.db_path)
    artists = Artist.get_by_spotify(cur, args.spotify_uri)
    is_in_database = (artists.shape[0] > 0
                      and artists[Artist.YOUTUBE].iloc[0] is not None)
    if is_in_database and not args.overwrite:
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
            if is_in_database:
                Artist.set_youtube(cur, artists.index[0], url)
            else:
                Artist.save(cur, args.artist_name, args.spotify_uri, url)
            con.commit()
            print(f'Found channel for {args.artist_name}: {url}')
