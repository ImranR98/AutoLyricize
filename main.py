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
    global inexact
    inexact = 0
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
    try: song_html=str('\n'.join(str(divs[0]).split('\n')[1:-1]).replace("<br/>",""))
    except:
        return None
    return(song_html[song_html.find("[ar: "):])





inexact_url=""
def genius_find_song_lyrics(query, access_token):
    """
    Return song lyrics from Genius.com for the first song found using the provided search string.
    If not found, return None.
    Requires a Genius.com access token.
    """
    headers = {
        "User-Agent": os.getenv("HEADER"),
        "Authorization": "Bearer " + access_token,
    }
    results = json.loads(requests.get(url="https://api.genius.com/search?q=" + urllib.parse.quote(query), headers={
        "Authorization": "Bearer " + access_token,
        "User-Agent": os.getenv("HEADER")
    }).text)
    if len(results["response"]["hits"]) <= 0:
        return None
    song = results["response"]["hits"][0]["result"]
    query_lower = query.lower()
    
    # Use Genius sucky search if you can and there's no exact match
    # Also sets variables to make this more transparent
    global inexact
    global inexact_url
    inexact = 0
    if query_lower.find(song["title"].lower()) <= 0 or query_lower.find(song["primary_artist"]["name"].lower()) <= 0:
        if requireexact == "y":
            return None
        inexact = 1
        inexact_url = song["url"]
 
    # Scrape the song URL for the lyrics text
    page = requests.get(song["url"], headers=headers)
    html = BeautifulSoup(page.text, "html.parser")
    if (html.find("div", id="cloudflare_content")):
        raise Exception(
            f"{Color.RED}Scraping encountered Cloudflare and cannot continue.{Color.OFF}")
    target_divs = html.find_all("div", {'data-lyrics-container': "true"})
    lyrics = []
    
    # Processing the fetched data
    for div in target_divs:    
        if div is None:
            return None
        else:
            lyrics = "\n".join("\n".join(div.strings) for div in target_divs).split("\n")
    final_lyrics = "\n".join(lyrics)
    if final_lyrics == "":
        inexact = 0
        return "inst"
    final_lyrics = final_lyrics.replace("(\n","(").replace("\n)",")").replace(" \n"," ").replace("\n "," ").replace("\n]","]").replace("\n,",",").replace("\n'\n","\n'").replace("\n\n[","\n[").replace("\n[","\n\n[") 
    # Removing unwanted line breaks lol
    return final_lyrics

# Hyperlink on inexact match
def link(uri, label=None):
    if label is None: 
        label = uri
    parameters = ''
    # OSC 8 ; params ; URI ST <name> OSC 8 ;; ST 
    escape_mask = '\033]8;{};{}\033\\{}\033]8;;\033\\'
    return escape_mask.format(parameters, uri, label)




# Start of the main script
if (len(sys.argv) < 2) and not os.getenv("STATIC_WORKING_DIR"):
    raise NameError(
        "The song directory path has not been provided as a parameter.")
if len(sys.argv) >= 2:
	song_dir = sys.argv[1]
else:
	song_dir = os.getenv("STATIC_WORKING_DIR")


# Resetting files
try: os.remove('current.txt')
except OSError: pass
open('current.txt', 'a').close()
try: os.remove('short.txt')
except OSError: pass
open('short.txt', 'a').close()
inexact = 0


# Tallying all the tracks
with open('current.txt', 'a') as current, open('short.txt', 'a') as short:
    total = 0
    for folder, subs, files in os.walk(song_dir):
        for file in files:
            current.write(folder + '/' + file + '\n')
            short.write(file + '\n')
            total += 1


# Environment variables and user input
genius_access_token = os.getenv("GENIUS_ACCESS_TOKEN")
if len(genius_access_token) == 0:
    genius_access_token = None
if genius_access_token is None:
    print(f"{Color.YELLOW}The GENIUS_ACCESS_TOKEN environment variable has not been defined. Genius searches will not be conducted.{Color.OFF}")
    
if total == 0:
    print("Directory is empty or does not exist.")
else:
    yesno = [ "y", "n" ]
    overwrite = input("Overwrite current lyrics? y/N ").lower()
    if overwrite not in yesno:
        print(f"{Color.YELLOW}Interpreting unknown response as no{Color.OFF}")
        evenifunsynced = "n"
    elif overwrite == "y" and os.getenv("I_WANT_SYNCED_LYRICS") == "True":
        evenifunsynced = input("Even if the new ones are unsynced? y/N ").lower()
        if evenifunsynced != "y":
            print(f"{Color.YELLOW}Intepreting unknown response as no{Color.OFF}")
            evenifunsynced = "n"
    requireexact = input("Require exact artist and title? (Recommended with large folders!!!) Y/n ").lower()
    if requireexact not in yesno:
        print(f"{Color.YELLOW}Interpreting unknown response as yes{Color.OFF}")
        requireexact = "y"
    print("\n")
