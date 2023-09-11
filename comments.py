"""Scrape youtube comments given a video id."""
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
import pandas as pd
import argparse
import sys
import time
from database import Video, Comment, get_db
import spacy
from spacy.language import Language
from spacy_language_detection import LanguageDetector
from common import options, find_all_in_scrollable


def find_youtube_comments_with_retries(url, max_comments, max_retries):
    """
    Find youtube comments for a video, retrying if necessary.

    Raises an exception after max_retries.
    """
    for n in range(max_retries):
        try:
            return find_youtube_comments(
                url,
                max_comments,
                options=options
            )
        except Exception:
            pass

    raise Exception('Could not find comments for %s after %d retries'
                    % (url, max_retries))


def find_youtube_comments(url, max_comments, options=None):
    """
    Find youtube comments for a video.

    Raises an exception if no comments are found, unless the video is
    specified as have 0 comments, or comments are turned off.
    """
    COMMENT_SELECTOR = '#content-text'
    STARTUP_WAIT_TIME = 5
    MAX_WAIT_TIME = 30

    comments = []
    with Chrome(options=options) as driver:
        driver.get(url)
        time.sleep(STARTUP_WAIT_TIME)

        comments = find_all_in_scrollable(
            driver, COMMENT_SELECTOR, MAX_WAIT_TIME, max_elements=max_comments)
        comments = [comment.text for comment in comments]

        if len(comments) == 0:
            body = driver.find_element(By.TAG_NAME, 'body')
            if 'Comments are turned off.' in body.text:
                return []
            if '\n0 Comments' in body.text:
                return []
            raise Exception(
                'Video URL %s has no comments, but was expected to have some'
                % url)

    return comments


@Language.factory('language_detector')
def get_lang_detector(nlp, name):
    """Language detector factory."""
    return LanguageDetector(seed=42)


def detect_languages(texts):
    """Detect languages for a list of texts using spacy."""
    nlp_model = spacy.load('en_core_web_sm')
    nlp_model.add_pipe('language_detector', last=True)

    languages = [nlp_model(text)._.language['language'] for text in texts]
    return languages


def create_dataframe(video_id, comments, languages):
    """Create a dataframe for a list of comments."""
    rows = [
        {
            Comment.VIDEO_ID: video_id,
            Comment.LANGUAGE: language,
            Comment.CONTENT: comment
        }
        for (comment, language) in zip(comments, languages)
    ]

    return pd.DataFrame(
        rows, columns=[Comment.VIDEO_ID, Comment.CONTENT, Comment.LANGUAGE])


def main(db_path, video_id, max_comments, max_retries):
    """Scrape youtube comments for a video and save them to the database."""
    con, cur = get_db(db_path)

    video = Video.get_by_id(cur, video_id)
    if video is None:
        print(f'ID: {video_id} not found in database', file=sys.stderr)
        return

    comments = find_youtube_comments_with_retries(
        video[Video.YOUTUBE], max_comments, max_retries)
    languages = detect_languages(comments)

    df = create_dataframe(video_id, comments, languages)
    comments_in_db = Comment.get_by_video(cur, video_id)
    new_comments_df = df[~df[Comment.CONTENT].isin(comments_in_db)]

    Comment.save_many(cur, new_comments_df)
    Video.set_updated(cur, video_id)
    con.commit()
    print('Found %d new comments for %s'
          % (len(new_comments_df), video[Video.TITLE]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', type=str)
    parser.add_argument('--video-id', type=str)
    parser.add_argument('--max-comments', type=int, default=1000)
    parser.add_argument('--max-retries', type=int, default=3)

    args = parser.parse_args()

    main(args.db_path, args.video_id, args.max_comments, args.max_retries)
