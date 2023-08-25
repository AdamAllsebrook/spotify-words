from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from concurrent import futures
import time
import logging
from tqdm import tqdm
from database import Artist, Video


def get_yt_videos(url, options=None):
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


def get_all_yt_videos(con, cur, artist_df, timeout=60, options=None, max_workers=5):
    logging.info('Starting get youtube videos')
    with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        all_future_videos = [(
            index,
            row[Artist.YOUTUBE],
            executor.submit(get_yt_videos, row[Artist.YOUTUBE], options))
            for (index, row) in artist_df.iterrows()
        ]

        for (artist_id, channel_url, future_videos) in tqdm(all_future_videos):
            try:
                videos = future_videos.result(timeout=timeout)
                videos_in_db = Video.get_by_artist(cur, artist_id)

                rows = []
                for (video_url, video_title) in videos:
                    if video_url not in videos_in_db[Video.YOUTUBE].values:
                        rows.append({
                            Video.ARTIST_ID: artist_id,
                            Video.TITLE: video_title,
                            Video.YOUTUBE: video_url
                        })

                new_videos_df = pd.DataFrame(
                    rows, columns=[Video.ARTIST_ID, Video.YOUTUBE, Video.TITLE])
                Video.save_many(cur, new_videos_df)
                Artist.set_updated(cur, artist_id)
                con.commit()

            except Exception:
                logging.warning(
                    f'Something went wrong getting videos for {channel_url}')
