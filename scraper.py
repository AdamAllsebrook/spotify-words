from selenium.webdriver.chrome.options import Options
import logging
import argparse
from database import get_db, Artist
from artists import load_artist_csv
from channels import get_all_yt_channels
from videos import get_all_yt_videos, get_yt_videos


if __name__ == '__main__':
    logging.basicConfig(encoding='utf-8', level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('--artist-csv-path', type=str)
    parser.add_argument('--db-path', type=str)
    parser.add_argument(
        '--get-channels', action=argparse.BooleanOptionalAction)
    parser.add_argument('--get-videos', action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    con, cur = get_db(args.db_path)

    # chrome driver options
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=2560,1440')

    if args.get_channels:
        artist_df = load_artist_csv(args.artist_csv_path)
        get_all_yt_channels(con, cur, artist_df,
                            options=options, max_retries=5)

    if args.get_videos:
        artist_to_update_df = Artist.get_by_updated_days_ago(cur, 28)
        get_all_yt_videos(con, cur, artist_to_update_df,
                          options=options, timeout=100)
