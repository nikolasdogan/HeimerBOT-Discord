import config
import discord
import spotipy
import asyncio
import logging
import lavalink
import yt_dlp as youtube_dl
import imageio_ffmpeg as ffmpeg
from discord.ext import commands
from discord.ui import Button, View
from spotipy.oauth2 import SpotifyOAuth
from inc.ffmpeg_control import ffmpeg_if as ffm
from discord import FFmpegPCMAudio
import wavelink
from dotenv import load_dotenv
import os


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='//', intents=intents)


if ffm():
    # Spotify API client
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=config.SPOTIPY_CLIENT_ID,
        client_secret=config.SPOTIPY_CLIENT_SECRET,
        redirect_uri=config.SPOTIPY_REDIRECT_URI,
        scope="user-read-playback-state,user-modify-playback-state"
    ))
else:
    pass


@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    node = await wavelink.NodePool.create_node(bot=bot, host='localhost', port=2333, password='123456', region='us_central')
    print(f'Node bağlantı durumu: {node.is_connected()}')


@bot.command(name='katil')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'{channel} kanalına katıldım!')
    else:
        await ctx.send('Ses kanalında değilsiniz!')

@bot.command(name='ayril')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Ses kanalından ayrıldım!')
    else:
        await ctx.send('Herhangi bir ses kanalında değilim!')


@bot.command(name='oynat')
async def play(ctx, *, query):
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    player = wavelink.Player(ctx.voice_client)

    tracks = await wavelink.YouTubeTrack.search(query=query)
    if not tracks:
        return await ctx.send("Hiçbir şarkı bulunamadı!")

    await player.play(tracks[0])
    await ctx.send(f"{tracks[0].title} şarkısını çalıyorum!")

@bot.command(name='durdur')
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Çalma durduruldu!")
    else:
        await ctx.send("Çalınan bir şarkı yok!")


@bot.command(name='mesajsil')
async def clear_messages(ctx, amount: int):
    if amount <= 0:
        await ctx.send('Silmek istediğiniz mesaj sayısı pozitif olmalı!')
        return

    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for the command message itself
    await ctx.send(f'{len(deleted) - 1} mesaj başarıyla silindi!')

@bot.command(name='sustur')
@commands.has_permissions(manage_roles=True)
async def mute_member(ctx, member: discord.Member, duration: int, *, reason=None):
    muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
    if not muted_role:
        muted_role = await ctx.guild.create_role(name='Muted')

    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f'{member} kullanıcısı {duration} saniyeliğine susturuldu.')

    await asyncio.sleep(duration)
    await member.remove_roles(muted_role)
    await ctx.send(f'{member} kullanıcısının susturulması kaldırıldı.')

@bot.command(name='zamanasimi')
@commands.has_permissions(manage_messages=True)
async def apply_timeout(ctx, member: discord.Member, duration: int, *, reason=None):
    await ctx.guild.get_role(ROLE_ID).edit(permissions=discord.Permissions.none())
    await asyncio.sleep(duration)
    await ctx.guild.get_role(ROLE_ID).edit(permissions=discord.Permissions.all())
    await ctx.send(f'{member} kullanıcısına {duration} saniyeliğine zaman aşımı uygulandı.')

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban_user(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'{member} kullanıcısı yasaklandı.')

allowed_roles = ["⭐TESTER⭐", "🥈PiXeLiST🥈", "Mrs Pixelist"]
role_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']  # Emojiler rollerle aynı sırayla olmalı


@bot.command(name='rolver')
async def assign_role(ctx):
    # Rollerin numaralandırılmış halini gönder
    message_text = 'Lütfen aşağıdaki rollerden birini seçiniz:'
    for index, (role_name, emoji) in enumerate(zip(allowed_roles, role_emojis), start=1):
        message_text += f'\n{emoji} {index}. {role_name}'

    message = await ctx.send(message_text)

    # Roller için tepkileri ekle
    for emoji in role_emojis[:len(allowed_roles)]:  # Sadece izin verilen roller için tepki ekle
        await message.add_reaction(emoji)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return  # Botun kendi tepkilerini işleme almaması için

    guild = await bot.fetch_guild(payload.guild_id)
    member = await guild.fetch_member(payload.user_id)
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    # İzin verilen roller için tepkiye karşılık gelen rolü al
    for index, emoji in enumerate(role_emojis):
        if payload.emoji.name == emoji:
            selected_role_name = allowed_roles[index]

            selected_role = discord.utils.get(guild.roles, name=selected_role_name)
            if selected_role:
                try:
                    await member.add_roles(selected_role)
                    await message.delete()  # Mesajı sil
                    break  # Rol bulunduğunda döngüyü sonlandır
                except discord.Forbidden:
                    await member.send(f'Rol verme yetkiniz yok!')
                except discord.HTTPException:
                    await member.send('Bir hata oluştu, rol verilemedi.')

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return  # Botun kendi tepkilerini işleme almaması için

    guild = await bot.fetch_guild(payload.guild_id)
    member = await guild.fetch_member(payload.user_id)

    # İzin verilen roller için tepkiye karşılık gelen rolü kaldır
    for index, emoji in enumerate(role_emojis):
        if payload.emoji.name == emoji:
            selected_role_name = allowed_roles[index]

            selected_role = discord.utils.get(guild.roles, name=selected_role_name)
            if selected_role:
                try:
                    await member.remove_roles(selected_role)
                except discord.Forbidden:
                    await member.send(f'Rol kaldırma yetkiniz yok!')
                except discord.HTTPException:
                    await member.send('Bir hata oluştu, rol kaldırılamadı.')


@bot.event
async def on_error(event, *args, **kwargs):
    # Hataları loglamak için
    logging.error(f'Hata oluştu: {event}, {args}, {kwargs}')

@bot.event
async def on_command_error(ctx, error):
    # Komut hatalarını loglamak için
    logging.error(f'Komut hatası: {ctx.command} içinde {ctx.message.content}, {error}')
    await ctx.send(f'Bir hata oluştu: {error}')

bot.run(config.DISCORD_TOKEN)
