"""
This script scans a specified directory for audio files, and for each file, 
finds lyrics from Lyricsify.com or Genius.com (as a fallback), 
and saves them to the file's metadata.
"""

import sys
import urllib
import json
from bs4 import BeautifulSoup
import requests
import os
import re
import eyed3
from dotenv import load_dotenv
load_dotenv()


def lyricsify_find_song_lyrics(query):
    """
    Return song lyrics from Lyricsify.com for the first song found using the provided search string.
    If not found, return None.
    """
    # Search Lyricsify for the song using web scraping
    link = BeautifulSoup(
        requests.get(url="https://www.lyricsify.com/search?q=" +
                     query.replace(
                         " - ", "+").replace(" ", "+"),
                     headers={
                         "User-Agent": ""
                     }).text,
        "html.parser").find("a", class_="title")
    # If not found, return None
    if link is None:
        return None
    # Scrape the song URL for the lyrics text
    song_html = BeautifulSoup(
        requests.get(url="https://www.lyricsify.com" + link.attrs['href'],
                     headers={
            "User-Agent": ""
        }).text,
        "html.parser")
    # If the artist or song name does not exist in the query, return None
    artist_title = song_html.find("h1").string[:-7]
    sep_ind = artist_title.find("-")
    artist = None if sep_ind < 0 else artist_title[0:sep_ind].strip()
    title = artist_title if sep_ind < 0 else artist_title[sep_ind + 1:].strip()
    query_lower = query.lower()
    if query_lower.find(title.lower()) < 0 or (sep_ind >= 0 and query_lower.find(artist.lower()) < 0):
        return None
    # Return the lyrics text
    return "".join(song_html.find("div", id="entry").strings)


def genius_find_song_lyrics(query, access_token):
    """
    Return song lyrics from Genius.com for the first song found using the provided search string.
    If not found, return None.
    Requires a Genius.com access token.
    """
    # Search Genius for the song using their API
    results = json.loads(requests.get(url="https://api.genius.com/search?q=" + urllib.parse.quote(query), headers={
        "Authorization": "Bearer " + access_token,
        "User-Agent": ""
    }).text)
    # If no hits, return None
    if len(results["response"]["hits"]) <= 0:
        return None
    # If the song has no URL or the artist or song name does not exist in the query, return None
    song = results["response"]["hits"][0]["result"]
    query_lower = query.lower()
    if song["url"] is None or query_lower.find(song["title"].lower()) < 0 or query_lower.find(song["primary_artist"]["name"].lower()) < 0:
        return None
    # Scrape the song URL for the lyrics text
    page = requests.get(song["url"])
    html = BeautifulSoup(page.text, "html.parser")
    target_div = html.find("div", id="lyrics-root")
    # This ususally means the song is an instrumental (exists on the site and was found, but no lyrics)
    if target_div is None:
        lyrics = ["[Instrumental]"]
    else:
        lyrics = "\n".join(
            html.find("div", id="lyrics-root").strings).split("\n")[1:-2]
    # The extracted lyrics text is mangled, needs some processing before it is returned...
    indices = []
    for i, lyric in enumerate(lyrics):
        if lyric[0] == "[":
            indices.append(i)
    inserted = 0
    for i in indices:
        lyrics.insert(i+inserted, "")
        inserted += 1
    final_lyrics = []
    for i, lyric in enumerate(lyrics):
        if (i < (len(lyrics) - 1) and (lyrics[i+1] == ")" or lyrics[i+1] == "]")) or lyric == ")" or lyric == "]" or (i > 0 and lyrics[i-1].endswith(" ") or lyric.startswith(" ")):
            final_lyrics[len(final_lyrics) -
                         1] = final_lyrics[len(final_lyrics)-1] + lyric
        else:
            final_lyrics.append(lyric)
    return "[ti:" + song["title_with_featured"] + "]\n[ar:" + song["primary_artist"]["name"] + "]\n" + "\n".join(final_lyrics)


# First, ensure user input exists
genius_access_token = os.getenv("GENIUS_ACCESS_TOKEN")
if len(genius_access_token) == 0:
    genius_access_token = None
if genius_access_token is None:
    print("Note: The GENIUS_ACCESS_TOKEN environment variable has not been defined. Only Lyricsify.com will be used as a data source.")
if (len(sys.argv) < 2):
    raise NameError(
        "The song directory path has not been provided as a parameter.")
song_dir = sys.argv[1]

# For each file in the songs directory, grab the artist/title and use them to find Lyricsify.com lyrics (with Genius.com as a fallback) and save them to the file
files = [os.path.splitext(each) for each in os.listdir(song_dir)]
# To suppress CRC check failed warnings - as a pre-existing CRC issue should not affect lyrics
eyed3.log.setLevel("ERROR")
for i, file in enumerate(files):
    audio_file = eyed3.load(song_dir + "/" + file[0] + file[1])
    if audio_file is None:
        print(str(i+1) + "\tof " + str(len(files)) + " : Failed  : Unsupported file format              : " +
              file[0] + file[1])
        continue
    if audio_file.tag is None:
        audio_file.initTag()
        temp_ind = file[0].find("-")
        if len(file[0]) > 0 and temp_ind > 0 and not file[0].endswith("-"):
            audio_file.tag.artist = file[0][0:temp_ind]
            audio_file.tag.title = file[0][temp_ind+1:]
            print(str(i+1) + "\tof " + str(len(files)) +
                  " : Warning : Artist/Title inferred from file name : " + file[0] + file[1])
        else:
            print(str(i+1) + "\tof " + str(len(files)) + " : Failed  : Artist/Title could not be found      : " +
                  file[0] + file[1])
            continue
    existing_lyrics = ""
    for lyric in audio_file.tag.lyrics:
        existing_lyrics += lyric.text
    if len(existing_lyrics.strip()) > 0:
        print(str(i+1) + "\tof " + str(len(files)) + " : Warning : File already has lyrics - skipped    : " +
              file[0] + file[1])
        continue
    # Note: re.sub... removes anything in brackets - used for "(feat. ...) as this improves search results"
    query = re.sub(r" ?\([^)]+\)", "",
                   audio_file.tag.artist + " - " + audio_file.tag.title)
    site_used = "Lyricsify"
    try:
        lyrics = lyricsify_find_song_lyrics(query)
    except Exception as e:
        print("Error getting Lyricsify lyrics for: " + file[0] + file[1])
        raise e
    if lyrics is None and genius_access_token is not None:
        site_used = "Genius   "
        try:
            lyrics = genius_find_song_lyrics(query, genius_access_token)
        except Exception as e:
            print("Error getting Lyricsify lyrics for: " + file[0] + file[1])
            raise e
    if lyrics is not None:
        audio_file.tag.lyrics.set(lyrics)
        audio_file.tag.save()
        print(str(i+1) + "\tof " + str(len(files)) + " : Success : Lyrics from " + site_used + " saved to       : " +
              file[0] + file[1])
    else:
        print(str(i+1) + "\tof " + str(len(files)) + " : Failed  : Lyrics not found for                 : " +
              file[0] + file[1])

# To generate lrc files from AutoLyricize-processed audio files if needed (bash script, requires exiftool):
# for f in *; do lrc="$(exiftool -lyrics "$f" | tail -c +35 | sed 's/\.\.\./\n\n/g' | sed 's/\.\./\n/g')"; if [ -n "$lrc" ]; then echo "$lrc" > "${f%.*}".lrc; fi; done