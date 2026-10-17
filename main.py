import os
import sys
import subprocess
import asyncio
import json
import random
import re
import base64
import io
from typing import Optional, List, Union
import datetime


def install_package(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])


required_packages = [
    "discord.py",
    "wavelink",
    "Pillow",
    "aiohttp",
    "aiosqlite",
]

for package in required_packages:
    if package == "discord.py":
        try:
            import discord  # noqa
        except ImportError:
            install_package("discord.py")
    elif package == "Pillow":
        try:
            import PIL  # noqa
        except ImportError:
            install_package("Pillow")
    else:
        install_package(package)

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import wavelink
import aiohttp

try:
    from music_database import MusicDatabase
except ImportError:
    class MusicDatabase:
        async def connect(self): pass
        async def close(self): pass
        async def register_server(self, *a, **k): pass
        async def register_voice_channel(self, *a, **k): pass
        async def log_music_play(self, *a, **k): pass
        async def log_search(self, *a, **k): pass


# ============================================================
# Emoji Configuration
# ============================================================
class EmojiConfig:
    def __init__(self):
        self.load_emojis()

    def load_emojis(self):
        try:
            with open("emoji_config.json", "r", encoding="utf-8") as f:
                emoji_data = json.load(f)

            self.PLAY = emoji_data["music_control"]["play"]
            self.PAUSE = emoji_data["music_control"]["pause"]
            self.RESUME = emoji_data["music_control"]["resume"]
            self.STOP = emoji_data["music_control"]["stop"]
            self.SKIP = emoji_data["music_control"]["skip"]
            self.PREVIOUS = emoji_data["music_control"]["previous"]
            self.REPEAT = emoji_data["music_control"]["repeat"]
            self.REPEAT_ONE = emoji_data["music_control"]["repeat_one"]
            self.SHUFFLE = emoji_data["music_control"]["shuffle"]
            self.VOLUME_UP = emoji_data["volume"]["volume_up"]
            self.VOLUME_DOWN = emoji_data["volume"]["volume_down"]
            self.VOLUME_MUTE = emoji_data["volume"]["volume_mute"]
            self.VOLUME_LOW = emoji_data["volume"]["volume_low"]
            self.VOLUME_HIGH = emoji_data["volume"]["volume_high"]
            self.SUCCESS = emoji_data["status"]["success"]
            self.ERROR = emoji_data["status"]["error"]
            self.WARNING = emoji_data["status"]["warning"]
            self.INFO = emoji_data["status"]["info"]
            self.LOADING = emoji_data["status"]["loading"]
            self.SEARCH = emoji_data["status"]["search"]
            self.SPOTIFY = emoji_data["music_sources"]["spotify"]
            self.YOUTUBE = emoji_data["music_sources"]["youtube"]
            self.SOUNDCLOUD = emoji_data["music_sources"]["soundcloud"]
            self.FILTER = emoji_data["features"]["filter"]
            self.EQUALIZER = emoji_data["features"]["equalizer"]
            self.HEADPHONES = emoji_data["features"]["headphones"]
            self.MICROPHONE = emoji_data["features"]["microphone"]
            self.MUSICAL_NOTE = emoji_data["features"]["musical_note"]
            self.MUSICAL_NOTES = emoji_data["features"]["musical_notes"]
            self.RADIO = emoji_data["features"]["radio"]
            self.STAR = emoji_data["features"]["star"]
            self.KEY = emoji_data["features"]["key"]
            self.QUALITY = emoji_data["features"]["quality"]
            self.YOUTUBE_PLATFORM = emoji_data["platforms"]["youtube_platform"]
            self.SOUNDCLOUD_PLATFORM = emoji_data["platforms"]["soundcloud_platform"]
            self.SETTINGS = emoji_data["control_panel"]["settings"]
            self.DASHBOARD = emoji_data["control_panel"]["dashboard"]
            self.QUEUE = emoji_data["control_panel"]["queue"]
            self.HISTORY = emoji_data["control_panel"]["history"]
            self.ADD = emoji_data["actions"]["add"]
            self.REMOVE = emoji_data["actions"]["remove"]
            self.CLEAR = emoji_data["actions"]["clear"]
            self.DOWNLOAD = emoji_data["actions"]["download"]
            self.UPLOAD = emoji_data["actions"]["upload"]
            self.CLOCK = emoji_data["time"]["clock"]
            self.HOURGLASS = emoji_data["time"]["hourglass"]
            self.TIMER = emoji_data["time"]["timer"]
            print("✅ Emojis loaded from emoji_config.json")
        except FileNotFoundError:
            print("⚠️ emoji_config.json not found, using default emojis")
            self.load_default_emojis()
        except Exception as e:
            print(f"⚠️ Error loading emojis: {e}, using defaults")
            self.load_default_emojis()

    def load_default_emojis(self):
        self.PLAY = "▶️"
        self.PAUSE = "⏸️"
        self.RESUME = "▶️"
        self.STOP = "⏹️"
        self.SKIP = "⏭️"
        self.PREVIOUS = "⏮️"
        self.REPEAT = "🔁"
        self.REPEAT_ONE = "🔂"
        self.SHUFFLE = "🔀"
        self.VOLUME_UP = "🔊"
        self.VOLUME_DOWN = "🔉"
        self.VOLUME_MUTE = "🔇"
        self.VOLUME_LOW = "🔈"
        self.VOLUME_HIGH = "🔊"
        self.SUCCESS = "✅"
        self.ERROR = "❌"
        self.WARNING = "⚠️"
        self.INFO = "ℹ️"
        self.LOADING = "⏳"
        self.SEARCH = "🔍"
        self.SPOTIFY = "🎧"
        self.YOUTUBE = "▶️"
        self.SOUNDCLOUD = "☁️"
        self.FILTER = "🎛️"
        self.EQUALIZER = "🎚️"
        self.HEADPHONES = "🎧"
        self.MICROPHONE = "🎤"
        self.MUSICAL_NOTE = "🎵"
        self.MUSICAL_NOTES = "🎶"
        self.RADIO = "📻"
        self.STAR = "⭐"
        self.KEY = "🔑"
        self.QUALITY = "💎"
        self.YOUTUBE_PLATFORM = "▶️"
        self.SOUNDCLOUD_PLATFORM = "☁️"
        self.SETTINGS = "⚙️"
        self.DASHBOARD = "📊"
        self.QUEUE = "📜"
        self.HISTORY = "📋"
        self.ADD = "➕"
        self.REMOVE = "➖"
        self.CLEAR = "🗑️"
        self.DOWNLOAD = "📥"
        self.UPLOAD = "📤"
        self.CLOCK = "🕒"
        self.HOURGLASS = "⏳"
        self.TIMER = "⏰"


# ============================================================
# YouTube API Manager
# ============================================================
class YouTubeAPIManager:
    def __init__(self, config_file="bot_config.json"):
        self.config_file = config_file
        self.api_key = None
        self.load_api_key()

    def load_api_key(self):
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
                self.api_key = config.get("youtube_api_key") or os.environ.get("YOUTUBE_API_KEY")
        except FileNotFoundError:
            self.api_key = os.environ.get("YOUTUBE_API_KEY")

    def save_config(self, config):
        existing = {}
        try:
            with open(self.config_file, "r") as f:
                existing = json.load(f)
        except FileNotFoundError:
            pass
        existing.update(config)
        with open(self.config_file, "w") as f:
            json.dump(existing, f, indent=4)

    def set_api_key(self, api_key):
        self.api_key = api_key
        self.save_config({"youtube_api_key": api_key})
        return True

    def get_api_key(self):
        return self.api_key

    def has_api_key(self):
        return bool(self.api_key and self.api_key.strip())


# ============================================================
# Fallback utility classes (used if core/utils not installed)
# ============================================================
try:
    from utils import Paginator, DescriptionEmbedPaginator  # noqa
    from core import Cog, axon, Context  # noqa
    from utils.Tools import *  # noqa
except ImportError:
    class Paginator:
        def __init__(self, source, ctx):
            self.source = source
            self.ctx = ctx

        async def paginate(self):
            await self.ctx.send("Paginator not available - showing first page only")
            entries = self.source.entries[:10]
            embed = discord.Embed(
                title=self.source.title,
                description="\n".join(entries),
                color=self.source.color
            )
            await self.ctx.send(embed=embed)

    class DescriptionEmbedPaginator:
        def __init__(self, entries, title, description, per_page, color):
            self.entries = entries
            self.title = title
            self.description = description
            self.per_page = per_page
            self.color = color

    class Cog(commands.Cog):
        pass

    class axon(commands.Bot):
        pass

    class Context(commands.Context):
        pass

    def blacklist_check():
        def predicate(ctx):
            return True
        return commands.check(predicate)

    def ignore_check():
        def predicate(ctx):
            return True
        return commands.check(predicate)


# ============================================================
# Global state
# ============================================================
track_histories: dict[int, list] = {}
active_player_messages: dict[int, discord.Message] = {}
user_playlists: dict[int, dict[str, list[dict]]] = {}

