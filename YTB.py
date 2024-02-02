import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from config import BOT_TOKEN
import os
import yt_dlp
songlist = []
linklist = []
voters = []
voice_client = None
userlist = []
stoplist = []
callbacks = {}
ranalready = False


async def music(interaction, query):
    # This function is very unoptimized and am planning on optimizing it some other time
    # Some examples of this is when I get data on the video, it is called at least 4 times in this function and could be only called once, getting all the needed info, then running the logic with that info.
    # Processes that need to be repeated can also be put into separate functions and called upon
    # Global variables that are needed for logic
    global voice_client
    global ranalready
    global song_title
    global songlist
    # Gets the voice channel of the user 
    voice_state = interaction.user.voice
    print(f"Voice state is {voice_state}")
    # If the bot is in a channel and is playing in the channel
    if voice_client and voice_client.is_playing():
        print("Running song is playing logic")
        # Give message to the channel, saying that its adding a song to the queue
        await interaction.response.send_message("Song is already playing, adding to queue")
        # The following can be put into a separate function for optimization
        with yt_dlp.YoutubeDL() as ydl:
            # As long as its a valid youtube link
            if "youtube.com" in query:
                # Info to be used for the embed
                info = ydl.extract_info(query, download=False)
                # Parse only the title of the video
                song_title = info['title']
            # Else it will search the name on youtube
            else:
                # Search on youtube for the video
                search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
                # Get the first result
                first_result = search_results['entries'][0]
                # Get the url of the video
                query = first_result['webpage_url']
                # Get the title of the video
                song_title = first_result['title']
        # Add the user in the order of song order
        userlist.append(interaction.user.id)
        print("Added user to list")
        # Add the link on the queue list
        linklist.append(query)
        # Add the song title to the queue list
        songlist.append(song_title)
        print("Added link, song, and user")
        # Edit the message so it confirms the action
        await interaction.edit_original_response(content=f"Added `{song_title}` to queue")
    # If the bot isn't in vc or isn't playing music
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
            # This whole part can be optimized into another function
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # As long as its a valid youtube link
                if "youtube.com" in query:
                    # Get the info from the video
                    info = ydl.extract_info(query, download=False)
                    # Then get the filesize of the video from the info
                    file_size = info.get('filesize', None)
                # If the query doesn't have a youtube link
                else:
                    # This gets skipped for now because it would make it too bloated
                    file_size = None
                # If the filesize exists and is over 300MB (You can change this to allow more or less space)
                if file_size is not None and file_size > 300 * 1024 * 1024:  # Check if file size is over 300MB
                    # Notify the user that the file is too large to download
                    message = "The file size is too large. The download will be aborted."
                    await interaction.response.send_message(message)  
                # Else the download is small enough to download
                else:
                    # Runs yt-dlp to download the mp3 file if it's under the size limit
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # Remove yt_dlp cache to avoid problems
                        ydl.cache.remove()
                        # As long as its a valid youtube link
                        if "youtube.com" in query: 
                            print(f"Link is: {query}, downloading...")
                            # If it hasn't ran already
                            if ranalready == False:
                                # Send a response message
                                response_msg = await interaction.response.send_message('Downloading...')  # Send initial response
                            else:
                                # Else send a normal message
                                # If it tries to send a response message while one is already sent, it will error out
                                # Also this makes sure the video player is the most recent message
                                sent_message = await interaction.channel.send(content='Downloading...')
                                print("Send downloading message")
                            # Getting embed info
                            # Get the info for the video
                            info = ydl.extract_info(query, download=True)
                            # Syntax the filename
                            audio_filename = ydl.prepare_filename(info)
                            # Get the title from the info
                            song_title = info['title']
                            # Get the thumbnail url for the embed
                            thumbnail_url = info.get('thumbnails', [{}])[0].get('url', '')
                            # Get the duration
                            duration = info.get('duration', 0)
                        # Else search for the video
                        else:
                            if ranalready == False:
                                # If it hasn't ran already
                                response_msg = await interaction.response.send_message('Searching...')  # Send initial response
                                alreadyRan = False
                            else:
                                # Else send a normal message
                                # If it tries to send a response message while one is already sent, it will error out
                                # Also this makes sure the video player is the most recent message
                                await interaction.channel.send(content='Searching...')
                            # Search with the query
                            search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
                            # Only get the first result
                            first_result = search_results['entries'][0]
                            # Update the query so it has the url of the first result
                            query = first_result['webpage_url']
                            # Download the video as well as the video info
                            info = ydl.extract_info(query, download=True)
                            # Get the filename
                            audio_filename = ydl.prepare_filename(info)
                            # Parse only the song title
                            song_title = info['title']
                            # Get the thumbnail url for embed
                            thumbnail_url = info.get('thumbnails', [{}])[0].get('url', '')
                            # Get the duration of the video
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
                    userlist.append(interaction.user.id)
                    print("Added user to list")
                    embed.add_field(name="Requested by:", value=f"<@{userlist[0]}>", inline=True)
                    print("Created embed")
                    
                    # Convert the downloaded audio to WebM format using FFmpeg
                    # Play the converted audio file using FFmpeg
                    # When the audio stops, it triggers on_music_end which has post music logic
                    voice_client.play(discord.FFmpegPCMAudio(audio_filename), after=lambda e: on_music_end(song_title, voice_client, interaction, sent_message, e))
                    print("Playing music")
                    
                    async def pause(interaction):
                        # As long as the user is in a vc
                        if voice_client is not None:
                            # Pause all audio
                            voice_client.pause()
                            # Create a resume button
                            rbutton = Button(label="Resume", style=discord.ButtonStyle.green, emoji="▶️")
                            # Create a callback to resume once pressed
                            rbutton.callback = resume
                            # Clear all buttons
                            view.clear_items()
                            # Add the resume button
                            view.add_item(rbutton)
                            # Edit the message so it has the proper view (buttons)
                            await interaction.message.edit(view=view)
                            print("Paused")
                    async def resume(interaction):
                        # As long as the user is in a vc
                        if voice_client is not None:
                            # Resume all audio
                            voice_client.resume()
                            # Clear all buttons
                            view.clear_items()
                            # Add pause, stop, and skip button
                            view.add_item(pbutton)
                            view.add_item(sbutton)
                            view.add_item(skbutton)
                            # Edit the message restore the original view (buttons)
                            await interaction.message.edit(view=view)
                            print("Resumed")
                    async def skip(interaction):
                        # Call skiplogic
                        # This is required so that commands get called back and stop before executing anything else
                        await skiplogic(interaction)

                    async def skiplogic(interaction):
                        # As long as the user is in a vc
                        if voice_client is not None:
                            # If the user is not apart of the voters
                            if str(interaction.user) not in voters:
                                # Add the user to the voters list
                                voters.append(str(interaction.user))
                                # If the user that requested the skip requested the song
                                if interaction.user.id == userlist[0]:
                                    # Delete all voters from the list
                                    del voters[:]
                                    # Stop the audio, triggering on_music_end
                                    voice_client.stop()
                                    return
                                # If the # of people in the channel minus the bot is more than one
                                if len(voice_channel.members) - 1 > 1:
                                    # The number of votes needed is half the members in the vc
                                    votesNeeded = (len(voice_channel.members) - 1) // 2
                                    # If there are enough votes to skip
                                    if len(voters) >= votesNeeded:
                                        # Delete all voters from the list
                                        del voters[:]
                                        # Stop the audio, triggering on_music_end
                                        voice_client.stop()
                                        return
                                    # Else let them know that they have been added to the voters list and voted
                                    else:
                                        await interaction.channel.send(f"Voted! You have {str(len(voters))}/{str(int(votesNeeded))} votes")
                                # That means only one other person is in vc, and can safely be skipped
                                else:
                                    # Delete all voters from the list
                                    del voters[:]
                                    # Stop the audio, triggering on_music_end
                                    voice_client.stop()
                                    return
                            else:
                                # Else he is already a voter and cannot vote again
                                await interaction.channel.send("You already voted :x:")

                    async def stop(interaction):
                        # As long as the user is in a vc
                        if voice_client is not None:
                            # If the user already voted to stop
                            if interaction.user.id in stoplist:
                                await interaction.response.send_message("You already voted!")
                            # Getting the number of times a user is in the list
                            while interaction.user.id in userlist: 
                                numUserInQueue =+ 1
                            # If the user isn't in queue
                            if numUserInQueue == 0:
                                await interaction.response.send_message("You haven't requested anything :x:")
                            # If the userlist is more than one and there is at least one more person that has requested a song
                            elif len(userlist) > 1 and len(userlist) > numUserInQueue:
                                # Remove the user from the userlist
                                while interaction.user.id in userlist:
                                    userlist.remove(interaction.user.id)
                                # Then add the user to the stoplist
                                stoplist.append(interaction.user.id)
                                await interaction.response.send_message(f"Voted to stop! {len(stoplist)}/{len(userlist)+len(stoplist)} votes, {len(userlist)} are needed...")
                            # If nobody is playing anything or the number of votes is passed
                            if userlist[0] == interaction.user.id:
                                # Delete the message
                                await interaction.message.delete()
                                # Stop all audio
                                voice_client.stop()
                                print("Stopped music")
                    # Make pause, stop, and skip buttons
                    pbutton = Button(label="Pause", style=discord.ButtonStyle.gray, emoji="⏸️")
                    sbutton = Button(label="Stop", style=discord.ButtonStyle.red, emoji="⏹️")
                    skbutton = Button(label="Skip", style=discord.ButtonStyle.green, emoji="⏩")
                    # Link the buttons to callback functions
                    pbutton.callback = pause
                    sbutton.callback = stop
                    skbutton.callback = skip
                    # Create a variable for the view
                    view = View()
                    # Add the buttons to the view
                    view.add_item(pbutton)
                    view.add_item(sbutton)
                    view.add_item(skbutton)
                    print(f"Has it ran already? {ranalready}")
                    # If the bot hasn't ran already
                    if ranalready == False:
                        # Edit the response with the embed
                        await interaction.edit_original_response(content="", embed=embed, view=view)
                        # Set ran already to true
                        ranalready = True
                        # Store the original response
                        sent_message = await interaction.original_response()
                    else:
                        # Edit the new sent message with the embed
                        await sent_message.edit(content="", embed=embed, view=view)
                    
                    print("Edited message to display embed")
        # Else the user is not in vc
        else:
            await interaction.response.send_message("Your not in a vc")

