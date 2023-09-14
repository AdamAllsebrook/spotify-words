"""Singleton logger for the project."""
import logging
import sys

log = logging.getLogger('spotify-youtube-scraper')
log.setLevel(logging.DEBUG)

# fmt = logging.Formatter(logging.BASIC_FORMAT)
fmt = logging.Formatter(
    '%(levelname)s (%(process)d) [%(asctime)s] %(filename)s:%(lineno)s | %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S %Z")

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(fmt)
log.addHandler(stdout_handler)

file_handler = logging.FileHandler('spotify-youtube-scraper.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(fmt)
log.addHandler(file_handler)
