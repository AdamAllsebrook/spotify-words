"""
Tests.

`python test.py`
"""
import os
from database import get_db

con, cur = get_db('test.db')


def test():
    os.system('python channels.py \
                --db-path=test.db \
                --artist-name=Drake \
                --spotify-uri=spotify:artist:3TVXtAsR1Inumwj472S9r4')

    cur.execute('select * from artist')
    artists = cur.fetchall()
    assert len(artists) == 1
    print('Found channel successfully.')

    os.system('python videos.py \
              --db-path=test.db \
              --artist-id=1')

    cur.execute('select * from video')
    videos = cur.fetchall()
    assert len(videos) > 0
    print('Found videos successfully.')

    os.system('python comments.py \
              --db-path=test.db \
              --video-id=1 \
              --max-comments=10')

    cur.execute('select * from comment')
    comments = cur.fetchall()
    assert len(comments) >= 10
    print('Found comments successfully.')


if __name__ == '__main__':
    try:
        test()
        print('All tests passed.')
    finally:
        con.close()
        os.remove('test.db')
