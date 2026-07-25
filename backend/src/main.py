## Imports

# for security importing keys
from backend.src.main import stream_id
from backend.src.main import recently_played
from dotenv import dotenv_values
# Spotify API for Python
import spotipy
# Login for Spotify API
from spotipy.oauth2 import SpotifyOAuth
# Gemini API for song recommendation
from google import genai
# turn jpg image to base 64 bytes
import base64
# os for filepaths
import os
# time for spotify loop
import time

# get current path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# path to DB logo
IMAGE_PATH = os.path.abspath(os.path.join(CURRENT_DIR,'../../frontend/media/db-black-tiny.jpg'))

# import secrets
secrets_path = os.path.abspath(os.path.join(CURRENT_DIR, '../../.env.dev')) # to get the env dev file
secrets = dotenv_values(secrets_path)

# list of permissions needed to access user information
SCOPE_LIST=['user-read-currently-playing','user-modify-playback-state','user-read-playback-state', 'user-read-private', 'playlist-modify-public', 'playlist-modify-private', 'ugc-image-upload']

# access spotify api using credentials
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=secrets['SPOTIFY_CLIENT_ID'],
    client_secret=secrets['SPOTIFY_CLIENT_SECRET'], 
    redirect_uri=secrets['SPOTIFY_REDIRECT_URI'],
    scope=SCOPE_LIST
))

# access Gemini API client
client = genai.Client(api_key=secrets['GEMINI_API_KEY'])


# counter for how many songs to be added to queue
# subtracts by 1 after every song
count = 15 # Gemini API only allows up to 20 requests per day, 1 is needed for playlist title
# list of recently played songs for Gemini to avoid
recently_played = []

# time left variable initialization
time_left = 0

def prompt_user_state(state):
    return f"User is feeling {state} to the current song."

# get song uri function to add song into queue
def get_song_uri(song_title, song_artist):
    query = "track: "+song_title+" artist: " + song_artist
    # Antigravity Agent suggested to add market variable to prevent unplayable tracks from being added
    result = sp.search(q=query, limit=1, type="track", market='from_token')
    tracks = result.get('tracks', {}).get('items', [])
    if tracks: 
        song_uri = tracks[0]['uri']
        return song_uri

# function to calculate time left of song in seconds
def calculate_time_left(track):
    duration_ms = track['item']['duration_ms']
    progress_ms = track['progress_ms']
    time_left_ms = duration_ms - progress_ms
    time_left = int(time_left_ms/1000)
    return time_left

# current music reccomendation system
# run song suggestion prompt
def run_prompt(prompt):
    interaction = client.interactions.create(
        model = 'gemini-3-flash', # change with gemini-2.5-flash or gemini-3.5-flash for more requests,
        input = prompt
    )
    return interaction.output_text

# find songs that match similar tempo and follows Camelot wheel
camelot_mode = False
camelot_prompt = ""
if camelot_mode:
    camelot_prompt = "When searching for song, use Camelot wheel to stay in the same key, move up or down one number, or switch between Minor(A) or Major(B) and match tempo, more or less, of current song"

# returns playlist id
def spotify_playlist_creation():
    user_id = sp.current_user()["id"]
    playlist_name = "Your Stream"
    playlist_description = "Brought to you by the Decoded Brain at UC San Diego. Your Stream will be saved to this playlist as you listen"

    new_playlist = sp.user_playlist_create(
        user=user_id,
        name=playlist_name,
        public=False, # i set public to false, yet it still makes a public playlist
        description=playlist_description
    )
    return new_playlist["id"]

