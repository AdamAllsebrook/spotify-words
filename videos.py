from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from database import Artist, Video, get_db
import argparse
import sys


def find_youtube_videos(url, options=None):
    VIDEOS_URL = '%s/videos'
    VIDEO_SELECTOR = '#content.ytd-rich-item-renderer'
    ANCHOR_SELECTOR = 'a#thumbnail'
    TITLE_SELECTOR = '#video-title'
    video_urls = []
    video_titles = []
    with Chrome(options=options) as driver:
        wait = WebDriverWait(driver, 3)
        driver.get(VIDEOS_URL % url)

        cookies_reject = driver.find_element(
            By.XPATH, "//button[@aria-label='Reject all']")
        cookies_reject.click()
        time.sleep(5)

        last_videos_len = None
        while len(video_urls) != last_videos_len:
            last_videos_len = len(video_urls)
            wait.until(EC.presence_of_element_located(
                (By.TAG_NAME, 'body'))).send_keys(Keys.END)

            for video in driver.find_elements(By.CSS_SELECTOR, VIDEO_SELECTOR):
                anchor_tag = video.find_element(
                    By.CSS_SELECTOR, ANCHOR_SELECTOR)
                link = anchor_tag.get_attribute('href')
                if link not in video_urls:
                    video_urls.append(link)

                    title = video.find_element(
                        By.CSS_SELECTOR, TITLE_SELECTOR).text
                    video_titles.append(title)

            time.sleep(1)

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
                break
            except Exception:
                videos = None

        if videos is None:
            print(
                f'Could not find videos for {args.youtube_url}', file=sys.stderr)

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
