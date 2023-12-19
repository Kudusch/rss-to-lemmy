# RSS to Lemmy

This Python script checks the RSS feeds for [The Greatest Generation](https://maximumfun.org/podcasts/greatest-generation/) and [Greatest Trek](https://maximumfun.org/podcasts/greatest-trek/) and posts new episodes to Lemmy.

## Installation

`virtualenv -p python3 venv`
`source venv/bin/activate`
`pip install -r requirements.txt`

Edit `example_config.ini` with the posting user's credentials and rename the file to `config.ini`.

## Usage

`python3 check_feeds.py`
