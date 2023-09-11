# Spotify YouTube Scraper

Scripts to scrape youtube comments for spotify artists

## Setup

- Install venv if it is not already installed  
https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#installing-virtualenv

- Use venv to create a virtual environment  
```bash
python3 -m venv env
```

- Activate venv  
```bash
source env/bin/activate
```

- Install requirements  
```bash
pip install -r requirements.txt
```

## CLI commands

### Get youtube channels for spotify artists
Start with a csv of spotify artists' names and URIs  
`spotify_artist_uris.csv` is a combination of these two datasets: https://www.kaggle.com/datasets/adnananam/spotify-artist-stats and https://www.kaggle.com/datasets/ehcall/spotify-artists  

```bash
cat spotify_artist_uris.csv | parallel --jobs 4 --colsep , python channels.py --db-path=datasets/db.sqlite --artist-name={2} --spotify-uri={3}
```

### Get videos for the youtube channels
Get all videos for all artists in the db  
Also save a screenshot of every channel for validation, these are not guaranteed to be correct as it is using youtube's search function  

```bash
sqlite3 datasets/db.sqlite "select id from artist where updated_at < datetime('now', '-28 day')" | parallel --jobs 4 --colsep , python videos.py --db-path=datasets/db.sqlite --artist-id={1} --screenshot-path=./screenshots
```

### Get comments for the top ten most viewed videos for each channel
```bash
sqlite3 datasets/db.sqlite "WITH RankedVideos AS ( SELECT v.id as video_id, v.updated_at as updated_at, ROW_NUMBER() OVER(PARTITION BY a.id ORDER BY v.views DESC) AS row_num FROM artist a JOIN video v ON a.id = v.artist_id) SELECT video_id FROM RankedVideos WHERE row_num <= 10 and updated_at < DATETIME('now', '-28 days')" | parallel --jobs 4 --colsep , python comments.py --db-path=datasets/db.sqlite --video-id={1} --max-comments=250
```

The same SQL query is copied for readability:
```sql
WITH RankedVideos AS (
  SELECT
    v.id as video_id,
    v.updated_at as updated_at,
    ROW_NUMBER() OVER(PARTITION BY a.id ORDER BY v.views DESC) AS row_num
  FROM artist a
  JOIN video v ON a.id = v.artist_id
)
SELECT video_id
FROM RankedVideos
WHERE row_num <= 10 and updated_at < DATETIME('now', '-28 days')
```

## Testing
```bash
python test.py
```
