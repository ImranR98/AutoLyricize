# AutoLyricize

> Automatically find and embed song lyrics.

This script scans a specified directory for audio files, and for each file, finds lyrics from Lyricsify.com or Genius.com (as a fallback), and saves them to the file's metadata.

Perfect for use with [Spotiflyer](https://github.com/Shabinder/SpotiFlyer/) (or [downtify-premium](https://github.com/eviabs/downtify-premium)), [Retro Music Player](https://github.com/RetroMusicPlayer/RetroMusicPlayer), and [Syncthing](https://github.com/syncthing/syncthing) to reduce your dependence on music streaming services.

## Setup

1. Install [Python](https://www.python.org/).
2. Install dependencies by running `pip install -r requirements.txt`.
3. Copy `template.env` to `.env` and add a valid [Genius.com](https://docs.genius.com/) access token to it (or set the appropriate environment variable some other way).
    - If no token is provided, only [Lyricsify.com](https://www.lyricsify.com/) will be used as a data source.

## Usage

Run `python main.py` and provide the path to your music directory as a command line argument. All audio files must be in this directory - nesting is not supported.