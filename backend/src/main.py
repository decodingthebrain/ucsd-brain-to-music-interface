from dotenv import dotenv_values
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google import genai


secrets = dotenv_values('../../.env.dev')
SCOPE_LIST=['user-read-currently-playing','user-modify-playback-state','user-read-playback-state']
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=secrets['SPOTIFY_CLIENT_ID'],
client_secret=secrets['SPOTIFY_CLIENT_SECRET'], redirect_uri=secrets['SPOTIFY_REDIRECT_URI'],scope=SCOPE_LIST))

count=0
recently_played=[]

def get_song_uri(song_title, song_artist):
    query = song_title + " " + song_artist
    result = sp.search(q=query, limit=1, type="track")
    tracks=result.get('tracks', {}).get('items', [])
    if tracks: 
        song_uri = tracks[0]['uri']
        return song_uri



while count < 10:
    current_track=sp.current_user_playing_track()
    if current_track and current_track.get('is_playing'):
        current_track_name=current_track['item']['name']
        current_track_artist=current_track['item']['artists'][0]['name']
        duration_ms = current_track['item']['duration_ms']
        progress_ms = current_track['progress_ms']
        time_left_ms = duration_ms - progress_ms
        time_left = int(time_left_ms/1000)
    
    if time_left == 15:
        recently_played.append(current_track_name + " by " + current_track_artist)
        prompt = f"Find a song similar to {current_track_name} by {current_track_artist} and not from this list: {recently_played}. Reply with only the song name and artist of the song in this format: Title: <insert title>\n Artist: <insert artist name>"
        client=genai.Client(api_key=secrets['GEMINI_API_KEY'])
        interaction = client.interactions.create(
            model = 'gemini-3.5-flash',
            input = prompt
        )
        output = interaction.output_text
        new_song_artist = output.split(':')[-1]
        new_song_title = output.split(':')[1].split('Artist')[0]
        upcoming_song_uri = get_song_uri(new_song_title, new_song_artist)
        sp.add_to_queue(uri=upcoming_song_uri)
        print(f"Added {new_song_title} by {new_song_artist} to queue!")
        count+=1
