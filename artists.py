from database import Artist
import pandas as pd


def load_artist_csv(path):
    df = pd.read_csv(path, index_col=Artist.ID)
    if Artist.YOUTUBE not in df.columns:
        df[Artist.YOUTUBE] = None
    return df
