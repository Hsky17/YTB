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
global userlist
userlist = []
global stoplist
stoplist = []
callbacks = {}
ranalready = False

async def music(interaction, query):
    global ranalready
    global voice_client
    # Gets the voice channel of the user 
    voice_state = interaction.user.voice
    print(f"Voice state is {voice_state}")
    
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

        if interaction.user.id not in userlist:
            userlist.append(interaction.user.id)
            print("Added user to list")
        linklist.append(query)
        songlist.append(song_title)
        print("Added link, song, and user")
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
                            if ranalready == False:
                                response_msg = await interaction.response.send_message('Downloading...')  # Send initial response
                            else:
                                sent_message = await interaction.channel.send(content='Downloading...')
                                print("Send downloading message")
                            info = ydl.extract_info(query, download=True)
                            audio_filename = ydl.prepare_filename(info)
                            song_title = info['title']
                            thumbnail_url = info.get('thumbnails', [{}])[0].get('url', '')
                            duration = info.get('duration', 0)
                            
                        else:
                            if ranalready == False:
                                response_msg = await interaction.response.send_message('Searching...')  # Send initial response
                                alreadyRan = False
                            else:
                                await interaction.channel.send(content='Searching...')
                            search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
                            first_result = search_results['entries'][0]
                            query = first_result['webpage_url']
                            info = ydl.extract_info(query, download=True)
                            audio_filename = ydl.prepare_filename(info)
                            song_title = info['title']
                            thumbnail_url = info.get('thumbnails', [{}])[0].get('url', '')
                            duration = info.get('duration', 0)
                            print(f"Searched query is {query}")




                    # Connects to the voice channel and sets up channel commands if needed
                    if interaction.guild.voice_client is None:
                        voice_client = await voice_channel.connect()
                        print("Connected to vc")

                    # Create and send an embed message with video details
                    embed = discord.Embed(title=song_title, url=query, color=discord.Color.blue())
                    embed.set_thumbnail(url=thumbnail_url)
                    # Add a field for video duration
                    embed.add_field(name="Duration:", value=convertfromseconds(duration), inline=False)  # Set inline to False for vertical alignment
                    # Fetching the user
                    if interaction.user.id not in userlist:
                        userlist.append(interaction.user.id)
                        print("Added user to list")
                    embed.add_field(name="Requested by:", value=f"<@{userlist[0]}>", inline=True)
                    print("Created embed")
                    
                    # Convert the downloaded audio to WebM format using FFmpeg
                    # Play the converted audio file using FFmpeg
                    voice_client.play(discord.FFmpegPCMAudio(audio_filename), after=lambda e: on_music_end(song_title, voice_client, interaction, sent_message, e))
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
                        await skiplogic(interaction)

                    async def skiplogic(interaction):
                        if voice_client is not None:
                            if str(interaction.user) not in voters:
                                voters.append(str(interaction.user))
                                if interaction.user.id == userlist[0]:
                                    del voters[:]
                                    voice_client.stop()
                                    return
                                if len(voice_channel.members) - 1 > 1:
                                    votesNeeded = len(voice_channel.members) - 1 // 2
                                    if len(voters) >= votesNeeded:
                                        del voters[:]
                                        voice_client.stop()
                                        return
                                    else:
                                        await interaction.channel.send(f"Voted! You have {str(len(voters))}/{str(int(votesNeeded))} votes")
                                else:
                                    del voters[:]
                                    voice_client.stop()
                                    return
                            else:
                                await interaction.channel.send("You already voted :x:")

                    async def stop(interaction):
                        if voice_client is not None:
                            if interaction.user.id in stoplist:
                                await interaction.response.send_message("You already voted!")
                            if interaction.user.id not in userlist:
                                await interaction.response.send_message("You haven't requested anything :x:")
                            else:
                                if len(userlist) > 1:
                                    userlist.remove(interaction.user.id)
                                    stoplist.append(interaction.user.id)
                                    await interaction.response.send_message(f"Voted to stop! {len(stoplist)}/{len(userlist)+len(stoplist)} votes, {len(userlist)} are needed...")
                                else:
                                    del userlist[:]
                            if len(userlist) == 0:
                                voice_client.stop()
                                print("Stopped music")
                                del songlist[:]
                                del linklist[:]
                                del userlist[:]
                                del stoplist[:]
                                await voice_client.disconnect()
                                await interaction.message.delete()
            
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
                    if ranalready == False:
                        await interaction.edit_original_response(content="", embed=embed, view=view)
                        ranalready = True
                        sent_message = await interaction.original_response()
                    else:
                        await sent_message.edit(content="", embed=embed, view=view)
                    
                    print("Edited message to display embed")
        else:
            await interaction.response.send_message("Your not in a vc")

def on_music_end(song_title, voice_client,interaction, sent_message, error):
        global alreadyran
        print("made it to music end")
        print(f"Songlist: {songlist}")
        print(f"Songtitle: {song_title}")
        asyncio.run_coroutine_threadsafe(sent_message.delete(),voice_client.loop)
        if error:
            print(f"Error during playback: {error}")
        if len(linklist) == 0:
            print("Queue is empty, disconnecting")
            voice_client.stop()
            alreadyran = False
            asyncio.run_coroutine_threadsafe(voice_client.disconnect(),voice_client.loop)
        elif song_title == songlist[0]:
            del linklist[0]
            del songlist[0]
            del userlist[0]
            print(f"Deleted {song_title} from the list")
            if len(songlist) != 0:
                print("Still a song in queue, playing new song")
                asyncio.run_coroutine_threadsafe(music(interaction,linklist[0]),voice_client.loop)
            else:
                print("Queue is empty, disconnecting")
                voice_client.stop()
                alreadyran = False
                asyncio.run_coroutine_threadsafe(voice_client.disconnect(),voice_client.loop)
        else:
            print("Song still in queue")
            asyncio.run_coroutine_threadsafe(music(interaction,linklist[0]),voice_client.loop)





def convertfromseconds(duration):
    inthours = 0
    intminutes = 0
    intseconds = 0
    hours = ""
    minutes = ""
    seconds = ""
    if duration // 3600 >= 1:
        inthours = duration // 3600
        hours = f"{inthours} hours, " 
    
    if inthours != 0 and (duration - (inthours * 3600)) // 60 >= 1:
        intminutes = (duration - (inthours * 3600)) // 60
        minutes = f"{intminutes} minutes, "
    elif duration // 60 >= 1:
        intminutes = duration // 60
        minutes = f"{intminutes} minutes, "
    
    if intminutes != 0 and duration - (intminutes * 60) >= 1:
        intseconds = duration - (intminutes * 60)
        seconds = f"{intseconds} seconds."
    else:
        intseconds = duration
        seconds = f"{intseconds} seconds."

    return hours + minutes + seconds

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
            del userlist[position]
            await interaction.response.send_message("Removed: " + title)
        
    
    
    
    if option.lower() == "list":
        if len(songlist) == 0:
            await interaction.response.send_message("Queue is empty, try adding something!")
        else:
            # Using a list comprehension to format each line with a number and the element
            formatted_songs = [f"{index + 1}. {song}" for index, song in enumerate(songlist)]
            await interaction.response.send_message("Queue currently is:\n" + '\n'.join(formatted_songs))




bot.run(BOT_TOKEN)