def run_stream(status_callback=None, stop_event=None):
    global count, recently_played, time_left, stream_id

    # reset variables for new Stream
    count = 15
    recently_played = []
    time_left = 0
    stream_id = None
    queued_for_track_id = None

    if status_callback:
        status_callback({
            "status":"initializing",
            "message":"Initializing Spotify playlist...",
            "recently_played": recently_played,
            "current_song":None,
            "playlist_id":None
        })
    
    first_song_uri=None
    song_to_add = []

    # get currently playing song as first song
    try:
        current_playing = sp.current_user_playing_track()
        if current_playing and current_playing.get('is_playing'):
            current_track_name = current_playing['item']['name']
            current_track_artist = current_playing['item']['artists'][0]['name']
            first_song_uri = get_song_uri(current_track_name, current_track_artist)
            if first_song_uri:
                song_to_add.append(first_song_uri)
                recently_played.append(current_track_name+ " by " + current_track_artist) # might need to change to song that actually plays vs wants to play since it leads to duplicates
    except Exception as e:
        print(f"Error checking currently playing track: {e}")

    try:
        stream_id = spotify_playlist_creation()
        stream_name = "Your Stream #" + stream_id[-4:] # change title to Your Stream #aaaa
        sp.playlist_change_details(playlist_id=stream_id, name=stream_name)
        if song_to_add:
            sp.playlist_add_items(playlist_id=stream_id, items=song_to_add)

        # upload cover image
        with open(IMAGE_PATH, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        
        try: 
            sp.playlist_upload_cover_image(stream_id, encoded_string)
            print("Cover art uploaded successfully")
        except Exception as e:
            print(f"An error occurred during cover art upload: {e}")
    except Exception as e:
        print(f"Error setting up Spotify playlist: {e}")
        if status_callback:
            status_callback({
                "status":"error",
                "message": f"Error setting up Spotify playlist: {e}",
                "recently_played": recently_played,
                "current_song": None,
                "playlist_id": None
            })
        return
    
    if status_callback:
        current_song_name = recently_played[0] if recently_played else None
        status_callback({
            "status":"running",
            "message":"Your Stream has started! Listening on Spotify...",
            "recently_played":recently_played,
            "current_song": current_song_name,
            "playlist_id":stream_id
        })

        # Main Polling Loop 
        while count > 0:
            if stop_event and stop_event.is_set():
                print("Stopping Stream...")
                break
            
            try:
                current_track = sp.current_user_playing_track()
                if current_track and current_track.get('is_playing'):
                    current_track_name = current_track['item']['name']
                    current_track_artist = current_track['item']['artists'][0]['name']
                    current_track_id = current_track['item']['id']
                    current_song_name = current_track_name + " by " + current_track_artist # title + artist

                    # update status callback on currently playing song
                    if status_callback:
                        status_callback({
                            "status":"running",
                            "message":f"Currently playing: {current_song_name}", # Omitting time left for now
                            "recently_played":recently_played,
                            "current_song":current_song_name,
                            "playlist_id":stream_id
                        })
                    
                    # Check if we should search and queue a new song
                    if 0<time_left <=25 and queued_for_track_id != current_track_id:
                        print(f"Suggesting new song...")
                        
                        if status_callback:
                            status_callback({
                                "status":"running",
                                "message":f"Suggesting new song...",
                                "recently_played":recently_played,
                                "current_song":current_song_name,
                                "playlist_id":stream_id   
                            })
                        
                        # mark next track ID as queued so it's no longer triggered again, safety lock
                        queued_for_track_id = current_track_id
                        if current_song_name not in recently_played:
                            recently_played.append(current_song_name)
                            
                            global client
                            client = genai.Client(api_key=secrets['GEMINI_API_KEY'])
                            state_prompt = prompt_user_state('pleasure')
                            prompt = f"{state_prompt} Find a song that matches user state and is similar to {current_track_name} by {current_track_artist}.{camelot_prompt}**Important**: Reply with only the song name and artist of the song in this format: Title: <insert title>\n Artist: <insert artist name>. Verify the song is not part of this list, if it is try again: {recently_played}."
                            
                            output = run_prompt(prompt)
                            new_song_artist = output.split(':')[-1].strip()
                            new_song_title = output.split(':')[1].split('Artist')[0].strip()

                            upcoming_song_uri = get_song_uri(new_song_title, new_song_artist)
                            if upcoming_song_uri:
                                sp.add_to_queue(uri=upcoming_song_uri)
                                song_to_add.clear()
                                song_to_add.append(upcoming_song_uri)
                                sp.playlist_add_items(stream_id, song_to_add)

                                recommended_song_name = f"{new_song_title} by {new_song_artist}"
                                recently_played.append(recommended_song_name)
                                print(f"Added {recommended_song_name} to queue!")
                                count -=1

                                if status_callback:
                                    status_callback({
                                        "status":"running",
                                        "message":f"Added recommended song: {recommended_song_name}",
                                        "recently_played": recently_played,
                                        "current_song":current_song_name,
                                        "playlist_id":stream_id
                                    })
                                else:
                                    print(f"Could not find a playable song on Spotify for: {new_song_title} by {new_song_artist}")
                                    if status_callback:
                                        status_callback({
                                            "status":"running",
                                            "message":f"Could not find a playable song on Spotify for: {new_song_title} by {new_song_artist}",
                                            "recently_played":recently_played,
                                            "current_song":current_song_name,
                                            "playlist_id":stream_id
                                        })
                # if spotify is active but no track is playing, needs to be updated
                else:
                    if status_callback:
                        status_callback({
                            "status":"running",
                            "message":"Spotify is active but no track is currently playing or it is paused",
                            "recently_played":recently_played,
                            "current_song": None,
                            "playlist_id": stream_id
                        })
            except Exception as e:
                print(f"Error in Stream loop iteration: {e}")
                if status_callback:
                    status_callback({
                        "status":"running",
                        "message": f"Error checking Spotify {e}",
                        "recently_played":recently_played,
                        "current_song":None,
                        "playlist_id":stream_id
                    })
            # avoid reaching rate limits, so sleeps for 1 second, doesn't interfere with time_left count
            time.sleep(1)
        
        # Summary section
        if recently_played:
            try:
                if status_callback:
                    status_callback({
                        "status":"completing",
                        "message":"Generating custom title...",
                        "recently_played": recently_played,
                        "current_song":None,
                        "playlist_id":stream_id
                    })
                # adds custom title to playlist 
                new_playlist_title = run_prompt(f"View the songs listed in {recently_played} and write a title for that playlist. Output ONLY the title name, nothing else.")
                sp.playlist_change_details(playlist_id=stream_id,name=new_playlist_title)

            except Exception as e:
                print(f"Error updating playlist title: {e}")
        print("="*40)
        print("List of songs played during your Stream: \n")
        for i in range(len(recently_played)):
            print(f"{i+1}. {recently_played[i]}")

        if status_callback:
            status_callback({
                "status":"stopped",
                "message":"Stream finished",
                "recently_played":recently_played,
                "current_song": None,
                "playlist_id":stream_id
            })

# Protect direct execution (running main on its own still works)
if __name__ == "__main__":
    run_stream()

            

    


    
