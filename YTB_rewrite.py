import yt_dlp.YoutubeDL, os, discord, datetime, asyncio
from yt_dlp.utils import download_range_func
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from config import BOT_TOKEN
userlist = []
linklist = []
songlist = []
idlemusiclist = []
ydl = yt_dlp.YoutubeDL

# Bot startup command
bot = commands.Bot(command_prefix="!", intents = discord.Intents.all())


def play_next(interaction, voice_client):
    print("Reached the end of song")
    del userlist[0]
    if not songlist and idlemusiclist:
        del idlemusiclist[0]
    elif songlist:
        del linklist [0]
        del songlist[0]
    if not songlist and idlemusiclist:
        asyncio.run_coroutine_threadsafe(play(interaction,idlemusiclist[0]))
    elif linklist:
        asyncio.run_coroutine_threadsafe(play(interaction,linklist[0]))
    else:
        asyncio.sleep(90)
        if not voice_client.is_playing():
            asyncio.run_coroutine_threadsafe(voice_client.disconnect(), voice_client.loop)
            asyncio.run_coroutine_threadsafe(interaction.message.send("No songs were played, timing out."), voice_client.loop)

async def get_info(query):
    if "youtube.com" not in query:
        # Search on youtube for the video
        search_results = ydl({'format': 'best'}).extract_info(f"ytsearch:{query}", download=False)
        # Get the first result
        first_result = search_results['entries'][0]
        # Get the url of the video
        query = first_result['webpage_url']
    # Info to be used for the embed
    print(f"Url is: {query}")
    info = ydl({'format': 'best'}).extract_info(query, download=False)
    file_size = info.get('filesize', None)
    if file_size is not None and file_size > 300 * 1024 * 1024:
        "The file size is too large. The download will be aborted."
    else:
        # Get the title from the info
        song_title = info['title']
        # Get the thumbnail url for the embed
        thumbnail_url = info.get('thumbnails', [{}])[0].get('url', '')
        # Get the duration
        duration = info.get('duration', 0)
        return query, song_title, thumbnail_url, duration

@bot.event
async def on_ready():
    print("Bot is Up and Ready!")
    try:
        # Try to sync all commands
        print("Trying to sync commands...")
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)     

@bot.tree.command(name="play", description="Play a song!")
@app_commands.describe(query = "Link or search term of the youtube video")
@app_commands.describe(start_time = "Start time (in seconds) of the song")
@app_commands.describe(end_time = "Time (in seconds) of the stop")
async def play(interaction: discord.Interaction, query: str, start_time: int = 0, end_time: int = 0):
    await interaction.response.defer()
    query, song_title, thumbnail_url, duration = await get_info(query)
    if end_time == 0:
        end_time = duration
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'MusicFiles/%(title)s.%(ext)s',
        'download_ranges': download_range_func(None, [(start_time, end_time)]),
        'force_keyframes_at_cuts': True,
        'noplaylist': True
    }
    # Defines the voice channel to connect to
    voice_client = interaction.guild.voice_client 
    print(f"Voice client is {voice_client}")
    if voice_client and voice_client.is_playing():
        if duration > 1200 and query not in idlemusiclist:
            idlemusiclist.append(query)
        if idlemusiclist and not songlist:
            # (Get the timestamp that was paused)
            voice_client.stop()
        else:
            userlist.append(interaction.user.id)
            linklist.append(query)
            songlist.append(song_title)
            await interaction.followup.send(f"Added `{song_title}` to the queue!")
    
    if duration > 1200 and query not in idlemusiclist:
        idlemusiclist.append(query)
        if not songlist:
            pass
    voice_state = interaction.user.voice
    print(f"Voice state is {voice_state}")
    if voice_client:
        if voice_client.is_playing():
            print("")
    else:
        # Check if the directory "MusicFiles" exists
        if not os.path.exists('MusicFiles'):
            # Make the MusicFiles directory
            os.makedirs('MusicFiles')
        # Using yt-dlp to download audio
        info = ydl(ydl_opts).extract_info(query, download=True)
        # Syntax the filename
        audio_filename = ydl(ydl_opts).prepare_filename(info)
        voice_channel = voice_state.channel
        if not voice_client:
            voice_client = await voice_channel.connect()
            print("Connected to vc")
        # Create and send an embed message with video details
        embed = discord.Embed(title=song_title, url=query, color=discord.Color.blue())
        embed.set_thumbnail(url=thumbnail_url)
        # Add a field for video duration
        embed.add_field(name="Duration:", value=str(datetime.timedelta(seconds=duration)), inline=False)  # Set inline to False for vertical alignment
        # Fetching the user
        userlist.append(interaction.user.id)
        print("Added user to list")
        embed.add_field(name="Requested by:", value=f"<@{userlist[0]}>", inline=True)
        print("Created embed")
        voice_client.play(discord.FFmpegPCMAudio(audio_filename), after=lambda e: play_next(interaction, voice_client))
        print("Playing music")
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="download", description="Download a song!")
@app_commands.describe(query = "Link or search term of the youtube video")
@app_commands.describe(format = "mp3 (audio) or mp4 (video)")
async def download(interaction: discord.Integration, query: str, format: str):
    await interaction.response.defer()
    if "youtube.com" not in query:
        # Search on youtube for the video
        search_results = ydl({'format': 'best'}).extract_info(f"ytsearch:{query}", download=False)
        # Get the first result
        first_result = search_results['entries'][0]
        # Get the url of the video
        query = first_result['webpage_url']
    ydl_opts = {
        'audio-format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'MusicFiles/%(title)s.%(ext)s',
        'noplaylist': True
    }
    # Using yt-dlp to download audio
    info = ydl(ydl_opts).extract_info(query, download=True)
    # Syntax the filename
    audio_filename = ydl(ydl_opts).prepare_filename(info)
    new_filename = audio_filename.rsplit('.', 1)[0] + '.mp3'
    await interaction.followup.send(file=discord.File(new_filename))


@play.error
async def play_error(ctx: commands.Context, error: commands.CommandError):
    embed = discord.Embed(title="Error", color=discord.Color.brand_red())
    embed.description = str(error)
    await ctx.followup.send(embed=embed)
    print(f"An error occurred :(\n{error}")





bot.run(BOT_TOKEN)