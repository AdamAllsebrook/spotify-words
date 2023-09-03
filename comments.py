
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
import pandas as pd
import argparse
import sys
import time
from database import Video, Comment, get_db
from videos import find_all_in_scrollable


def find_youtube_comments(url, max_comments, options=None):
    COMMENT_SELECTOR = '#content-text'
    comments = []
    with Chrome(options=options) as driver:
        driver.get(url)
        time.sleep(5)

        comments = find_all_in_scrollable(
            driver, COMMENT_SELECTOR, 15, max_elements=max_comments)
        comments = [comment.text for comment in comments]

    return comments


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', type=str)
    parser.add_argument('--video-id', type=str)
    parser.add_argument('--max-comments', type=int, default=1000)
    parser.add_argument('--max-retries', type=int, default=3)

    args = parser.parse_args()

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=2560,1440')
    options.add_argument("--mute-audio")

    con, cur = get_db(args.db_path)
    videos = Video.get_by_id(cur, args.video_id)
    if videos.shape[0] == 0:
        print(f'ID: {args.video_id} not found in database', file=sys.stderr)
    else:
        video = videos.iloc[0]
        for n in range(args.max_retries):
            try:
                comments = find_youtube_comments(
                    video[Video.YOUTUBE], args.max_comments, options=options)
                break
            except Exception:
                comments = None

        if comments is None:
            print(
                f'Could not find comments for {video[Video.TITLE]}', file=sys.stderr)

        else:
            comments_in_db = Comment.get_by_video(cur, args.video_id)
            rows = []
            for comment in comments:
                if comment not in comments_in_db[Comment.CONTENT].values:
                    rows.append({
                        Comment.VIDEO_ID: args.video_id,
                        Comment.CONTENT: comment
                    })

            new_comments_df = pd.DataFrame(
                rows, columns=[Comment.VIDEO_ID, Comment.CONTENT])
            Comment.save_many(cur, new_comments_df)
            Video.set_updated(cur, args.video_id)
            con.commit()
            print(f'Found {len(rows)} new comments for {video[Video.TITLE]}')
