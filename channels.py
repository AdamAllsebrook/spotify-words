"""Find the YouTube channel for an artist."""
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import argparse
from database import Artist, get_db
from common import options
import logging
import os

dir_path = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler('%s/youtube-scraper-spotify-channels.log'
                            % dir_path),
        logging.StreamHandler(sys.stdout)
    ]
)

log = logging.getLogger(__name__)


def find_all_youtube_channels_with_retries(artist_name, max_retries):
    """
    Find all youtube channels for an artist, retrying if necessary.

    Raises an exception after max_retries.
    """
    for n in range(max_retries):
        log.info('Finding channel for %s, attempt %d',
                 artist_name, n + 1)
        try:
            return find_youtube_channel(artist_name, options=options)
        except Exception as e:
            log.debug('Error finding channel for %s: ', artist_name, e)

    raise Exception('Could not find channel for %s' % artist_name)


def find_youtube_channel(artist_name, options=None):
    """Find the YouTube channel for an artist."""
    SEARCH_URL = 'https://www.youtube.com/results?search_query=%s'
    # selector for right sidebar channel link
    MUSIC_CHANNEL_SELECTOR = '.ytd-secondary-search-container-renderer a'
    # selector for top search result channel link
    CHANNEL_SELECTOR = 'a.channel-link'
    STARTUP_WAIT_TIME = 5

    artist_name = artist_name.replace('&', '%26')
    artist_name += ' music'

    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, STARTUP_WAIT_TIME)
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


def main(db_path, artist_name, spotify_uri, max_retries, overwrite):
    """Find the YouTube channel for an artist and save it to the database."""
    con, cur = get_db(db_path)
    artists = Artist.get_by_spotify(cur, spotify_uri)
    is_in_database = (artists.shape[0] > 0
                      and artists[Artist.YOUTUBE].iloc[0] is not None)
    if is_in_database and not overwrite:
        log.error('%s already has a channel in the database, not overwriting.',
                  artist_name)
        return

    url = find_all_youtube_channels_with_retries(artist_name, max_retries)

    if is_in_database:
        Artist.set_youtube(cur, artists.index[0], url)
        log.info('Updating %s in database (channel: %s)', artist_name, url)
    else:
        Artist.save(cur, artist_name, spotify_uri, url)
        log.info('Creating record for %s to database (channel: %s)',
                 artist_name, url)

    con.commit()
    log.info('Saved %s to database', artist_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', type=str)
    parser.add_argument('--artist-name', type=str)
    parser.add_argument('--spotify-uri', type=str)
    parser.add_argument('--max-retries', type=int, default=3)
    parser.add_argument('--overwrite', action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    main(args.db_path, args.artist_name, args.spotify_uri,
         args.max_retries, args.overwrite)
