
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
import pandas as pd
import argparse
import sys
import time
from database import Video, Comment, get_db
from videos import find_all_in_scrollable
import spacy
from spacy.language import Language
from spacy_language_detection import LanguageDetector


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


def detect_languages(texts):
    def get_lang_detector(nlp, name):
        return LanguageDetector(seed=42)

    nlp_model = spacy.load("en_core_web_sm")
    Language.factory("language_detector", func=get_lang_detector)
    nlp_model.add_pipe('language_detector', last=True)

    languages = [nlp_model(text)._.language['language'] for text in texts]
    return languages


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
                if len(comments) == 0:
                    raise Exception('No comments found')
                break
            except Exception:
                comments = None

        if comments is None:
            print(
                f'Could not find comments for {video[Video.TITLE]}', file=sys.stderr)

        else:
            comments_in_db = Comment.get_by_video(cur, args.video_id)
            languages = detect_languages(comments)
            rows = []
            for (comment, language) in zip(comments, languages):
                if comment not in comments_in_db[Comment.CONTENT].values:
                    rows.append({
                        Comment.VIDEO_ID: args.video_id,
                        Comment.LANGUAGE: language,
                        Comment.CONTENT: comment
                    })

            if len(rows) > 0:
                new_comments_df = pd.DataFrame(
                    rows, columns=[Comment.VIDEO_ID, Comment.CONTENT, Comment.LANGUAGE])
                Comment.save_many(cur, new_comments_df)
                Video.set_updated(cur, args.video_id)
                con.commit()
            print(f'Found {len(rows)} new comments for {video[Video.TITLE]}')