youtube_api = YouTubeAPIManager()

SPOTIFY_TRACK_REGEX = r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)"
SPOTIFY_PLAYLIST_REGEX = r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
SPOTIFY_ALBUM_REGEX = r"https?://open\.spotify\.com/album/([a-zA-Z0-9]+)"


# ============================================================
# Spotify API
# ============================================================
class SpotifyAPI:
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: Optional[str] = None

    async def get_token(self):
        auth_url = "https://accounts.spotify.com/api/token"
        auth_value = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("utf-8")
        headers = {"Authorization": f"Basic {auth_value}"}
        data = {"grant_type": "client_credentials"}
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, headers=headers, data=data) as response:
                text = await response.text()
                if response.status != 200:
                    raise Exception(f"Failed to fetch token: {response.status}, {text}")
                result = await response.json()
                self.token = result.get("access_token")

    async def get(self, endpoint: str, params: Optional[dict] = None):
        retries = 2
        for attempt in range(retries):
            if not self.token or attempt > 0:
                await self.get_token()

            url = f"{self.BASE_URL}/{endpoint}"
            headers = {"Authorization": f"Bearer {self.token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 401 and attempt < retries - 1:
                        continue
                    elif response.status != 200:
                        raise Exception(
                            f"Failed to fetch data from Spotify: {response.status}"
                        )
                    return await response.json()
        raise Exception("Exceeded max retries to fetch Spotify data")

    async def get_track(self, track_id: str):
        return await self.get(f"tracks/{track_id}")

    async def get_playlist(self, playlist_id: str):
        return await self.get(f"playlists/{playlist_id}")


# Load Spotify credentials
try:
    with open("bot_config.json", "r") as f:
        _cfg = json.load(f)
    spotify_client_id = _cfg.get("spotify_client_id") or os.environ.get("SPOTIFY_CLIENT_ID")
    spotify_client_secret = _cfg.get("spotify_client_secret") or os.environ.get("SPOTIFY_CLIENT_SECRET")
except FileNotFoundError:
    spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

if not spotify_client_id or not spotify_client_secret:
    print("⚠️ WARNING: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET not set")
    spotify_api: Optional[SpotifyAPI] = None
else:
    spotify_api = SpotifyAPI(spotify_client_id, spotify_client_secret)
    print("✅ Spotify API initialized successfully")


# ============================================================
# Helpers
# ============================================================
def format_duration(ms: int) -> str:
    sec = ms // 1000
    return f"{sec // 60}:{sec % 60:02d}"


def source_from_uri(uri: str) -> tuple[str, str]:
    """Return (emoji, name) for track uri."""
    e = EmojiConfig()
    uri_lower = (uri or "").lower()
    if "spotify" in uri_lower:
        return e.SPOTIFY, "Spotify"
    if "youtube" in uri_lower or "youtu" in uri_lower:
        return e.YOUTUBE, "YouTube"
    if "soundcloud" in uri_lower:
        return e.SOUNDCLOUD, "SoundCloud"
    return e.MUSICAL_NOTE, "Unknown"


def get_player(ctx: commands.Context) -> Optional[wavelink.Player]:
    return ctx.voice_client  # type: ignore


def is_user_in_player_channel(ctx: commands.Context, player: wavelink.Player) -> bool:
    if not ctx.author.voice or not ctx.author.voice.channel:
        return False
    return ctx.author.voice.channel.id == player.channel.id


# ============================================================
# Music Control View
# ============================================================
class UltraAdvancedMusicControlView(View):
    def __init__(self, player: wavelink.Player, ctx: commands.Context):
        super().__init__(timeout=300)
        self.player = player
        self.ctx = ctx
        self.emoji = EmojiConfig()
        self._build()

    def _build(self):
        # Row 1: Playback
        self.add_item(Button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="music_previous"))
        self.add_item(Button(emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="music_pause_resume"))
        self.add_item(Button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music_stop"))
        self.add_item(Button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="music_skip"))
        self.add_item(Button(emoji="🔄", style=discord.ButtonStyle.secondary, custom_id="music_replay"))

        # Row 2: Seek & Speed
        self.add_item(Button(emoji="⏪", style=discord.ButtonStyle.secondary, custom_id="music_rewind"))
        self.add_item(Button(emoji="🐌", style=discord.ButtonStyle.secondary, custom_id="music_speed_075"))
        self.add_item(Button(emoji="⏲️", style=discord.ButtonStyle.primary, custom_id="music_seek_menu"))
        self.add_item(Button(emoji="⚡", style=discord.ButtonStyle.secondary, custom_id="music_speed_125"))
        self.add_item(Button(emoji="⏩", style=discord.ButtonStyle.secondary, custom_id="music_forward"))

        # Row 3: Volume & Loop
        self.add_item(Button(emoji="🔇", style=discord.ButtonStyle.secondary, custom_id="music_mute"))
        self.add_item(Button(emoji="🔉", style=discord.ButtonStyle.primary, custom_id="music_vol_down"))
        self.add_item(Button(emoji="🔁", style=discord.ButtonStyle.success, custom_id="music_loop"))
        self.add_item(Button(emoji="🔊", style=discord.ButtonStyle.primary, custom_id="music_vol_up"))
        self.add_item(Button(emoji="🔂", style=discord.ButtonStyle.success, custom_id="music_loop_track"))

        # Row 4: Queue
        self.add_item(Button(emoji="📜", style=discord.ButtonStyle.secondary, custom_id="music_show_queue"))
        self.add_item(Button(emoji="🔀", style=discord.ButtonStyle.success, custom_id="music_shuffle"))
        self.add_item(Button(emoji="🎵", style=discord.ButtonStyle.primary, custom_id="music_add_track"))
        self.add_item(Button(emoji="💾", style=discord.ButtonStyle.success, custom_id="music_save_playlist"))
        self.add_item(Button(emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="music_clear_queue"))

        # Row 5: Effects & Info
        self.add_item(Button(emoji="🎛️", style=discord.ButtonStyle.secondary, custom_id="music_filter_menu"))
        self.add_item(Button(emoji="🧹", style=discord.ButtonStyle.danger, custom_id="music_clear_effects"))
        self.add_item(Button(emoji="📊", style=discord.ButtonStyle.primary, custom_id="music_stats"))
        self.add_item(Button(emoji="💎", style=discord.ButtonStyle.success, custom_id="music_quality_info"))
        self.add_item(Button(emoji="🔧", style=discord.ButtonStyle.secondary, custom_id="music_settings"))

        for item in self.children:
            if isinstance(item, Button):
                item.callback = self.button_callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        player = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Player Not Active",
                    description="I'm not currently in a voice channel.",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
            return False
        if interaction.user in player.channel.members:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.ERROR} Permission Denied",
                description="Only members in the same voice channel can control the player.",
                color=0xFF0000,
            ),
            ephemeral=True,
        )
        return False

    async def button_callback(self, interaction: discord.Interaction):
        button_id = interaction.data["custom_id"].replace("music_", "")
        actions = {
            "pause_resume": self.pause_resume,
            "skip": self.skip,
            "previous": self.previous,
            "rewind": self.rewind,
            "forward": self.forward,
            "loop": self.loop,
            "shuffle": self.shuffle,
            "vol_down": self.volume_down,
            "vol_up": self.volume_up,
            "filter_menu": self.filter_menu,
            "show_queue": self.show_queue,
            "clear_queue": self.clear_queue,
            "save_playlist": self.save_playlist,
            "stop": self.stop,
            "speed_075": self.speed_075,
            "speed_125": self.speed_125,
            "loop_track": self.loop_track,
            "replay": self.replay,
            "stats": self.stats,
            "quality_info": self.quality_info,
            "mute": self.mute,
            "seek_menu": self.seek_menu,
            "add_track": self.add_track,
            "settings": self.settings,
            "clear_effects": self.clear_effects,
        }
        if button_id in actions:
            try:
                await actions[button_id](interaction)
            except Exception as e:
                print(f"Button callback error ({button_id}): {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title=f"{self.emoji.ERROR} Error",
                            description=f"An error occurred: {str(e)}",
                            color=0xFF0000,
                        ),
                        ephemeral=True,
                    )

    async def pause_resume(self, interaction):
        p = interaction.guild.voice_client
        if not p or not (p.playing or p.paused):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        if p.paused:
            await p.pause(False)
            embed = discord.Embed(
                title=f"{self.emoji.SUCCESS} Playback Resumed",
                description=f"**{p.current.title}** has been resumed!",
                color=0x1DB954,
            )
        else:
            await p.pause(True)
            embed = discord.Embed(
                title=f"{self.emoji.PAUSE} Playback Paused",
                description=f"**{p.current.title}** has been paused!",
                color=0xFFA500,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def skip(self, interaction):
        p = interaction.guild.voice_client
        if not p or not p.playing:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        await p.stop()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.SKIP} Track Skipped",
                description=f"Skipped by **{interaction.user.display_name}**!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def previous(self, interaction):
        p = interaction.guild.voice_client
        guild_id = interaction.guild.id
        if p and guild_id in track_histories and track_histories[guild_id]:
            prev = track_histories[guild_id].pop()
            await p.play(prev)
            embed = discord.Embed(
                title=f"{self.emoji.PREVIOUS} Playing Previous Track",
                description=f"**{prev.title}**",
                color=0x1DB954,
            )
        else:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Previous Track",
                description="There's no previous track in history!",
                color=0xFF0000,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def rewind(self, interaction):
        p = interaction.guild.voice_client
        if not p or not p.playing:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        new_pos = max(0, p.position - 30000)
        await p.seek(new_pos)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏪ Rewinded",
                description=f"Rewinded 30 seconds in **{p.current.title}**!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def forward(self, interaction):
        p = interaction.guild.voice_client
        if not p or not p.playing:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        new_pos = min(p.current.length, p.position + 30000)
        await p.seek(new_pos)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏩ Forwarded",
                description=f"Forwarded 30 seconds in **{p.current.title}**!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def loop(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        p.queue.mode = (
            wavelink.QueueMode.loop
            if p.queue.mode != wavelink.QueueMode.loop
            else wavelink.QueueMode.normal
        )
        mode = "enabled" if p.queue.mode == wavelink.QueueMode.loop else "disabled"
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.REPEAT} Loop {mode.title()}",
                description=f"Loop mode has been **{mode}**!",
                color=0x1DB954 if mode == "enabled" else 0xFFA500,
            ),
            ephemeral=True,
        )

    async def shuffle(self, interaction):
        p = interaction.guild.voice_client
        if p and p.queue and not p.queue.is_empty:
            queue_list = list(p.queue)
            random.shuffle(queue_list)
            p.queue.clear()
            for track in queue_list:
                p.queue.put(track)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.SHUFFLE} Queue Shuffled",
                    description="Queue has been shuffled!",
                    color=0x1DB954,
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Queue Empty",
                    description="The queue is currently empty!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )

    async def volume_down(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        cur = p.volume
        new = max(0, cur - 20)
        await p.set_volume(new)
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.VOLUME_DOWN} Volume Decreased",
                description=f"Volume: `{cur}%` → `{new}%`",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def volume_up(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        cur = p.volume
        new = min(200, cur + 20)
        await p.set_volume(new)
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.VOLUME_UP} Volume Increased",
                description=f"Volume: `{cur}%` → `{new}%`",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def filter_menu(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.FILTER} Audio Filters",
                description="Select an audio filter to apply:",
                color=0x1DB954,
            ),
            view=FilterSelectView(self.ctx),
            ephemeral=True,
        )

    async def show_queue(self, interaction):
        p = interaction.guild.voice_client
        if not p or not p.queue or p.queue.is_empty:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.QUEUE} Queue Empty",
                    description="The queue is currently empty!",
                    color=0xFFA500,
                ),
                ephemeral=True,
            )
        tracks = list(p.queue)[:10]
        text = "\n".join(f"`{i+1}.` **{t.title[:40]}**" for i, t in enumerate(tracks))
        embed = discord.Embed(
            title=f"{self.emoji.QUEUE} Current Queue",
            description=text,
            color=0x1DB954,
        )
        if len(p.queue) > 10:
            embed.set_footer(text=f"And {len(p.queue)-10} more tracks...")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def clear_queue(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        if p.queue.is_empty:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.WARNING} Queue Already Empty",
                    description="The queue is already empty!",
                    color=0xFFA500,
                ),
                ephemeral=True,
            )
        c = len(p.queue)
        p.queue.clear()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.CLEAR} Queue Cleared",
                description=f"Cleared `{c}` tracks!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def save_playlist(self, interaction):
        p = interaction.guild.voice_client
        if not p or p.queue.is_empty:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Queue Empty",
                    description="There are no tracks in the queue to save!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                title="💾 Save Playlist",
                description="Save the current queue as a playlist:",
                color=0x1DB954,
            ),
            view=PlaylistSaveView(p.queue, interaction.user.id),
            ephemeral=True,
        )

    async def stop(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        guild_id = interaction.guild.id
        if guild_id in active_player_messages:
            try:
                await active_player_messages[guild_id].delete()
                del active_player_messages[guild_id]
            except Exception:
                pass
        await p.disconnect()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.STOP} Playback Stopped",
                description="Music playback has been stopped!",
                color=0x1DB954,
            )
        )

    async def speed_075(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        filters = wavelink.Filters()
        filters.timescale.set(speed=0.75)
        await p.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🐌 Playback Speed Set",
                description="Playback speed set to **0.75x**",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def speed_125(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        filters = wavelink.Filters()
        filters.timescale.set(speed=1.25)
        await p.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⚡ Playback Speed Set",
                description="Playback speed set to **1.25x**",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def clear_effects(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        await p.set_filters(wavelink.Filters())
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🧹 All Effects Cleared",
                description="All audio filters and effects have been removed!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def loop_track(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        p.queue.mode = (
            wavelink.QueueMode.loop_all
            if p.queue.mode != wavelink.QueueMode.loop_all
            else wavelink.QueueMode.normal
        )
        mode = "enabled" if p.queue.mode == wavelink.QueueMode.loop_all else "disabled"
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"🔂 Track Loop {mode.title()}",
                description=f"Current track loop has been **{mode}**!",
                color=0x1DB954 if mode == "enabled" else 0xFFA500,
            ),
            ephemeral=True,
        )

    async def replay(self, interaction):
        p = interaction.guild.voice_client
        if not p or not p.playing:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        await p.seek(0)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔄 Replaying Track",
                description=f"Restarting **{p.current.title}**!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def stats(self, interaction):
        p = interaction.guild.voice_client
        if not p or not p.current:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Track",
                    description="No track is currently playing!",
                    color=0xFF0000,
                ),
                ephemeral=True,
            )
        pos = p.position / 1000
        length = p.current.length / 1000
        pct = (pos / length * 100) if length > 0 else 0
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📊 Player Statistics",
                description=(
                    f"**Now Playing:** {p.current.title}\n"
                    f"**Progress:** {pct:.1f}%\n"
                    f"**Volume:** {p.volume}%\n"
                    f"**Queue:** {len(p.queue)} tracks"
                ),
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def quality_info(self, interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="💎 Audio Quality",
                description=(
                    "**Bitrate:** 320 kbps\n"
                    "**Sample Rate:** 48 kHz\n"
                    "**Channels:** Stereo (2.0)\n"
                    "**Codec:** Opus"
                ),
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def mute(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        if not hasattr(p, "_pre_mute_volume"):
            p._pre_mute_volume = p.volume
            await p.set_volume(0)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔇 Muted",
                    description="Player has been muted!",
                    color=0x1DB954,
                ),
                ephemeral=True,
            )
        else:
            await p.set_volume(p._pre_mute_volume)
            delattr(p, "_pre_mute_volume")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔊 Unmuted",
                    description="Player has been unmuted!",
                    color=0x1DB954,
                ),
                ephemeral=True,
            )

    async def seek_menu(self, interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏲️ Seek Controls",
                description="Use the ⏪ (30s back) and ⏩ (30s forward) buttons to seek!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def add_track(self, interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🎵 Add Track",
                description="Use `/play <song name>` to add tracks!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )

    async def settings(self, interaction):
        p = interaction.guild.voice_client
        if not p:
            return
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔧 Player Settings",
                description=(
                    f"• Volume: {p.volume}%\n"
                    f"• Loop: {p.queue.mode.name}\n"
                    f"• Queue Size: {len(p.queue)} tracks"
                ),
                color=0x1DB954,
            ),
            ephemeral=True,
        )


