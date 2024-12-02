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
from colorist import Color
from dotenv import load_dotenv
load_dotenv()


def lyricsify_find_song_lyrics(query):
    """
    Return song lyrics from Lyricsify.com for the first song found using the provided search string.
    If not found, return None.
    """
    # Search Lyricsify for the song using web scraping
    link = BeautifulSoup(
        requests.get(url="https://www.lyricsify.com/lyrics/" +
                     query.lower().replace(
                         " - ", "/").replace(" ", "-"),
                     headers={
                         "User-Agent": os.getenv("HEADER")
                     }).text,
        "html.parser")
    divs = link.find_all("div", id=re.compile(r"lyrics_.*_details"))# The site obfuscates(?) the div name but we can bypass this with the power of regex
    
    # If not found, return None
    if divs is None:
        return None
    # Scrape the song html for the lyrics text
    song_html='\n'.join(str(divs[0]).split('\n')[1:-1]).replace("<br/>","")
    return(song_html)


def genius_find_song_lyrics(query, access_token):
    """
    Return song lyrics from Genius.com for the first song found using the provided search string.
    If not found, return None.
    Requires a Genius.com access token.
    """
    headers = {
        "User-Agent": os.getenv("HEADER"),
        "Authorization": "Bearer " + access_token,  # Include your Genius API key
    }
    # Search Genius for the song using their API
    results = json.loads(requests.get(url="https://api.genius.com/search?q=" + urllib.parse.quote(query), headers={
        "Authorization": "Bearer " + access_token,
        "User-Agent": os.getenv("HEADER")
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
    page = requests.get(song["url"], headers=headers)
    html = BeautifulSoup(page.text, "html.parser")
    if (html.find("div", id="cloudflare_content")):
        raise Exception(
            "Scraping encountered Cloudflare and cannot continue.")
    target_divs = html.find_all("div", {'data-lyrics-container': "true"})
    lyrics = []
    for div in target_divs:    
        if div is None: # This ususally means the song is an instrumental (exists on the site and was found, but no lyrics)
            return None
        else:
            lyrics = "\n".join("\n".join(div.strings) for div in target_divs).split("\n")
    final_lyrics = "\n".join(lyrics)
    final_lyrics = final_lyrics.replace("(\n","(").replace("\n)",")").replace(" \n"," ").replace("\n]","]").replace("\n,",",").replace("\n'\n","\n'").replace("\n[","\n\n[") # Removing unwanted line breaks. This mostly works
    if final_lyrics == "":
        return None
    return final_lyrics

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

# Record all files in the current directory by both full path and short name
try: os.remove('current.txt')
except OSError: pass
open('current.txt', 'a').close()
try: os.remove('short.txt')
except OSError: pass
open('short.txt', 'a').close()

with open('current.txt', 'a') as current:
    total = 0
    with open('short.txt', 'a') as short:
        for folder, subs, files in os.walk(song_dir):
            for file in files:
                current.write(folder + '/' + file + '\n')
                short.write(file + '\n')
                total += 1
if total == 0:
    print("Directory is empty or does not exist.")
else:
    overwrite = input("Reply Y to overwrite current lyrics: ").lower()

# To suppress CRC check failed warnings - as a pre-existing CRC issue should not affect lyrics
eyed3.log.setLevel("ERROR")
with open('current.txt') as current:
    i = 0
    shlong = open("short.txt", 'r')
    short = shlong.readlines()
    for file in current:
        try: audio_file = eyed3.load(file.strip())
        except:
            print(str(i+1) + "\tof " + str(total) + f" : {Color.RED}Failed{Color.OFF}  : File does not appear to exist        : " +
                  short[i].strip())
            i += 1
            continue
        if audio_file is None:
            print(str(i+1) + "\tof " + str(total) + f" : {Color.RED}Failed{Color.OFF}  : Unsupported file format              : " +
                  short[i].strip())
            i += 1
            continue
        if audio_file.tag is None:
            audio_file.initTag()
            temp_ind = file.find("-")
            continue
        """
        if len(file) > 0 and temp_ind > 0 and not file.endswith("-"):
            audio_file.tag.artist = file[0][0:temp_ind]
            audio_file.tag.title = file[0][temp_ind+1:]
            print(str(i+1) + "\tof " + str(len(files)) +
              " : Warning : Artist/Title inferred from file name : " + file[0] + file[1])
        else:
            print(str(i+1) + "\tof " + str(len(files)) + " : Failed  : Artist/Title could not be found      : " +
              file[0] + file[1])
            continue
        # didn't adapt this section since this situation doesn't happen to me. also i don't understand the code.
        """
        existing_lyrics = ""
        for lyric in audio_file.tag.lyrics:
            existing_lyrics += lyric.text
        if len(existing_lyrics) > 0 and overwrite != 'y':
            print(str(i+1) + "\tof " + str(total) + f" : {Color.YELLOW}Warning{Color.OFF} : File already has lyrics - skipped    : " +
                  short[i].strip())
            i += 1
            continue
        # Note: re.sub... removes anything in brackets - used for "(feat. ...) as this improves search results"
        query = re.sub(r" \[^]+\)", "",
               audio_file.tag.artist + " - " + audio_file.tag.title)
        site_used = "Lyricsify"
        ''' i don't actually want to use lyricsify. uncomment if you do.
        try:
            lyrics = lyricsify_find_song_lyrics(query)
        except Exception as e:
            print("Error getting Lyricsify lyrics for: " + short[i].strip())
            raise e
        '''
        lyrics = None
        if lyrics is None and genius_access_token is not None:
            site_used = "Genius   "
            try:
                #print(query)
                lyrics = genius_find_song_lyrics(query, genius_access_token)
            except Exception as e:
                print("Error getting Genius lyrics for: " + short[i].strip())
                raise e
        if lyrics is not None:
            audio_file.tag.lyrics.set(lyrics)
            audio_file.tag.save()
            print(str(i+1) + "\tof " + str(total) + f" : {Color.GREEN}Success{Color.OFF} : Lyrics from " + site_used + " saved to       : " +
                  short[i].strip())
        else:
            print(str(i+1) + "\tof " + str(total) + f" : {Color.RED}Failed{Color.OFF}  : Lyrics not found for                 : " +
                  short[i].strip())
        i += 1
os.remove('current.txt')
os.remove('short.txt')
# To generate lrc files from AutoLyricize-processed audio files if needed (bash script, requires exiftool):
# for f in *; do lrc="$(exiftool -lyrics "$f" | tail -c +35 | sed 's/\.\./\n/g' | sed 's/\.\[/\n[/g')"; if [ -n "$lrc" ]; then echo "$lrc" > "${f%.*}".lrc; fi; done
