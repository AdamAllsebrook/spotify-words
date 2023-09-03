from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
from database import Artist, Video, get_db
import argparse
import sys


# find all elements matching selector in a scrollable page
def find_all_in_scrollable(driver, selector, max_wait_time, max_elements=None):
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


def find_youtube_videos(url, options=None):
    VIDEOS_URL = '%s/videos'
    VIDEO_SELECTOR = '#content.ytd-rich-item-renderer'
    ANCHOR_SELECTOR = 'a#thumbnail'
    TITLE_SELECTOR = '#video-title'
    video_urls = []
    video_titles = []
    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, 5)
        driver.get(VIDEOS_URL % url)

        cookies_reject = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[@aria-label='Reject all']")))
        cookies_reject.click()
        time.sleep(3)

        videos = find_all_in_scrollable(driver, VIDEO_SELECTOR, 3)
        for video in videos:
            anchor_tag = video.find_element(By.CSS_SELECTOR, ANCHOR_SELECTOR)
            url = anchor_tag.get_attribute('href')
            title = video.find_element(By.CSS_SELECTOR, TITLE_SELECTOR).text

            video_urls.append(url)
            video_titles.append(title)

    return list(zip(video_urls, video_titles))


# find videos linked in the artist sidebar when searching for the artist
# in future can extend this to include playlists linked here
def find_youtube_music_videos(artist_name, options=None):
    SEARCH_URL = 'https://www.youtube.com/results?search_query=%s'
    VIDEO_SELECTOR = '''.ytd-two-column-search-results-renderer
ytd-watch-card-compact-video-renderer.ytd-vertical-watch-card-list-renderer'''
    ANCHOR_SELECTOR = 'a'  # .yt-simple-endpoint'
    TITLE_SELECTOR = '.title'

    video_urls = []
    video_titles = []
    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, 5)
        driver.get(SEARCH_URL % artist_name)

        try:
            videos = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, VIDEO_SELECTOR)))
        except TimeoutException:
            return []

        for video in videos:
            title = video.find_element(By.CSS_SELECTOR, TITLE_SELECTOR).text
            anchor_tag = video.find_element(By.CSS_SELECTOR, ANCHOR_SELECTOR)
            url = anchor_tag.get_attribute('href')
            # remove unnecessary query params
            if '&' in url:
                url = url[:url.find('&')]

            video_urls.append(url)
            video_titles.append(title)

    return list(zip(video_urls, video_titles))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', type=str)
    parser.add_argument('--artist-id', type=str)
    parser.add_argument('--max-retries', type=int, default=3)

    args = parser.parse_args()

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=2560,1440')

    con, cur = get_db(args.db_path)
    artists = Artist.get_by_id(cur, args.artist_id)
    if artists.shape[0] == 0:
        print(f'ID: {args.artist_id} not found in database', file=sys.stderr)
    else:
        artist = artists.iloc[0]
        for n in range(args.max_retries):
            try:
                videos = find_youtube_videos(
                    artist[Artist.YOUTUBE], options=options)
                urls = [url for (url, title) in videos]

                music_videos = find_youtube_music_videos(
                    artist[Artist.NAME], options=options)

                # join two sources of videos
                for (url, title) in music_videos:
                    if url not in urls:
                        videos.append((url, title))
                break
            except Exception:
                videos = None

        if videos is None:
            print(
                f'Could not find videos for {artist[Artist.NAME]}', file=sys.stderr)

        else:
            videos_in_db = Video.get_by_artist(cur, args.artist_id)
            rows = []
            for (video_url, video_title) in videos:
                if video_url not in videos_in_db[Video.YOUTUBE].values:
                    rows.append({
                        Video.ARTIST_ID: args.artist_id,
                        Video.TITLE: video_title,
                        Video.YOUTUBE: video_url
                    })

            new_videos_df = pd.DataFrame(
                rows, columns=[Video.ARTIST_ID, Video.YOUTUBE, Video.TITLE])
            Video.save_many(cur, new_videos_df)
            Artist.set_updated(cur, args.artist_id)
            con.commit()
            print(f'Found {len(rows)} new videos for {artist[Artist.NAME]}')