# ============================================================
# Filter Select View
# ============================================================
class FilterSelectView(View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.emoji = EmojiConfig()

    @discord.ui.select(
        placeholder="🎛️ Select Audio Filter...",
        options=[
            discord.SelectOption(label="Nightcore", description="Increase pitch and speed", emoji="🎵", value="nightcore"),
            discord.SelectOption(label="Bass Boost", description="Enhance bass frequencies", emoji="🔊", value="bassboost"),
            discord.SelectOption(label="Vaporwave", description="Slow down and pitch down", emoji="🌴", value="vaporwave"),
            discord.SelectOption(label="Karaoke", description="Remove vocal frequencies", emoji="🎤", value="karaoke"),
            discord.SelectOption(label="Tremolo", description="Amplitude modulation effect", emoji="🎛️", value="tremolo"),
            discord.SelectOption(label="Vibrato", description="Pitch modulation effect", emoji="🎶", value="vibrato"),
            discord.SelectOption(label="Rotation", description="3D rotation effect", emoji="🔄", value="rotation"),
            discord.SelectOption(label="Distortion", description="Add distortion effect", emoji="🎸", value="distortion"),
            discord.SelectOption(label="Clear Filters", description="Remove all filters", emoji="🧹", value="clear"),
        ],
    )
    async def select_filter(self, interaction: discord.Interaction, select: Select):
        p = interaction.guild.voice_client
        if not p:
            return await interaction.response.send_message(
                "I'm not connected to a voice channel.", ephemeral=True
            )
        name = select.values[0]
        filters = wavelink.Filters()
        if name == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1.0)
            desc = "Applied Nightcore filter!"
        elif name == "bassboost":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.8}, {"band": 1, "gain": 0.6},
                {"band": 2, "gain": 0.4}, {"band": 3, "gain": 0.2},
                {"band": 4, "gain": 0.1}, {"band": 5, "gain": 0.0},
            ])
            desc = "Applied Bass Boost!"
        elif name == "vaporwave":
            filters.timescale.set(rate=0.8, pitch=0.9)
            desc = "Applied Vaporwave filter!"
        elif name == "karaoke":
            filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
            desc = "Applied Karaoke filter!"
        elif name == "tremolo":
            filters.tremolo.set(depth=0.5, frequency=10.0)
            desc = "Applied Tremolo effect!"
        elif name == "vibrato":
            filters.vibrato.set(depth=0.5, frequency=5.0)
            desc = "Applied Vibrato effect!"
        elif name == "rotation":
            filters.rotation.set(rotation_hz=0.2)
            desc = "Applied Rotation effect!"
        elif name == "distortion":
            filters.distortion.set(
                sin_offset=0.0, sin_scale=1.0,
                cos_offset=0.0, cos_scale=1.0,
                tan_offset=0.0, tan_scale=1.0,
                offset=0.0, scale=1.0,
            )
            desc = "Applied Distortion effect!"
        else:
            filters = wavelink.Filters()
            desc = "All audio filters have been cleared!"

        await p.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.FILTER} Filter Applied",
                description=desc,
                color=0x1DB954,
            ),
            ephemeral=True,
        )


