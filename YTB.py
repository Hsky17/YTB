import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from config import BOT_TOKEN
import os
import yt_dlp
import requests
global songlist
songlist = []
global linklist
linklist = []
global voters
voters = []
global alreadyRan
voice_client = None

# This is your youtube api key for creating embeds, pretty big implemenentation of the bot but could be rewritten to not use it
API_KEY = "API_KEY_HERE"

async def music(interaction, query):
    global voice_client
    # Gets the voice channel of the user 
    voice_state = interaction.user.voice
    print(f"Voice state is {voice_state}")

    # Checks for annoying danny messages
    if "pornhub" in query:
        print("Found unfunny website")
        await interaction.response.send_message('Your not funny exiting')
    
    if voice_client and voice_client.is_playing():
        print("Running song is play logic")
        await interaction.response.send_message("Song is already playing, adding to queue")
        with yt_dlp.YoutubeDL() as ydl:
            if "youtube.com" in query:
                info = ydl.extract_info(query, download=False)
                song_title = info['title']
            else:
                search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
                first_result = search_results['entries'][0]
                query = first_result['webpage_url']
                song_title = first_result['title']

        linklist.append(query)
        songlist.append(song_title)
        print("Added link and song")
        await interaction.edit_original_response(content=f"Added `{song_title}` to queue")
    else:

        # As long as the user is in a channel and is connected?
        if voice_state is not None and voice_state.channel is not None:
            
            # Defines the voice channel to connect to
            voice_channel = voice_state.channel
            print(f"Voice channel is {voice_channel}")

            # Check if the directory "MusicFiles" exists
            if not os.path.exists('MusicFiles'):
                # Make the MusicFiles directory
                os.makedirs('MusicFiles')
            # Example using yt-dlp to retrieve song title and download audio
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': 'MusicFiles/%(title)s.%(ext)s',
                'noplaylist': True
            }
            # Runs yt-dlp to download the mp3 file 
            # Runs yt-dlp to get information about the file (without downloading it)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if "youtube.com" in query:
                    info = ydl.extract_info(query, download=False)
                    file_size = info.get('filesize', None)
                else:
                    file_size = None
                if file_size is not None and file_size > 300 * 1024 * 1024:  # Check if file size is over 300MB
                    # Notify the user that the file is too large to download
                    message = "The file size is too large. The download will be aborted."
                    await interaction.response.send_message(message)  
                else:
                    # Runs yt-dlp to download the mp3 file if it's under the size limit
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.cache.remove()
                        if "youtube.com" in query: 
                            print(f"Link is: {query}, downloading...")
                            try:
                                await interaction.response.send_message('Downloading...')  # Send initial response
                                alreadyRan = False
                            except:
                                await interaction.edit_original_response(content='Downloading...',embed=None)
                                alreadyRan = True
                                print("Send downloading message")
                            info = ydl.extract_info(query, download=True)
                            audio_filename = ydl.prepare_filename(info)
                        else:
                            try:
                                await interaction.response.send_message('Searching...')  # Send initial response
                                alreadyRan = False
                            except:
                                await interaction.edit_original_response(content='Searching...',embed=None)
                            search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
                            first_result = search_results['entries'][0]
                            query = first_result['webpage_url']
                            info = ydl.extract_info(query, download=True)
                            audio_filename = ydl.prepare_filename(info)
                            print(f"Searched query is {query}")




                    # Connects to the voice channel and sets up channel commands if needed
                    if interaction.guild.voice_client is None:
                        voice_client = await voice_channel.connect()
                        print("Connected to vc")

                    # Youtube embed stuff
                    video_id = query.split("v=")[1]
                    response = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={video_id}&key={API_KEY}")
                    video_data = response.json()
                    # print(f"Video data is: {video_data}")
                    if "items" in video_data:
                        video = video_data["items"][0] 
                        title = video["snippet"]["title"]
                        thumbnail = video["snippet"]["thumbnails"]["high"]["url"]
                        duration = video["contentDetails"]["duration"]

                    # Create and send an embed message with video details
                    embed = discord.Embed(title=title, color=discord.Color.blue())
                    embed.set_thumbnail(url=thumbnail)
                    # Add a field for video duration
                    embed.add_field(name="Duration", value=convert_iso8601_duration(duration), inline=False)  # Set inline to False for vertical alignment
                    print("Created embed")
                    
                    # Convert the downloaded audio to WebM format using FFmpeg
                    # Play the converted audio file using FFmpeg
                    voice_client.play(discord.FFmpegPCMAudio(audio_filename), after=lambda e: on_music_end(title, voice_client, interaction, e))
                    print("Playing music")
                    isplaying = True
                    
                    async def pause(interaction):
                        if voice_client is not None:
                            voice_client.pause()
                            rbutton = Button(label="Resume", style=discord.ButtonStyle.green, emoji="▶️")
                            rbutton.callback = resume
                            view.clear_items()
                            view.add_item(rbutton)
                            await interaction.message.edit(view=view)
                            print("Paused")
                    async def resume(interaction):
                        if voice_client is not None:
                            voice_client.resume()
                            view.clear_items()
                            view.add_item(pbutton)
                            view.add_item(sbutton)
                            view.add_item(skbutton)
                            await interaction.message.edit(view=view)
                            print("Resumed")
                    async def skip(interaction):
                        if voice_client is not None:
                            if str(interaction.user) not in voters:
                                voters.append(str(interaction.user))
                                if len(voice_channel.members) > 3:
                                    votesNeeded = len(voice_channel.members) // 2
                                    if len(voters) >= votesNeeded:
                                        print("Skipping")
                                        del voters[:]
                                        voice_client.stop()
                                    else:
                                        await interaction.response.send_message(f"Voted! You have {str(len(voters))}/{str(int(votesNeeded))} votes")
                                else:
                                    print("Skipping")
                                    del voters[:]
                                    voice_client.stop()
                            else:
                                await interaction.response.send_message("You already voted :x:")
            
                    pbutton = Button(label="Pause", style=discord.ButtonStyle.gray, emoji="⏸️")
                    sbutton = Button(label="Stop", style=discord.ButtonStyle.red, emoji="⏹️")
                    skbutton = Button(label="Skip", style=discord.ButtonStyle.green, emoji="⏩")
                    pbutton.callback = pause
                    sbutton.callback = stop
                    skbutton.callback = skip
                    view = View()
                    view.add_item(pbutton)
                    view.add_item(sbutton)
                    view.add_item(skbutton)
                    await interaction.edit_original_response(content="", embed=embed, view=view)
                    print("Edited message to display embed")
        else:
            await interaction.response.send_message("Your not in a vc")

