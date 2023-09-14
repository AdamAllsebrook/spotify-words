"""Methods for interacting with the database."""
import pandas as pd
import sqlite3
from logger import log


def generate_schema():
    """Generate the SQL schema for the database."""
    return f'''
CREATE TABLE IF NOT EXISTS artist (
    {Artist.ID} INTEGER PRIMARY KEY,
    {Artist.NAME} TEXT NOT NULL,
    {Artist.SPOTIFY} TEXT NOT NULL,
    {Artist.YOUTUBE} TEXT NOT NULL,
    {Artist.UPDATED} TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS video (
    {Video.ID} INTEGER PRIMARY KEY,
    {Video.ARTIST_ID} INTEGER NOT NULL,
    {Video.TITLE} TEXT NOT NULL,
    {Video.YOUTUBE} TEXT NOT NULL,
    {Video.VIEWS} BIGINT NOT NULL,
    {Video.UPDATED} TEXT NOT NULL,
    FOREIGN KEY ({Video.ARTIST_ID}) REFERENCES artist ({Artist.ID})
);

CREATE TABLE IF NOT EXISTS comment (
    {Comment.ID} INTEGER PRIMARY KEY,
    {Comment.VIDEO_ID} INTEGER NOT NULL,
    {Comment.CONTENT} TEXT NOT NULL,
    {Comment.LANGUAGE} TEXT NOT NULL,
    {Comment.UPDATED} TEXT NOT NULL,
    FOREIGN KEY ({Comment.VIDEO_ID}) REFERENCES video ({Video.ID})
);
'''