# ============================================================
# Playlist Save View & Modal
# ============================================================
class PlaylistSaveView(View):
    def __init__(self, queue, user_id: int):
        super().__init__(timeout=60)
        self.queue = queue
        self.user_id = user_id

    @discord.ui.button(label="Save Queue as Playlist", style=discord.ButtonStyle.success, emoji="💾")
    async def save_queue(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SaveQueueModal(self.queue, self.user_id))


class SaveQueueModal(discord.ui.Modal, title="Save Queue as Playlist"):
    name = discord.ui.TextInput(
        label="Playlist Name",
        placeholder="My Queue Playlist",
        required=True,
        max_length=50,
    )

    def __init__(self, queue, user_id: int):
        super().__init__()
        self.queue = queue
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        playlist_name = self.name.value
        if self.user_id not in user_playlists:
            user_playlists[self.user_id] = {}
        queue_tracks = list(self.queue)
        user_playlists[self.user_id][playlist_name] = [
            {"title": t.title, "uri": t.uri, "author": t.author} for t in queue_tracks
        ]
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Playlist Saved",
                description=f"Saved **{len(queue_tracks)}** tracks to **{playlist_name}**!",
                color=0x1DB954,
            ),
            ephemeral=True,
        )


# ============================================================
# Platform Select + Search Results
# ============================================================
class PlatformSelectView(View):
    def __init__(self, ctx: commands.Context, query: str):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.query = query
        self.emoji = EmojiConfig()

        yt_button = Button(label="YouTube", emoji="▶️", style=discord.ButtonStyle.danger)
        yt_button.callback = self._make_cb("ytsearch", "YouTube")
        self.add_item(yt_button)

        sc_button = Button(label="SoundCloud", emoji="☁️", style=discord.ButtonStyle.primary)
        sc_button.callback = self._make_cb("scsearch", "SoundCloud")
        self.add_item(sc_button)

    def _make_cb(self, source: str, name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title=f"{self.emoji.ERROR} Permission Denied",
                        description="Only the command author can select a platform.",
                        color=0xFF0000,
                    ),
                    ephemeral=True,
                )
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.SEARCH} Searching...",
                    description=f"Searching for `{self.query}` on {name}...",
                    color=0x1DB954,
                ),
                ephemeral=True,
            )
            await self._perform_search(source, name)
            try:
                await interaction.message.delete()
            except Exception:
                pass
        return callback

    async def _perform_search(self, source: str, name: str):
        try:
            # wavelink 3.x: source must be prefixed in the query string
            results = await wavelink.Playable.search(f"{source}:{self.query}")
        except Exception as e:
            return await self.ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Search Error",
                    description=f"An error occurred: {e}",
                    color=0xFF0000,
                )
            )
        if not results:
            return await self.ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Results Found",
                    description=f"No results found for `{self.query}` on {name}.",
                    color=0xFF0000,
                )
            )
        if isinstance(results, wavelink.Playlist):
            top = results.tracks[:5]
        else:
            top = results[:5]

        embed = discord.Embed(
            title=f"{self.emoji.SEARCH} Search Results - {name}",
            description=f"Top 5 results for `{self.query}`:",
            color=0x1DB954,
        )
        for i, t in enumerate(top, 1):
            embed.add_field(
                name=f"{i}. {t.title[:50]}",
                value=f"**Artist:** {t.author[:40]}\n**Duration:** {format_duration(t.length)}",
                inline=False,
            )
        await self.ctx.send(embed=embed, view=SearchResultView(self.ctx, top))


class SearchResultView(View):
    def __init__(self, ctx: commands.Context, results: list):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.results = results
        self.emoji = EmojiConfig()
        for i in range(min(5, len(results))):
            btn = Button(label=str(i + 1), style=discord.ButtonStyle.primary)
            btn.callback = self._make_cb(i)
            self.add_item(btn)

    def _make_cb(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title=f"{self.emoji.ERROR} Permission Denied",
                        description="Only the command author can select a track.",
                        color=0xFF0000,
                    ),
                    ephemeral=True,
                )
            track = self.results[index]
            vc = self.ctx.voice_client

            if not vc:
                if not self.ctx.author.voice:
                    return await interaction.response.send_message(
                        embed=discord.Embed(
                            title=f"{self.emoji.ERROR} Voice Channel Required",
                            description="You need to be in a voice channel.",
                            color=0xFF0000,
                        ),
                        ephemeral=True,
                    )
                vc = await self.ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(100)
            vc.ctx = self.ctx

            if not vc.playing:
                await vc.play(track)
                embed = discord.Embed(
                    title=f"{self.emoji.MUSICAL_NOTE} Now Playing",
                    description=f"**{track.title}** by **{track.author}**",
                    color=0x1DB954,
                )
                await interaction.response.send_message(embed=embed)
                music_cog = self.ctx.bot.get_cog("Music")
                if music_cog:
                    await music_cog.display_player_embed(vc, track, self.ctx)
            else:
                await vc.queue.put_wait(track)
                embed = discord.Embed(
                    title=f"{self.emoji.ADD} Added to Queue",
                    description=f"**{track.title}** by **{track.author}**",
                    color=0x1DB954,
                )
                embed.set_footer(text=f"Position in queue: {len(vc.queue)}")
                await interaction.response.send_message(embed=embed)
        return callback