def on_music_end(song_title, voice_client,interaction, sent_message, error):
        # Make sure the ranalready is global for resets
        global ranalready
        # Logging info
        print("Made it to music end")
        print(f"Songlist: {songlist}")
        print(f"Songtitle: {song_title}")
        print(f"Users in queue: {userlist}")
        # Delete the user from the userlist because the song ended
        del userlist[0]
        # Delete the original response
        asyncio.run_coroutine_threadsafe(sent_message.delete(),voice_client.loop)
        if error:
            print(f"Error during playback: {error}")
        # If the linklist is empty
        if len(linklist) == 0:
            print("Queue is empty, disconnecting")
            # Stop all audio
            voice_client.stop()
            # Reset ranalready
            ranalready = False
            # Disconnect from vc
            asyncio.run_coroutine_threadsafe(voice_client.disconnect(),voice_client.loop)
        # Else if the song_title was the one playing
        # This is because if someone requests for a song to be played, it only plays the video, but if its requested, the song title and link are stored
        elif song_title == songlist[0]:
            # Delete the first link and title
            del linklist[0]
            del songlist[0]
            print(f"Deleted {song_title} from the list")
            # If the songlist isn't empty
            if len(songlist) != 0:
                print("Still a song in queue, playing new song")
                # Play music function with the link as the query
                asyncio.run_coroutine_threadsafe(music(interaction,linklist[0]),voice_client.loop)
            # Else its empty and should disconnect
            else:
                print("Queue is empty, disconnecting")
                # Stop all audio
                voice_client.stop()
                # Reset ran already
                ranalready = False
                # Disconnect from queue
                asyncio.run_coroutine_threadsafe(voice_client.disconnect(),voice_client.loop)
        # If the linklist isn't empty and the song wasn't the one that already played
        else:
            print("Song still in queue")
            # Play music function with the link as the query
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
