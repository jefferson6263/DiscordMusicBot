import asyncio
import discord
import os
import youtube_dl
from discord.voice_client import VoiceClient
import urllib.parse, urllib.request, re
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from token_1 import token



ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'yesplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', 
}

ffmpeg_options = {
    'options': '-vn'
}

song_queue = []

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

client = commands.Bot(
    command_prefix="!",
    intents=discord.Intents.all()
)



class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)




def check_queue(ctx):
    if song_queue != []:
        dic = song_queue.pop(0)
        player = dic["player"]
        voice_channel = ctx.message.guild.voice_client
        voice_channel.play(player, after=lambda e : check_queue(ctx))


@client.command(name='play', help='This command plays music')
async def play(ctx):
    voice = discord.utils.get(client.voice_clients, guild = ctx.message.guild)
    if not ctx.message.author.voice:
        await ctx.message.channel.send("You are not connected to a voice channel")
        return
    elif voice == None:
        channel = ctx.message.author.voice.channel
        await channel.connect()
    else:
        pass

    search = str(ctx.message.content)

    query_string = urllib.parse.urlencode({'search_query': search})
    htm_content = urllib.request.urlopen(
    'http://www.youtube.com/results?' + query_string)
    search_results = re.findall(r'/watch\?v=(.{11})',
                            htm_content.read().decode())
    url = 'http://www.youtube.com/watch?v=' + search_results[0]
    player = await YTDLSource.from_url(url, loop=client.loop)
    voice_channel = ctx.message.guild.voice_client

    r = requests.get(url)
    s = BeautifulSoup(r.text, "html.parser")
    title = str(s.head.title)
    
    title = title.replace("<title>", '')
    title = title.replace("</title>", '')

    try:
        playing = discord.Embed(
            title = "Now Playing",
            description = f"{title}"
        )
        voice_channel.play(player, after=lambda e : check_queue(ctx))
        await ctx.message.channel.send(embed = playing)
    except:
        dic = {
            "player": player,
            "title": title,
            "url": url
        }
        song_queue.append(dic)
        queued = discord.Embed(
            title = "Audio already playing",
            description = f"Added _{title}_ to queue"
        )
        await ctx.message.channel.send(embed = queued)


@client.command(name='pause', help='Pause the bot from palying music')
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild = ctx.message.guild)

    if voice == None:
        await ctx.message.channel.send("Bot is not connected to a Voice channel")
    elif voice.is_playing():
        voice.pause()
    else:
        await ctx.message.channel.send("No audio is being played ATM")

@client.command(name='unpause', help='Unpauses the bot')
async def unpause(ctx):
    voice = discord.utils.get(client.voice_clients, guild = ctx.message.guild)
    if voice == None:
        await ctx.message.channel.send("Bot is not connected to a Voice channel")
    elif voice.is_paused():
        voice.resume()
    else: 
        await ctx.message.channel.send("Audio is not paused")

@client.command(name='skip', help='skip current audio')
async def skip(ctx):
    voice = discord.utils.get(client.voice_clients, guild = ctx.message.guild)
    if voice == None:
        skip = discord.Embed(
            title = "No Audio is Being Played",
        )
        await ctx.message.channel.send(embed = skip)

    elif song_queue == []:
        skip = discord.Embed(
            title = "Skipping Current Audio",
            description = "No Audio is queued"
        )
        await ctx.message.channel.send(embed = skip)
        voice.stop()
    else: 
        Title = song_queue[0]["title"]
        url = song_queue[0]["url"]
        dic = song_queue.pop(0)
        queue = ""
        counter = 1

        for dic in song_queue:
            title = dic["title"]
            queue += f"{counter}. {title}\n"
            counter += 1

        skip = discord.Embed(
            title = "Skipping Current Audio",
            description = f"Now Playing\n{Title}\n{url}\n\nQueue:\n{queue}" 
        )
        await ctx.message.channel.send(embed = skip)
   
    
        
        player = dic["player"]
        voice_channel = ctx.message.guild.voice_client
        #need to stop client from playying audio first
        voice.pause()
        voice_channel.play(player, after=lambda e : check_queue(ctx))
    

@client.command(name='leave', help='Disconnects bot')
async def leave(ctx):
    voice = discord.utils.get(client.voice_clients, guild = ctx.message.guild)
    if voice == None:
        await ctx.message.channel.send("Bot is not connected to a Voice channel")
    else:
        await voice.disconnect()

@client.command(name='helpme', help='brings out help menu')
async def helpme(ctx):
    with open("helpmenu.txt") as f:
        print("test")

        messages = f.readlines()
        help_message = ""
        for line in messages:
            help_message += line
        f.close()
        await ctx.message.channel.send(help_message)
        
@client.command(name='sq', help='Shows the current queue')
async def sq(ctx):
    if song_queue == []:
        await ctx.message.channel.send('No Audio queued atm')
    else:
        await ctx.message.channel.send(song_queue)

@client.command(name='clear', help='clears musice queue')
async def clear(ctx):
    song_queue.clear()
    await ctx.message.channel.send('Music queue cleared')

@client.command(name='join',help='Bot joins voice channel')
async def join(ctx):
    voice = discord.utils.get(client.voice_clients, guild = ctx.message.guild)
    if not ctx.message.author.voice:
        await ctx.message.channel.send("You are not connected to a voice channel")
        return
    elif voice == None:
        channel = ctx.message.author.voice.channel
        await channel.connect()
    else:
        pass

print("Bot is running")

# hiding bot token
client.run(token)





    