# ============================================================
# Music Cog
# ============================================================
class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.inactivity_timeout = 120
        self.emoji = EmojiConfig()
        self._inactivity_task: Optional[asyncio.Task] = None
        self._monitor_running = False

    async def cog_load(self):
        await self.connect_nodes()
        if not self._monitor_running:
            self._monitor_running = True
            self._inactivity_task = asyncio.create_task(self._monitor_inactivity())

    def cog_unload(self):
        if self._inactivity_task:
            self._inactivity_task.cancel()

    async def connect_nodes(self):
        try:
            lavalink_uri = None
            lavalink_password = None
            try:
                with open("bot_config.json", "r") as f:
                    cfg = json.load(f)
                lavalink_uri = cfg.get("lavalink_uri") or os.environ.get("LAVALINK_URI")
                lavalink_password = cfg.get("lavalink_password") or os.environ.get("LAVALINK_PASSWORD")
            except FileNotFoundError:
                lavalink_uri = os.environ.get("LAVALINK_URI")
                lavalink_password = os.environ.get("LAVALINK_PASSWORD")

            if not lavalink_uri or not lavalink_password:
                print("⚠️ WARNING: LAVALINK_URI and LAVALINK_PASSWORD not set")
                lavalink_uri = "https://lava-v4.ajieblogs.eu.org:443/"
                lavalink_password = "https://dsc.gg/ajidevserver"

            nodes = [wavelink.Node(uri=lavalink_uri, password=lavalink_password)]
            await wavelink.Pool.connect(nodes=nodes, client=self.client, cache_capacity=None)
            print("🎵 Successfully connected to Lavalink node")
        except Exception as e:
            print(f"❌ Failed to connect to Lavalink: {e}")

    async def _monitor_inactivity(self):
        while True:
            try:
                await asyncio.sleep(60)
                for guild in list(self.client.guilds):
                    await self._check_inactivity(guild)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"inactivity monitor error: {e}")

    async def _check_inactivity(self, guild: discord.Guild):
        player: Optional[wavelink.Player] = guild.voice_client  # type: ignore
        if player and player.playing and len(player.channel.members) == 1:
            await asyncio.sleep(self.inactivity_timeout)
            if player.is_connected() and len(player.channel.members) == 1:
                ctx = getattr(player, "ctx", None)
                await player.disconnect(force=True)
                if ctx:
                    try:
                        await ctx.channel.send(
                            embed=discord.Embed(
                                title=f"{self.emoji.WARNING} Inactivity Timeout",
                                description="I've been disconnected due to inactivity.",
                                color=0xFFA500,
                            )
                        )
                    except Exception:
                        pass

    async def _delete_later(self, message: discord.Message, delay: float):
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:
            pass

    async def _log_track_play(self, ctx: commands.Context, track):
        try:
            db = getattr(self.client, "music_db", None)
            if not db:
                return
            await db.register_server(ctx.guild.id, ctx.guild.name)
            if ctx.author.voice and ctx.author.voice.channel:
                await db.register_voice_channel(
                    ctx.author.voice.channel.id,
                    ctx.guild.id,
                    ctx.author.voice.channel.name,
                )
                uri_lower = (track.uri or "").lower()
                source = "youtube"
                if "spotify" in uri_lower:
                    source = "spotify"
                elif "soundcloud" in uri_lower:
                    source = "soundcloud"
                await db.log_music_play(
                    server_id=ctx.guild.id,
                    channel_id=ctx.author.voice.channel.id,
                    user_id=ctx.author.id,
                    user_name=str(ctx.author),
                    track_title=track.title,
                    track_author=track.author,
                    track_uri=track.uri,
                    track_duration=track.length // 1000,
                    track_source=source,
                )
        except Exception as e:
            print(f"❌ Database logging error: {e}")

    async def _log_search(self, ctx: commands.Context, query: str, results_count: int):
        try:
            db = getattr(self.client, "music_db", None)
            if not db:
                return
            await db.register_server(ctx.guild.id, ctx.guild.name)
            await db.log_search(
                server_id=ctx.guild.id,
                user_id=ctx.author.id,
                user_name=str(ctx.author),
                search_query=query,
                results_count=results_count,
            )
        except Exception as e:
            print(f"❌ Search logging error: {e}")

    async def display_player_embed(self, player: wavelink.Player, track, ctx: commands.Context, autoplay: bool = False):
        try:
            if hasattr(player, "_autoplay_only") and player._autoplay_only:
                embed = discord.Embed(
                    title=f"{self.emoji.MUSICAL_NOTES} Now Playing - 24/7 Autoplay",
                    description=f"**{track.title}**\nby **{track.author}**",
                    color=0x1DB954,
                )
                if getattr(track, "artwork", None):
                    embed.set_thumbnail(url=track.artwork)
                embed.set_footer(text="Autoplay Mode - Music plays continuously")
                msg = await ctx.send(embed=embed)
                asyncio.create_task(self._delete_later(msg, 10))
                return

            guild_id = ctx.guild.id
            if guild_id in active_player_messages:
                try:
                    await active_player_messages[guild_id].delete()
                except Exception:
                    pass

            duration = format_duration(track.length)
            source_emoji, source_name = source_from_uri(track.uri or "")

            embed = discord.Embed(
                title=f"{self.emoji.MUSICAL_NOTES} Now Playing",
                color=0x1DB954,
            )
            embed.add_field(name=f"{self.emoji.MUSICAL_NOTE} Track", value=f"**{track.title[:60]}**", inline=False)
            embed.add_field(name=f"{self.emoji.MICROPHONE} Artist", value=f"**{track.author[:40]}**", inline=True)
            embed.add_field(name=f"{self.emoji.CLOCK} Duration", value=f"**{duration}**", inline=True)
            embed.add_field(name=f"{self.emoji.QUALITY} Quality", value="**High Quality**", inline=True)
            embed.add_field(name=f"{self.emoji.RADIO} Source", value=f"{source_emoji} **{source_name}**", inline=True)
            embed.add_field(name=f"{self.emoji.VOLUME_HIGH} Volume", value=f"**{player.volume}%**", inline=True)

            if getattr(track, "artwork", None):
                embed.set_image(url=track.artwork)

            requester = "Autoplay" if autoplay else ctx.author.display_name
            embed.set_footer(text=f"Requested by {requester}", icon_url=ctx.author.display_avatar.url)

            msg = await ctx.send(embed=embed, view=UltraAdvancedMusicControlView(player, ctx))
            active_player_messages[guild_id] = msg

            await self._log_track_play(ctx, track)
        except Exception as e:
            print(f"❌ Error displaying player embed: {e}")
            await self._display_fallback(player, track, ctx, autoplay)

    async def _display_fallback(self, player: wavelink.Player, track, ctx: commands.Context, autoplay: bool):
        embed = discord.Embed(
            title=f"{self.emoji.MUSICAL_NOTES} Now Playing",
            description=f"**{track.title}** by **{track.author}**",
            color=0x1DB954,
        )
        embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
        if getattr(track, "artwork", None):
            embed.set_image(url=track.artwork)
        msg = await ctx.send(embed=embed, view=UltraAdvancedMusicControlView(player, ctx))
        active_player_messages[ctx.guild.id] = msg

    async def play_source(self, ctx: commands.Context, query: str):
        if not ctx.author.voice:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Voice Channel Required",
                    description="You need to be in a voice channel to play music!",
                    color=0xFF0000,
                )
            )

        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(100)
            except Exception as e:
                return await ctx.send(
                    embed=discord.Embed(
                        title=f"{self.emoji.ERROR} Connection Failed",
                        description=f"Failed to connect: {e}",
                        color=0xFF0000,
                    )
                )

        vc.ctx = ctx

        if vc.playing and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description=f"You must be in {vc.channel.mention} to control the music!",
                    color=0xFF0000,
                )
            )

        # Spotify
        if spotify_api and re.match(SPOTIFY_TRACK_REGEX, query):
            return await self._handle_spotify(ctx, vc, query, "track")
        if spotify_api and re.match(SPOTIFY_PLAYLIST_REGEX, query):
            return await self._handle_spotify(ctx, vc, query, "playlist")
        if spotify_api and re.match(SPOTIFY_ALBUM_REGEX, query):
            return await self._handle_spotify(ctx, vc, query, "album")

        # Regular search
        search_msg = await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.SEARCH} Searching...",
                description=f"Searching for `{query}`...",
                color=0x1DB954,
            )
        )

        try:
            tracks = await wavelink.Playable.search(query)
        except Exception as e:
            return await search_msg.edit(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Search Error",
                    description=f"An error occurred while searching: {e}",
                    color=0xFF0000,
                )
            )

        if not tracks:
            return await search_msg.edit(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Results Found",
                    description=f"No results found for `{query}`.",
                    color=0xFF0000,
                )
            )

        count = len(tracks.tracks) if isinstance(tracks, wavelink.Playlist) else len(tracks)
        await self._log_search(ctx, query, count)

        if isinstance(tracks, wavelink.Playlist):
            await vc.queue.put_wait(tracks.tracks)
            total_sec = sum(t.length // 1000 for t in tracks.tracks)
            embed = discord.Embed(
                title=f"{self.emoji.ADD} Playlist Added to Queue",
                description=f"**{tracks.name}**",
                color=0x1DB954,
            )
            embed.add_field(name="Tracks", value=f"{len(tracks.tracks)} songs", inline=True)
            embed.add_field(name="Total Duration", value=f"{total_sec//60}:{total_sec%60:02d}", inline=True)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            await search_msg.edit(embed=embed)
            asyncio.create_task(self._delete_later(search_msg, 5))

            if not vc.playing and not vc.queue.is_empty:
                next_track = await vc.queue.get_wait()
                await vc.play(next_track)
                await self.display_player_embed(vc, next_track, ctx)
        else:
            track = tracks[0]
            await vc.queue.put_wait(track)
            embed = discord.Embed(
                title=f"{self.emoji.ADD} Track Added to Queue",
                description=f"**{track.title}**",
                color=0x1DB954,
            )
            embed.add_field(name="Artist", value=track.author, inline=True)
            embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
            if getattr(track, "artwork", None):
                embed.set_thumbnail(url=track.artwork)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            await search_msg.edit(embed=embed)
            asyncio.create_task(self._delete_later(search_msg, 5))

            if not vc.playing and not vc.queue.is_empty:
                next_track = await vc.queue.get_wait()
                await vc.play(next_track)
                await self.display_player_embed(vc, next_track, ctx)

    async def _handle_spotify(self, ctx: commands.Context, vc: wavelink.Player, link: str, type_: str):
        try:
            if type_ == "track":
                tid = re.search(SPOTIFY_TRACK_REGEX, link).group(1)
                info = await spotify_api.get_track(tid)
                title = info["name"]
                author = ", ".join(a["name"] for a in info["artists"])
                results = await wavelink.Playable.search(f"{title} by {author}")
                if not results:
                    return await ctx.send(
                        embed=discord.Embed(
                            title=f"{self.emoji.ERROR} Track Not Available",
                            description="This Spotify track is not available on YouTube.",
                            color=0xFF0000,
                        )
                    )
                track = results[0] if not isinstance(results, wavelink.Playlist) else results.tracks[0]
                await vc.queue.put_wait(track)
                embed = discord.Embed(
                    title=f"{self.emoji.SPOTIFY} Spotify Track Added",
                    description=f"**{track.title}**",
                    color=0x1DB954,
                )
                embed.add_field(name="Artist", value=track.author, inline=True)
                embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
                if getattr(track, "artwork", None):
                    embed.set_thumbnail(url=track.artwork)
                msg = await ctx.send(embed=embed)
                asyncio.create_task(self._delete_later(msg, 5))
                if not vc.playing:
                    await vc.play(track)
                    await self.display_player_embed(vc, track, ctx)

            elif type_ == "playlist":
                proc = await ctx.send(
                    embed=discord.Embed(
                        title=f"{self.emoji.LOADING} Processing Playlist",
                        description="Adding tracks from Spotify playlist...",
                        color=0x1DB954,
                    )
                )
                pid = re.search(SPOTIFY_PLAYLIST_REGEX, link).group(1)
                info = await spotify_api.get(f"playlists/{pid}")
                items = info.get("tracks", {}).get("items", [])
                total = len(items)
                c = 0
                for item in items:
                    if not item.get("track"):
                        continue
                    t_title = item["track"]["name"]
                    t_author = ", ".join(a["name"] for a in item["track"]["artists"])
                    try:
                        res = await wavelink.Playable.search(f"{t_title} {t_author}")
                        if res:
                            t = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                            await vc.queue.put_wait(t)
                            c += 1
                    except Exception:
                        continue
                await proc.edit(
                    embed=discord.Embed(
                        title=f"{self.emoji.ADD} Spotify Playlist Added",
                        description=f"**{c}** of **{total}** tracks added from **{info['name']}**!",
                        color=0x1DB954,
                    )
                )
                asyncio.create_task(self._delete_later(proc, 5))
                if not vc.playing and not vc.queue.is_empty:
                    nt = await vc.queue.get_wait()
                    await vc.play(nt)
                    await self.display_player_embed(vc, nt, ctx)

            elif type_ == "album":
                proc = await ctx.send(
                    embed=discord.Embed(
                        title=f"{self.emoji.LOADING} Processing Album",
                        description="Adding tracks from Spotify album...",
                        color=0x1DB954,
                    )
                )
                aid = re.search(SPOTIFY_ALBUM_REGEX, link).group(1)
                info = await spotify_api.get(f"albums/{aid}")
                items = info.get("tracks", {}).get("items", [])
                c = 0
                for item in items:
                    t_title = item["name"]
                    t_author = ", ".join(a["name"] for a in item["artists"])
                    try:
                        res = await wavelink.Playable.search(f"{t_title} {t_author}")
                        if res:
                            t = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                            await vc.queue.put_wait(t)
                            c += 1
                    except Exception:
                        continue
                await proc.edit(
                    embed=discord.Embed(
                        title=f"{self.emoji.ADD} Spotify Album Added",
                        description=f"**{c}** tracks added from **{info['name']}**!",
                        color=0x1DB954,
                    )
                )
                asyncio.create_task(self._delete_later(proc, 5))
                if not vc.playing and not vc.queue.is_empty:
                    nt = await vc.queue.get_wait()
                    await vc.play(nt)
                    await self.display_player_embed(vc, nt, ctx)
        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Spotify Error",
                    description=f"An error occurred: {e}",
                    color=0xFF0000,
                )
            )

    # -------- Commands --------
    @commands.hybrid_command(name="play", aliases=["p"], help="Plays a song or playlist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str):
        await self.play_source(ctx, query)

    @commands.hybrid_command(name="search", help="Searches music from multiple platforms.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def search2(self, ctx: commands.Context, *, query: str):
        if not ctx.author.voice:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Voice Channel Required",
                    description="You need to be in a voice channel!",
                    color=0xFF0000,
                )
            )
        embed = discord.Embed(
            title=f"{self.emoji.SEARCH} Select Search Platform",
            description=f"Choose where to search for: **{query}**",
            color=0x1DB954,
        )
        await ctx.send(embed=embed, view=PlatformSelectView(ctx, query))

    @commands.hybrid_command(name="nowplaying", aliases=["np"], help="Shows current song info.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def nowplaying(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc or not vc.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                )
            )
        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel as me!",
                    color=0xFF0000,
                )
            )
        track = vc.current
        if not track:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Track",
                    description="No track is currently playing!",
                    color=0xFF0000,
                )
            )
        pos = vc.position / 1000
        length = track.length / 1000
        pct = (pos / length * 100) if length > 0 else 0
        source_emoji, source_name = source_from_uri(track.uri or "")
        embed = discord.Embed(title=f"{self.emoji.MUSICAL_NOTES} Now Playing", color=0x1DB954)
        embed.add_field(name=f"{self.emoji.MUSICAL_NOTE} Track", value=f"[{track.title}]({track.uri})", inline=False)
        embed.add_field(name=f"{self.emoji.MICROPHONE} Artist", value=track.author, inline=True)
        embed.add_field(name=f"{self.emoji.CLOCK} Progress", value=f"`{format_duration(int(pos*1000))}` / `{format_duration(track.length)}` ({pct:.0f}%)", inline=True)
        embed.add_field(name=f"{self.emoji.QUEUE} Queue", value=f"`{len(vc.queue)}` tracks", inline=True)
        embed.add_field(name=f"{self.emoji.RADIO} Source", value=f"{source_emoji} {source_name}", inline=True)
        if getattr(track, "artwork", None):
            embed.set_image(url=track.artwork)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="join", help="Joins your voice channel.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def join(self, ctx: commands.Context):
        if not ctx.author.voice:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Voice Channel Required",
                    description="You need to be in a voice channel!",
                    color=0xFF0000,
                )
            )
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if vc:
            if vc.channel.id == ctx.author.voice.channel.id:
                return await ctx.send(
                    embed=discord.Embed(
                        title=f"{self.emoji.WARNING} Already Connected",
                        description=f"I'm already in {vc.channel.mention}!",
                        color=0xFFA500,
                    )
                )
            await vc.move_to(ctx.author.voice.channel)
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.SUCCESS} Moved",
                    description=f"Moved to {ctx.author.voice.channel.mention}!",
                    color=0x1DB954,
                )
            )
        try:
            if not wavelink.Pool.nodes:
                return await ctx.send(
                    embed=discord.Embed(
                        title=f"{self.emoji.ERROR} Lavalink Not Connected",
                        description="Music server is not ready. Please wait a moment.",
                        color=0xFF0000,
                    )
                )
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            vc.ctx = ctx
            await vc.set_volume(100)
            await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.SUCCESS} Connected",
                    description=f"Joined {ctx.author.voice.channel.mention}!\n\nUse `/play` to start playing.",
                    color=0x1DB954,
                )
            )
        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Connection Failed",
                    description=f"Failed to join: {e}",
                    color=0xFF0000,
                )
            )

    @commands.hybrid_command(name="disconnect", aliases=["dc", "leave"], help="Disconnects from voice.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def disconnect(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel as me!",
                    color=0xFF0000,
                )
            )
        await vc.disconnect()
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.SUCCESS} Disconnected",
                description="Successfully disconnected!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="pause", help="Pauses the current track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pause(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc or not vc.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        await vc.pause(True)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.PAUSE} Playback Paused",
                description=f"**{vc.current.title}**",
                color=0xFFA500,
            )
        )

    @commands.hybrid_command(name="resume", help="Resumes the paused track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def resume(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if not vc.paused:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.WARNING} Already Playing",
                    description="The music is already playing!",
                    color=0xFFA500,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        await vc.pause(False)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.PLAY} Playback Resumed",
                description=f"**{vc.current.title}**",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="skip", help="Skips the current track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def skip(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc or not vc.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        title = vc.current.title if vc.current else "Unknown"
        await vc.stop()
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.SKIP} Track Skipped",
                description=f"**{title}**",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="stop", help="Stops playback and clears the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def stop(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        gid = ctx.guild.id
        if gid in active_player_messages:
            try:
                await active_player_messages[gid].delete()
                del active_player_messages[gid]
            except Exception:
                pass
        vc.queue.clear()
        await vc.disconnect()
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.STOP} Playback Stopped",
                description="Music playback has been stopped and queue cleared!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="volume", aliases=["vol"], help="Sets the player volume (1-200).")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def volume(self, ctx: commands.Context, volume: int):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        if not 1 <= volume <= 200:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Invalid Volume",
                    description="Volume must be between 1 and 200!",
                    color=0xFF0000,
                )
            )
        old = vc.volume
        await vc.set_volume(volume)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.VOLUME_HIGH} Volume Adjusted",
                description=f"Volume: `{old}%` → `{volume}%`",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="queue", aliases=["q"], help="Shows the current queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def queue(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if vc.queue.is_empty:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.QUEUE} Queue Empty",
                    description="The queue is currently empty!",
                    color=0xFFA500,
                )
            )
        embed = discord.Embed(
            title=f"{self.emoji.QUEUE} Current Queue",
            description="Showing up to 10 tracks",
            color=0x1DB954,
        )
        for i, t in enumerate(list(vc.queue)[:10], 1):
            embed.add_field(
                name=f"{i}. {t.title[:50]}",
                value=f"**Artist:** {t.author[:30]} | **Duration:** {format_duration(t.length)}",
                inline=False,
            )
        if len(vc.queue) > 10:
            embed.set_footer(text=f"And {len(vc.queue) - 10} more tracks...")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clearqueue", aliases=["cq"], help="Clears the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def clearqueue(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        if vc.queue.is_empty:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.WARNING} Queue Already Empty",
                    description="The queue is already empty!",
                    color=0xFFA500,
                )
            )
        c = len(vc.queue)
        vc.queue.clear()
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.CLEAR} Queue Cleared",
                description=f"Cleared `{c}` tracks!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="shuffle", help="Shuffles the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shuffle(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        if vc.queue.is_empty:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Queue Empty",
                    description="The queue is empty, nothing to shuffle!",
                    color=0xFF0000,
                )
            )
        queue_list = list(vc.queue)
        random.shuffle(queue_list)
        vc.queue.clear()
        for t in queue_list:
            vc.queue.put(t)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.SHUFFLE} Queue Shuffled",
                description=f"Shuffled `{len(queue_list)}` tracks!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="loop", help="Toggles loop mode.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def loop(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc or not vc.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        vc.queue.mode = (
            wavelink.QueueMode.loop
            if vc.queue.mode != wavelink.QueueMode.loop
            else wavelink.QueueMode.normal
        )
        mode = "enabled" if vc.queue.mode == wavelink.QueueMode.loop else "disabled"
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.REPEAT} Loop {mode.title()}",
                description=f"Loop mode has been **{mode}**!",
                color=0x1DB954 if mode == "enabled" else 0xFFA500,
            )
        )

    @commands.hybrid_command(name="autoplay", help="Start 24/7 autoplay.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def autoplay(self, ctx: commands.Context):
        if not ctx.author.voice:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Voice Channel Required",
                    description="You need to be in a voice channel!",
                    color=0xFF0000,
                )
            )
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(100)
            except Exception as e:
                return await ctx.send(
                    embed=discord.Embed(
                        title=f"{self.emoji.ERROR} Connection Failed",
                        description=f"Failed to join: {e}",
                        color=0xFF0000,
                    )
                )
        vc.ctx = ctx
        vc._autoplay_only = True

        queries = [
            "lofi hip hop radio", "lofi study music", "chill lofi beats",
            "latest hindi songs", "bollywood romantic songs",
            "sad songs english", "top english songs", "arabic songs",
        ]
        status = await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.LOADING} Starting 24/7 Autoplay",
                description="Loading random songs...",
                color=0x1DB954,
            )
        )
        added = 0
        for _ in range(20):
            q = random.choice(queries)
            try:
                res = await wavelink.Playable.search(q)
                if res:
                    t = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                    await vc.queue.put_wait(t)
                    added += 1
            except Exception:
                continue
        await status.edit(
            embed=discord.Embed(
                title=f"{self.emoji.SUCCESS} 24/7 Autoplay Started!",
                description=f"Loaded **{added}** songs. Stop with `/stop`.",
                color=0x1DB954,
            )
        )
        asyncio.create_task(self._delete_later(status, 5))
        if not vc.playing and not vc.queue.is_empty:
            nt = await vc.queue.get_wait()
            await vc.play(nt)
            embed = discord.Embed(
                title=f"{self.emoji.MUSICAL_NOTES} Now Playing - Autoplay",
                description=f"**{nt.title}**\nby **{nt.author}**",
                color=0x1DB954,
            )
            if getattr(nt, "artwork", None):
                embed.set_thumbnail(url=nt.artwork)
            msg = await ctx.send(embed=embed)
            asyncio.create_task(self._delete_later(msg, 10))

    @commands.hybrid_command(name="seek", help="Seek to a position (seconds).")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def seek(self, ctx: commands.Context, seconds: int):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc or not vc.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        if seconds < 0 or seconds * 1000 > vc.current.length:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Invalid Position",
                    description=f"Position must be between 0 and {vc.current.length // 1000} seconds!",
                    color=0xFF0000,
                )
            )
        await vc.seek(seconds * 1000)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.CLOCK} Seeked",
                description=f"Seeked to `{seconds // 60}:{seconds % 60:02d}` in **{vc.current.title}**!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="replay", help="Replays the current track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def replay(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc or not vc.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        await vc.seek(0)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.REPEAT} Replaying",
                description=f"Replaying **{vc.current.title}**!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="previous", aliases=["prev"], help="Play the previous track")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def previous(self, ctx: commands.Context):
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000,
                )
            )
        if ctx.author.voice and ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel!",
                    color=0xFF0000,
                )
            )
        gid = ctx.guild.id
        if gid in track_histories and track_histories[gid]:
            prev = track_histories[gid].pop()
            await vc.play(prev)
            await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.PREVIOUS} Playing Previous Track",
                    description=f"**{prev.title}**",
                    color=0x1DB954,
                )
            )
            await self.display_player_embed(vc, prev, ctx)
        else:
            await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Previous Track",
                    description="There's no previous track in history!",
                    color=0xFF0000,
                )
            )

    # -------- Playlists --------
    @commands.hybrid_command(name="createplaylist", help="Create a new playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def createplaylist(self, ctx: commands.Context, *, name: str):
        uid = ctx.author.id
        if uid not in user_playlists:
            user_playlists[uid] = {}
        if name in user_playlists[uid]:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Playlist Exists",
                    description=f"You already have a playlist named **{name}**!",
                    color=0xFF0000,
                )
            )
        user_playlists[uid][name] = []
        await ctx.send(
            embed=discord.Embed(
                title="✅ Playlist Created",
                description=f"Created playlist **{name}**!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="playlists", help="View your playlists")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def playlists(self, ctx: commands.Context):
        pl = user_playlists.get(ctx.author.id, {})
        if not pl:
            return await ctx.send(
                embed=discord.Embed(
                    title="📂 Your Playlists",
                    description="You don't have any playlists yet!\nUse `x!createplaylist <name>` to create one.",
                    color=0xFFA500,
                )
            )
        embed = discord.Embed(
            title="📂 Your Playlists",
            description=f"You have {len(pl)} playlist(s):",
            color=0x1DB954,
        )
        for name, tracks in list(pl.items())[:10]:
            embed.add_field(name=f"📁 {name}", value=f"`{len(tracks)}` tracks", inline=True)
        if len(pl) > 10:
            embed.set_footer(text=f"And {len(pl) - 10} more...")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="playplaylist", help="Play a saved playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def playplaylist(self, ctx: commands.Context, *, name: str):
        if not ctx.author.voice:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Voice Channel Required",
                    description="You need to be in a voice channel!",
                    color=0xFF0000,
                )
            )
        pl = user_playlists.get(ctx.author.id, {})
        if name not in pl:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Playlist Not Found",
                    description=f"You don't have a playlist named **{name}**!",
                    color=0xFF0000,
                )
            )
        vc: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not vc:
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            await vc.set_volume(100)
        vc.ctx = ctx
        msg = await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.LOADING} Loading Playlist",
                description=f"Loading **{name}**...",
                color=0x1DB954,
            )
        )
        loaded = 0
        for td in pl[name]:
            try:
                res = await wavelink.Playable.search(td["uri"])
                if res:
                    t = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                    await vc.queue.put_wait(t)
                    loaded += 1
            except Exception:
                continue
        await msg.edit(
            embed=discord.Embed(
                title="✅ Playlist Loaded",
                description=f"Loaded **{loaded}** tracks from **{name}**!",
                color=0x1DB954,
            )
        )
        if not vc.playing and not vc.queue.is_empty:
            nt = await vc.queue.get_wait()
            await vc.play(nt)
            await self.display_player_embed(vc, nt, ctx)

    @commands.hybrid_command(name="deleteplaylist", help="Delete a playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def deleteplaylist(self, ctx: commands.Context, *, name: str):
        pl = user_playlists.get(ctx.author.id, {})
        if name not in pl:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Playlist Not Found",
                    description=f"You don't have a playlist named **{name}**!",
                    color=0xFF0000,
                )
            )
        del user_playlists[ctx.author.id][name]
        await ctx.send(
            embed=discord.Embed(
                title="✅ Playlist Deleted",
                description=f"Deleted playlist **{name}**!",
                color=0x1DB954,
            )
        )

    @commands.hybrid_command(name="viewplaylist", help="View tracks in a playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def viewplaylist(self, ctx: commands.Context, *, name: str):
        pl = user_playlists.get(ctx.author.id, {})
        if name not in pl:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Playlist Not Found",
                    description=f"You don't have a playlist named **{name}**!",
                    color=0xFF0000,
                )
            )
        tracks = pl[name]
        if not tracks:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"📁 {name}",
                    description="This playlist is empty!",
                    color=0xFFA500,
                )
            )
        embed = discord.Embed(
            title=f"📁 {name}",
            description=f"{len(tracks)} tracks:",
            color=0x1DB954,
        )
        for i, t in enumerate(tracks[:10], 1):
            embed.add_field(
                name=f"{i}. {t['title'][:40]}",
                value=f"by {t['author'][:30]}",
                inline=False,
            )
        if len(tracks) > 10:
            embed.set_footer(text=f"And {len(tracks) - 10} more...")
        await ctx.send(embed=embed)

    # -------- Wavelink events --------
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        track = payload.track
        if not player or not track or not player.guild:
            return
        gid = player.guild.id
        track_histories.setdefault(gid, []).append(track)
        if len(track_histories[gid]) > 20:
            track_histories[gid].pop(0)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        # wavelink v3 auto-advances the queue; just handle autoplay refill + no-user cleanup.
        player = payload.player
        if not player or not player.guild:
            return

        if getattr(player, "_autoplay_only", False) and len(player.queue) < 5:
            queries = [
                "lofi hip hop radio", "lofi study music", "chill lofi beats",
                "latest hindi songs", "bollywood romantic songs",
                "sad songs english", "top english songs", "arabic songs",
            ]
            for _ in range(10):
                q = random.choice(queries)
                try:
                    res = await wavelink.Playable.search(q)
                    if res:
                        t = res.tracks[0] if isinstance(res, wavelink.Playlist) else res[0]
                        await player.queue.put_wait(t)
                except Exception:
                    continue

        # If queue empty and not autoplay, disconnect after inactivity
        if player.queue.is_empty and not getattr(player, "_autoplay_only", False):
            ctx = getattr(player, "ctx", None)
            try:
                await asyncio.sleep(5)  # small grace
                if player.is_connected() and player.queue.is_empty and not getattr(player, "_autoplay_only", False):
                    await player.disconnect()
                    if ctx:
                        emoji = EmojiConfig()
                        try:
                            await ctx.channel.send(
                                embed=discord.Embed(
                                    title=f"{emoji.STOP} Queue Ended",
                                    description="All tracks have been played. I've left the voice channel.",
                                    color=0x1DB954,
                                )
                            )
                        except Exception:
                            pass
            except Exception:
                pass