def get_db(db_path):
    """Get a connection to the database, creating it if necessary."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    schema = generate_schema()
    cur.executescript(schema)
    con.commit()
    log.debug('Connected to database at %s', db_path)
    return con, cur


class Artist:
    """Methods for interacting with the artist table."""

    ID = 'id'
    NAME = 'name'
    SPOTIFY = 'spotify_uri'
    YOUTUBE = 'youtube_url'
    UPDATED = 'updated_at'

    def sql_result_to_df(db_items):
        """Convert a SQL result to a pandas DataFrame."""
        df = pd.DataFrame(db_items, columns=[
            Artist.ID,
            Artist.NAME,
            Artist.SPOTIFY,
            Artist.YOUTUBE,
            Artist.UPDATED
        ])
        df.set_index(Artist.ID, inplace=True)
        return df

    def get_all(cur):
        """Get all artists from the database."""
        cur.execute(' SELECT * FROM artist')
        return Artist.sql_result_to_df(cur.fetchall())

    def get_by_id(cur, artist_id):
        """Get an artist by their ID."""
        cur.execute(
            f'SELECT * FROM artist WHERE {Artist.ID} = ?', (artist_id,))
        artists = Artist.sql_result_to_df(cur.fetchall())
        if artists.shape[0] == 0:
            log.debug('No artist found with id:%s', artist_id)
            return None
        return artists.iloc[0]

    def get_by_spotify(cur, spotify_uri):
        """Get artists by their Spotify URI."""
        cur.execute(
            f'SELECT * FROM artist WHERE {Artist.SPOTIFY} = ?',
            (spotify_uri,))

        return Artist.sql_result_to_df(cur.fetchall())

    def get_by_youtube(cur, youtube_channel):
        """Get artists by their YouTube channel."""
        cur.execute(
            f'SELECT * FROM artist WHERE {Artist.YOUTUBE} = ?',
            (youtube_channel,))
        return Artist.sql_result_to_df(cur.fetchall())

    def save(cur, name, spotify_uri, youtube_url):
        """Save an artist to the database."""
        cur.execute(
            f'''INSERT INTO artist (
                {Artist.NAME},
                {Artist.SPOTIFY},
                {Artist.YOUTUBE},
                {Artist.UPDATED})
            VALUES (?, ?, ?, datetime('2001-01-01'))''',
            (name, spotify_uri, youtube_url)
        )
        log.debug('Saved artist %s, %s, %s', name, spotify_uri, youtube_url)

    def set_youtube(cur, artist_id, youtube_url):
        """Set the YouTube channel for an artist."""
        # i couldn't get passing args in a tuple to work, idk why
        cur.execute(
            f'''UPDATE artist
               SET {Artist.YOUTUBE} = "{youtube_url}"
               WHERE id = {artist_id}'''
        )
        log.debug('Set YouTube channel for artist id:%s to %s',
                  artist_id, youtube_url)

    def set_updated(cur, artist_id):
        """Set the updated_at field for an artist."""
        cur.execute(
            f'''UPDATE artist
               SET {Artist.UPDATED} = datetime('now')
               WHERE id = ?''',
            (artist_id,)
        )
        log.debug('Set updated_at for artist id:%s to now', artist_id)


class Video:
    """Methods for interacting with the video table."""

    ID = 'id'
    ARTIST_ID = 'artist_id'
    TITLE = 'title'
    YOUTUBE = 'youtube_url'
    VIEWS = 'views'
    UPDATED = 'updated_at'

    def sql_result_to_df(db_items):
        """Convert a SQL result to a pandas DataFrame."""
        df = pd.DataFrame(db_items, columns=[
            Video.ID,
            Video.ARTIST_ID,
            Video.TITLE,
            Video.YOUTUBE,
            Video.VIEWS,
            Video.UPDATED
        ])
        df.set_index(Video.ID, inplace=True)
        return df

    def get_by_id(cur, video_id):
        """Get a video by its ID."""
        cur.execute(
            f'SELECT * FROM video WHERE {Video.ID} = ?', (video_id,))
        videos = Video.sql_result_to_df(cur.fetchall())
        if videos.shape[0] == 0:
            return None
        return videos.iloc[0]

    def get_by_artist(cur, artist_id):
        """Get videos by their artist."""
        cur.execute(f'''
    SELECT * FROM video
    WHERE {Video.ARTIST_ID} = ?''',
                    (artist_id,))
        return Video.sql_result_to_df(cur.fetchall())

    def save_many(cur, videos_df):
        """Save many videos to the database."""
        cur.executemany(
            f'''INSERT INTO video (
                {Video.ARTIST_ID},
                {Video.TITLE},
                {Video.YOUTUBE},
                {Video.VIEWS},
                {Video.UPDATED})
            VALUES (?, ?, ?, ?, datetime('2001-01-01'))''',
            videos_df[[Video.ARTIST_ID, Video.TITLE,
                       Video.YOUTUBE, Video.VIEWS]].itertuples(index=False)
        )
        log.debug('Saved %s videos', videos_df.shape[0])

    def set_updated(cur, video_id):
        """Set the updated_at field for a video."""
        cur.execute(
            f'''UPDATE video
               SET {Video.UPDATED} = datetime('now')
               WHERE id = ?''',
            (video_id,)
        )
        log.debug('Set updated_at for video id:%s to now', video_id)


class Comment:
    """Methods for interacting with the comment table."""

    ID = 'id'
    VIDEO_ID = 'video_id'
    CONTENT = 'content'
    LANGUAGE = 'language'
    UPDATED = 'updated_at'

    def sql_result_to_df(db_items):
        """Convert a SQL result to a pandas DataFrame."""
        df = pd.DataFrame(db_items, columns=[
            Comment.ID,
            Comment.VIDEO_ID,
            Comment.CONTENT,
            Comment.LANGUAGE,
            Comment.UPDATED
        ])
        df.set_index(Comment.ID, inplace=True)
        return df

    def get_all(cur):
        """Get all comments from the database."""
        cur.execute('SELECT * FROM comment')
        return Comment.sql_result_to_df(cur.fetchall())

    def get_by_artist(cur, artist_id):
        """Get comments by their artist."""
        cur.execute(f'''SELECT
                    comment.{Comment.ID},
                    {Comment.VIDEO_ID},
                    {Comment.CONTENT},
                    {Comment.LANGUAGE},
                    comment.{Comment.UPDATED} FROM comment
                    LEFT JOIN video ON
                        comment.{Comment.VIDEO_ID} = video.{Video.ID}
                    WHERE video.{Video.ARTIST_ID} = ? LIMIT 1000''',
                    (artist_id,))
        return Comment.sql_result_to_df(cur.fetchall())

    def get_by_video(cur, video_id):
        """Get comments by their video."""
        cur.execute(f''' SELECT * FROM comment WHERE {Comment.VIDEO_ID} = ?''',
                    (video_id,))
        return Comment.sql_result_to_df(cur.fetchall())

    def save_many(cur, comments_df):
        """Save many comments to the database."""
        cur.executemany(
            f'''INSERT INTO comment (
                {Comment.VIDEO_ID},
                {Comment.CONTENT},
                {Comment.LANGUAGE},
                {Comment.UPDATED})
            VALUES (?, ?, ?, datetime('2001-01-01'))''',
            comments_df[[Comment.VIDEO_ID, Comment.CONTENT, Comment.LANGUAGE]
                        ].itertuples(index=False)
        )
        log.debug('Saved %s comments', comments_df.shape[0])
