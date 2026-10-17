import aiosqlite
import os


class MusicDatabase:
    def __init__(self, db_path: str = "music.db"):
        self.db_path = db_path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                server_id INTEGER PRIMARY KEY,
                server_name TEXT
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS voice_channels (
                channel_id INTEGER PRIMARY KEY,
                server_id INTEGER,
                channel_name TEXT
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS music_plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                channel_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                track_title TEXT,
                track_author TEXT,
                track_uri TEXT,
                track_duration INTEGER,
                track_source TEXT,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                search_query TEXT,
                results_count INTEGER,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def register_server(self, server_id: int, server_name: str):
        if not self.conn:
            return
        await self.conn.execute(
            "INSERT OR REPLACE INTO servers (server_id, server_name) VALUES (?, ?)",
            (server_id, server_name)
        )
        await self.conn.commit()

    async def register_voice_channel(self, channel_id: int, server_id: int, channel_name: str):
        if not self.conn:
            return
        await self.conn.execute(
            "INSERT OR REPLACE INTO voice_channels (channel_id, server_id, channel_name) VALUES (?, ?, ?)",
            (channel_id, server_id, channel_name)
        )
        await self.conn.commit()

    async def log_music_play(self, server_id, channel_id, user_id, user_name,
                             track_title, track_author, track_uri, track_duration, track_source):
        if not self.conn:
            return
        await self.conn.execute(
            """INSERT INTO music_plays
               (server_id, channel_id, user_id, user_name, track_title, track_author,
                track_uri, track_duration, track_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (server_id, channel_id, user_id, user_name, track_title, track_author,
             track_uri, track_duration, track_source)
        )
        await self.conn.commit()

    async def log_search(self, server_id, user_id, user_name, search_query, results_count):
        if not self.conn:
            return
        await self.conn.execute(
            """INSERT INTO searches
               (server_id, user_id, user_name, search_query, results_count)
               VALUES (?, ?, ?, ?, ?)""",
            (server_id, user_id, user_name, search_query, results_count)
        )
        await self.conn.commit()