# ============================================================
# Filter Cog
# ============================================================
class FilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_filters: dict[int, str] = {}
        self.emoji = EmojiConfig()

    @commands.hybrid_group(invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def filter(self, ctx: commands.Context):
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.FILTER} Audio Filters",
                description=(
                    "• `filter enable` - Enable audio filters\n"
                    "• `filter disable` - Disable all filters"
                ),
                color=0x1DB954,
            ).add_field(
                name="Current Filter",
                value=f"`{self.active_filters.get(ctx.guild.id, 'None')}`",
                inline=True,
            )
        )

    @filter.command(help="Enable audio filters.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def enable(self, ctx: commands.Context):
        p: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not p or not p.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="I'm not playing any music right now!",
                    color=0xFF0000,
                )
            )
        if not ctx.author.voice or ctx.author.voice.channel.id != p.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel as me!",
                    color=0xFF0000,
                )
            )
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.FILTER} Select a Filter",
                description="Choose an audio filter to apply.",
                color=0x1DB954,
            ),
            view=FilterSelectView(ctx),
        )

    @filter.command(help="Disable all audio filters.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def disable(self, ctx: commands.Context):
        p: Optional[wavelink.Player] = ctx.voice_client  # type: ignore
        if not p or not p.playing:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="I'm not playing any music right now!",
                    color=0xFF0000,
                )
            )
        if not ctx.author.voice or ctx.author.voice.channel.id != p.channel.id:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Wrong Voice Channel",
                    description="You need to be in the same voice channel as me!",
                    color=0xFF0000,
                )
            )
        await p.set_filters(wavelink.Filters())
        self.active_filters.pop(ctx.guild.id, None)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.emoji.SUCCESS} Filters Disabled",
                description="All audio filters have been removed!",
                color=0x1DB954,
            )
        )


