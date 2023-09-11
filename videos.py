"""Scrape youtube videos for an artist."""
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from database import Artist, Video, get_db
from common import options, find_all_in_scrollable
import argparse
import sys
from dataclasses import dataclass
import logging
import os

dir_path = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler('%s/youtube-scraper-spotify-videos.log'
                            % dir_path),
        logging.StreamHandler(sys.stdout)
    ]
)

log = logging.getLogger(__name__)


@dataclass
class VideoData:
    """Store video data before it is inserted into the database."""

    url: str
    title: str
    views: int


def views_to_int(views):
    """Convert a string of views to an integer."""
    views = views[:views.find(' ')]
    if 'K' in views:
        return int(float(views.replace('K', '')) * 1_000)
    if 'M' in views:
        return int(float(views.replace('M', '')) * 1_000_000)
    if 'B' in views:
        return int(float(views.replace('B', '')) * 1_000_000_000)
    return int(views)


def find_all_youtube_videos_with_retries(artist, max_retries, screenshot_path):
    """
    Find all youtube videos for an artist, retrying if necessary.

    Raises an exception after max_retries.
    """

    for n in range(max_retries):
        log.info('Finding videos for %s, attempt %d',
                 artist[Artist.NAME], n + 1)
        try:
            if screenshot_path is not None:
                screenshot_path += '/%s.png' % artist[Artist.NAME]

            videos = find_youtube_videos(
                artist[Artist.YOUTUBE], screenshot_path, options=options)
            log.info('Found %d videos for %s',
                     len(videos), artist[Artist.NAME])
            urls = [video.url for video in videos]

            music_videos = find_youtube_music_videos(
                artist[Artist.NAME], options=options)
            log.info('Found %d music videos for %s',
                     len(music_videos), artist[Artist.NAME])

            # join two sources of videos
            for video in music_videos:
                if video.url not in urls:
                    videos.append(video)
            log.info('Found %d total videos for %s',
                     len(videos), artist[Artist.NAME])
            return videos

        except Exception as e:
            log.debug('Error finding videos for %s: %s',
                      artist[Artist.NAME], e)

    raise Exception('Could not find videos for %s after %d retries'
                    % (artist[Artist.NAME], max_retries))


def find_youtube_videos(url, screenshot_path=None, options=None):
    """Find youtube videos for a channel."""
    VIDEOS_URL = '%s/videos'
    CHANNEL_NAME = '#channel-name'
    VIDEO_SELECTOR = '#content.ytd-rich-item-renderer'
    ANCHOR_SELECTOR = 'a#thumbnail'
    TITLE_SELECTOR = '#video-title'
    VIEWS_SELECTOR = '#metadata-line span'
    MAX_VIDEOS = 800
    MAX_WAIT_TIME = 10

    videos = []
    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, MAX_WAIT_TIME)
        driver.get(VIDEOS_URL % url)

        cookies_reject = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[@aria-label='Reject all']")))
        cookies_reject.click()

        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, CHANNEL_NAME)))

        if screenshot_path is not None:
            driver.save_screenshot(screenshot_path)

        video_elements = find_all_in_scrollable(
            driver, VIDEO_SELECTOR, MAX_WAIT_TIME, max_elements=MAX_VIDEOS)
        for video_el in video_elements:
            anchor_tag = video_el.find_element(
                By.CSS_SELECTOR, ANCHOR_SELECTOR)
            url = anchor_tag.get_attribute('href')
            title = video_el.find_element(By.CSS_SELECTOR, TITLE_SELECTOR).text

            try:
                views = video_el.find_element(
                    By.CSS_SELECTOR, VIEWS_SELECTOR).text
            except NoSuchElementException:
                # some channels (Maroon 5) have premium video,
                # which don't list the view count
                continue

            video = VideoData(url, title, views_to_int(views))
            videos.append(video)

    return videos


def find_youtube_music_videos(artist_name, options=None):
    """Find videos linked in the artist sidebar when searching for the artist."""
    SEARCH_URL = 'https://www.youtube.com/results?search_query=%s'
    VIDEO_SELECTOR = '''.ytd-two-column-search-results-renderer
    ytd-watch-card-compact-video-renderer.ytd-vertical-watch-card-list-renderer'''
    ANCHOR_SELECTOR = 'a'  # .yt-simple-endpoint'
    TITLE_SELECTOR = '.title'
    VIEWS_SELECTOR = '.subtitle'
    MAX_WAIT_TIME = 10

    videos = []
    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, MAX_WAIT_TIME)
        driver.get(SEARCH_URL % artist_name)

        try:
            video_elements = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, VIDEO_SELECTOR)))
        except TimeoutException:
            return []

        for video_el in video_elements:
            title = video_el.find_element(By.CSS_SELECTOR, TITLE_SELECTOR).text

            anchor_tag = video_el.find_element(
                By.CSS_SELECTOR, ANCHOR_SELECTOR)
            url = anchor_tag.get_attribute('href')
            # remove unnecessary query params
            if '&' in url:
                url = url[:url.find('&')]

            views = video_el.find_element(
                By.CSS_SELECTOR, VIEWS_SELECTOR).text

            video = VideoData(url, title, views_to_int(views))
            videos.append(video)

    return videos


def get_dataframe(artist_id, videos):
    """Convert a list of VideoData objects to a dataframe."""
    rows = [
        {
            Video.ARTIST_ID: artist_id,
            Video.TITLE: video.title,
            Video.YOUTUBE: video.url,
            Video.VIEWS: video.views
        }
        for video in videos
    ]

    return pd.DataFrame(rows, columns=[
        Video.ARTIST_ID, Video.YOUTUBE, Video.TITLE, Video.VIEWS
    ])


def main(db_path, artist_id, max_retries, screenshot_path):
    """Find all youtube videos for an artist and save them to the database."""
    con, cur = get_db(db_path)

    artist = Artist.get_by_id(cur, artist_id)
    if artist is None:
        log.error('ID: %s not found in database', artist_id)
        return

    videos = find_all_youtube_videos_with_retries(
        artist, max_retries, screenshot_path)

    df = get_dataframe(artist_id, videos)
    videos_in_db = Video.get_by_artist(cur, artist_id)
    new_videos_df = df[~df[Video.YOUTUBE].isin(videos_in_db[Video.YOUTUBE])]

    Video.save_many(cur, new_videos_df)
    Artist.set_updated(cur, artist_id)
    con.commit()
    log.info('Saved %d new videos for %s',
             new_videos_df.shape[0], artist[Artist.NAME])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', type=str)
    parser.add_argument('--artist-id', type=str)
    parser.add_argument('--max-retries', type=int, default=3)
    parser.add_argument('--screenshot-path', type=str, default=None)

    args = parser.parse_args()

    main(args.db_path, args.artist_id, args.max_retries, args.screenshot_path)