# To suppress CRC check failed warnings - as a pre-existing CRC issue should not affect lyrics
eyed3.log.setLevel("ERROR")
with open('current.txt') as current:
    shlong = open("short.txt", 'r')
    short = shlong.readlines()
    
    
    for i, file in enumerate(current):
        try: audio_file = eyed3.load(file.strip())
        except:
            print(str(i+1) + "\tof " + str(total) + f" : {Color.RED}Failed{Color.OFF}  : File does not appear to exist        : " +
                  short[i].strip())
            continue
        if audio_file is None:
            print(str(i+1) + "\tof " + str(total) + f" : {Color.RED}Failed{Color.OFF}  : Unsupported file format              : " +
                  short[i].strip())
            continue
            
        '''
        # Automatically detecting metadata of untagged files. This does not work
        if audio_file.tag is None:
            audio_file.initTag()
            audio_file.tag.artist = u'TPE1'
            audio_file.tag.title = u'TIT2'
            temp_ind = file.find("-")
            if len(file) > 0 and temp_ind > 0 and not file.endswith("-"):
                audio_file.tag.artist.set(file[0][0:temp_ind])
                audio_file.tag.title.set(file[0][temp_ind+1:])                
                print(str(i+1) + "\tof " + str(len(files)) +
                  f" : {Color.YELLOW}Warning{Color.OFF} : Artist/Title inferred from file name : " + short[i].strip())
            else:
                print(str(i+1) + "\tof " + str(len(files)) + f" : {Color.RED}Failed{Color.OFF}  : Artist/Title could not be found      : " +
                  short[i].strip())
                continue
        '''
        
        existing_lyrics = ""
        try:
            for lyric in audio_file.tag.lyrics:
                existing_lyrics += lyric.text
        except:
            existing_lyrics = ""
        if len(existing_lyrics) > 0 and overwrite != 'y':
            print(str(i+1) + "\tof " + str(total) + f" : {Color.YELLOW}Skipped{Color.OFF} : File already has lyrics              : " +
                  short[i].strip())
            continue
        # Note: re.sub... removes anything in brackets - used for "(feat. ...) as this improves search results"
        try:
            query = re.sub(r" \[^]+\)", "",
                   audio_file.tag.artist + " - " + audio_file.tag.title)
        except:
            print(str(i+1) + "\tof " + str(total) + f" : {Color.RED}Failed{Color.OFF}  : Artist/Title could not be found      : " +
              short[i].strip())
            continue
        
        # Calling Lyricsify script
        if os.getenv("I_WANT_SYNCED_LYRICS") == "True":
            site_used = "Lyricsify"
            try:
                lyrics = lyricsify_find_song_lyrics(query)
            except Exception as e:
                print(f"{Color.RED}Error getting Lyricsify lyrics for: " + short[i].strip() + f"{Color.OFF}")
                raise e
                
        
        # Calling Genius script
        if lyrics is None and genius_access_token is not None and ( len(existing_lyrics) == 0 or evenifunsynced == "y" ):
            site_used = "Genius   "
            try:
                lyrics = genius_find_song_lyrics(query, genius_access_token)
            except Exception as e:
                print(f"{Color.RED}Error getting Genius lyrics for: " + short[i].strip() + f"{Color.OFF}")
                raise e
                
                
        # Dealing with double lyrics tags. These were a pain in the ass
        if b'USLT' in audio_file.tag.frame_set and lyrics is not None :
            del audio_file.tag.frame_set[b'USLT'] 
            audio_file.tag.save() # Utterly villainous way to delete the previous lyrics
            # If this throws an error you should run print(audio_file.tag.frame_set.keys()) to check what tag to use instead
            # USLT is lyrics. b'USLT' means it's stored in bytes instead of as a string
                
             
        # Saving tags and logging success
        if lyrics is not None:
            # Instrumental
            if lyrics == "inst":
                print(str(i+1) + "\tof " + str(total) + f" : {Color.YELLOW}Success{Color.OFF} : Genius says song is an instrumental  : " +
                      short[i].strip())
                continue
            audio_file.tag.lyrics.set(lyrics)
            audio_file.tag.save()
            if inexact == 1:
                # Success with inexact search
                print(str(i+1) + "\tof " + str(total) + f" : {Color.GREEN}Success{Color.OFF} : Lyrics from " + site_used + f" saved to  {Color.YELLOW}" + link(inexact_url, "(i)") + f"{Color.OFF}  : " +
                      short[i].strip())
            else:
                # Success with perfect match
                print(str(i+1) + "\tof " + str(total) + f" : {Color.GREEN}Success{Color.OFF} : Lyrics from " + site_used + " saved to       : " +
                      short[i].strip())
                      
        # Logging failures              
        elif evenifunsynced != "y" and len(existing_lyrics) > 0:
            # No synced results when only synced results are allowed
            print(str(i+1) + "\tof " + str(total) + f" : {Color.YELLOW}Failed{Color.OFF}  : No synced lyrics found, preserving   : " +
              short[i].strip())
        else:
            # No lyrics found at all
            print(str(i+1) + "\tof " + str(total) + f" : {Color.RED}Failed{Color.OFF}  : Lyrics not found for                 : " +
              short[i].strip())
              
              
              
os.remove('current.txt')
os.remove('short.txt')


# To generate lrc files from AutoLyricize-processed audio files if needed (bash script, requires exiftool):
# for f in *; do lrc="$(exiftool -lyrics "$f" | tail -c +35 | sed 's/\.\./\n/g' | sed 's/\.\[/\n[/g')"; if [ -n "$lrc" ]; then echo "$lrc" > "${f%.*}".lrc; fi; done

# This file really didn't need this many comments did it
