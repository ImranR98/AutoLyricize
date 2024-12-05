# AutoLyricize

> Automatically find and embed song lyrics.

This script scans a specified directory for audio files, and for each file, finds lyrics from Lyricsify.com or Genius.com (as a fallback), and saves them to the file's metadata.

Perfect for use with [Spotiflyer](https://github.com/Shabinder/SpotiFlyer/), [Retro Music Player](https://github.com/RetroMusicPlayer/RetroMusicPlayer), and [Syncthing](https://github.com/syncthing/syncthing) to reduce your dependence on music streaming services.

## Setup

1. Install [Python](https://www.python.org/).
2. Install dependencies by running `pip install -r requirements.txt`.
3. Copy `template.env` to a new file called `.env` and add a valid [Genius.com](https://docs.genius.com/) access token to it (or set the appropriate environment variable some other way).
    - If no token is provided, only [Lyricsify.com](https://www.lyricsify.com/) will be used as a data source.
4. Also add a browser user-agent under the HEADER variable. You can get your very own [here](https://whatmyuseragent.com/) - it's the field at the top.

## Usage

Run `python main.py "path/to/folder"`.
*useful tip for noobs: you can drag a folder into the terminal window to paste its full path* 👍

## Limitations

- Inexact search uses Genius's search system, which loves to give you results that have absolutely nothing to do with the original track. If you use inexact search with instrumental tracks or albums, you are going to get garbage data.
- Only works with mp3 files due to a limitation in the eyed3 library.