# ============================================================
# Help
# ============================================================
class HelpView(View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.current_page = 0
        self.pages = self._build_pages()

    def _build_pages(self) -> list[discord.Embed]:
        e1 = discord.Embed(
            title="🎵 Music Bot - Help",
            description="**Prefixes:** `x!` `/`",
            color=0x1DB954,
        )
        e1.add_field(
            name="🎶 Basic Commands",
            value=(
                "`x!play <query>` - Play music\n"
                "`x!search <query>` - Search platforms\n"
                "`x!nowplaying` - Show current track\n"
                "`x!queue` - Show queue\n"
                "`x!skip` - Skip track\n"
                "`x!pause` / `x!resume`\n"
                "`x!stop` - Stop & clear\n"
                "`x!volume <1-200>`"
            ),
            inline=False,
        )
        e1.set_footer(text="Page 1/3")

        e2 = discord.Embed(title="🎛️ Advanced", color=0x1DB954)
        e2.add_field(
            name="🔧 Controls",
            value=(
                "`x!loop` - Toggle loop\n"
                "`x!shuffle` - Shuffle queue\n"
                "`x!seek <seconds>`\n"
                "`x!replay` - Restart track\n"
                "`x!previous` - Previous track\n"
                "`x!autoplay` - 24/7 autoplay\n"
                "`x!clearqueue`\n"
                "`x!join` / `x!disconnect`"
            ),
            inline=False,
        )
        e2.set_footer(text="Page 2/3")

        e3 = discord.Embed(title="📂 Playlists & Filters", color=0x1DB954)
        e3.add_field(
            name="Playlists",
            value=(
                "`x!createplaylist <name>`\n"
                "`x!playlists`\n"
                "`x!playplaylist <name>`\n"
                "`x!deleteplaylist <name>`\n"
                "`x!viewplaylist <name>`"
            ),
            inline=False,
        )
        e3.add_field(
            name="Filters",
            value=(
                "`x!filter enable` - Apply filters\n"
                "`x!filter disable` - Remove filters"
            ),
            inline=False,
        )
        e3.set_footer(text="Page 3/3")
        return [e1, e2, e3]

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = 0
        await interaction.response.edit_message(embed=self.pages[0], view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = max(0, self.current_page - 1)
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", help="Shows all available commands.")
    async def help_command(self, ctx: commands.Context):
        view = HelpView(ctx)
        await ctx.send(embed=view.pages[0], view=view)


class _music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = EmojiConfig()

    def help_custom(self):
        return self.emoji.MUSICAL_NOTES, "Music Commands", "Complete music system"


# ============================================================
# Bot
# ============================================================
intents = discord.Intents.all()


def load_bot_token() -> Optional[str]:
    try:
        with open("bot_config.json", "r") as f:
            cfg = json.load(f)
        token = cfg.get("discord_token") or os.environ.get("DISCORD_TOKEN")
        if token and token.strip():
            return token
    except FileNotFoundError:
        pass
    return os.environ.get("DISCORD_TOKEN")


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=["x!", "/"], intents=intents, help_command=None)
        self.session: Optional[aiohttp.ClientSession] = None
        self.music_db = MusicDatabase()

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await self.music_db.connect()
        self.update_presence.start()

        await self.add_cog(Music(self))
        await self.add_cog(FilterCog(self))
        await self.add_cog(HelpCog(self))
        await self.add_cog(_music(self))
        print("✅ All cogs loaded successfully!")

        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

    async def close(self):
        if self.session:
            await self.session.close()
        await self.music_db.close()
        await super().close()

    @tasks.loop(minutes=5)
    async def update_presence(self):
        try:
            total = sum(g.member_count for g in self.guilds)
            activity = discord.Activity(
                type=discord.ActivityType.streaming,
                name=f"{len(self.guilds)} Servers | {total} Members",
                details="Ultra HD Music Player",
                state="Prefix: x!",
                url="https://twitch.tv/discord",
            )
            await self.change_presence(activity=activity, status=discord.Status.online)
        except Exception as e:
            print(f"❌ Presence error: {e}")

    @update_presence.before_loop
    async def before_update_presence(self):
        await self.wait_until_ready()


bot = MusicBot()


def main():
    token = load_bot_token()
    if not token:
        print("❌ ERROR: Discord bot token not found!")
        print("Set DISCORD_TOKEN in env or add 'discord_token' to bot_config.json")
        return
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid Discord token!")
    except Exception as e:
        print(f"❌ ERROR: Failed to start bot: {e}")


if __name__ == "__main__":
    main()