def on_music_end(song_title, voice_client,interaction, error):
        print("made it to music end")
        print(f"Songlist: {songlist}")
        print(f"Songtitle: {song_title}")
        if error:
            print(f"Error during playback: {error}")
        if len(linklist) == 0:
            print("Queue is empty, disconnecting")
            voice_client.stop()
            asyncio.run_coroutine_threadsafe(voice_client.disconnect(),voice_client.loop)
        elif song_title == songlist[0]:
            del linklist[0]
            del songlist[0]
            print(f"Deleted {song_title} from the list")
            if len(songlist) != 0:
                print("Still a song in queue, playing new song")
                asyncio.run_coroutine_threadsafe(music(interaction,linklist[0]),voice_client.loop)
            else:
                print("Queue is empty, disconnecting")
                voice_client.stop()
                asyncio.run_coroutine_threadsafe(voice_client.disconnect(),voice_client.loop)
        else:
            print("Song still in queue")
            asyncio.run_coroutine_threadsafe(music(interaction,linklist[0]),voice_client.loop)





def convert_iso8601_duration(duration):
    # Remove the leading 'PT' from the duration string
    duration = duration[2:]
    print(f"Duration is {duration}")
    # Initialize variables for minutes and seconds
    minutes = 0
    seconds = 0
    hours = 0

    # Extract hours if present
    if 'H' in duration:
        hours_str = duration.split('H')[0]
        hours = int(hours_str)
        duration = duration[len(hours_str) + 1:] # Remove the extracted hours part

    # Extract minutes if present
    if 'M' in duration:
        minutes_str = duration.split('M')[0]
        minutes = int(minutes_str)
        duration = duration[len(minutes_str) + 1:]  # Remove the extracted minutes part
    
    # Extract seconds if present
    if 'S' in duration:
        seconds_str = duration.split('S')[0]
        seconds = int(seconds_str)
    
    return f"{hours} hour(s), {minutes} minutes, and {seconds} seconds"

# Bot startup command
bot = commands.Bot(command_prefix="!", intents = discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot is Up and Ready!")
    try:
        # Try to sync all commands
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
        

    
    




    
    
    
    

@bot.tree.command(name="play", description="Play a song!")
@app_commands.describe(link = "Link or search term of the youtube video")
async def play(interaction: discord.Interaction, link: str):
    await music(interaction,link)

async def stop(interaction):
    if voice_client is not None:
        voice_client.stop()
        print("Stopped music")
        del songlist[:]
        del linklist[:]
        await interaction.message.delete()
        await voice_client.disconnect()



@bot.tree.command(name="queue", description="Command for managing the queue")
@app_commands.describe(option = "Remove, List")
@app_commands.describe(suboption = "Add link or specify song position to remove")
async def queue(interaction: discord.Interaction, option: str,suboption: str = ""):
    if option.lower() == "remove":
        if suboption == "":
            await interaction.response.send_message("No position given")
        elif suboption == "1":
            await interaction.response.send_message("You cant remove what your playing silly :P. Try the skip button instead...")
        else:
            position = int(suboption) - 1
            title = songlist[position]
            del linklist[position]
            del songlist[position]
            await interaction.response.send_message("Removed: " + title)
        
    
    
    
    if option.lower() == "list":
        if len(songlist) == 0:
            await interaction.response.send_message("Queue is empty, try adding something!")
        else:
            # Using a list comprehension to format each line with a number and the element
            formatted_songs = [f"{index + 1}. {song}" for index, song in enumerate(songlist)]
            await interaction.response.send_message("Queue currently is:\n" + '\n'.join(formatted_songs))



# Replace BOT_TOKEN with your bot token you get from https://discord.com/developers
bot.run("BOT_TOKEN")
