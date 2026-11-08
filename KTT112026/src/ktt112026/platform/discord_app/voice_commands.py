"""Discord slash commands and the legacy .tts prefix command."""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ...config import Settings
from ...features.voice.music.manager import MusicManager
from ...features.voice.music.models import TTSClip, Track
from ...features.voice.music.resolver import resolve_track
from ...features.voice.tts.service import enqueue_speech
from ...features.voice.tts.voices import DEFAULT_VOICE, VOICE_LABELS

logger = logging.getLogger(__name__)


def _duration(seconds: int | None) -> str:
    if seconds is None:
        return "?:??"
    minutes, secs = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _item_title(item: Track | TTSClip) -> str:
    if isinstance(item, TTSClip):
        return f"🔊 {item.title}"
    return f"🎵 [{item.title}]({item.webpage_url}) `{_duration(item.duration)}`"


class VoiceCommands(commands.Cog):
    def __init__(self, music: MusicManager, settings: Settings) -> None:
        self.music = music
        self.settings = settings

    @staticmethod
    async def _voice_channel(interaction: discord.Interaction) -> discord.VoiceChannel | None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Chỉ dùng lệnh này trong máy chủ Discord.", ephemeral=True)
            return None
        voice_state = interaction.user.voice
        channel = voice_state.channel if voice_state else None
        if not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message("Hãy vào một kênh thoại thường trước.", ephemeral=True)
            return None
        return channel

    @staticmethod
    async def _prefix_voice_channel(ctx: commands.Context) -> discord.VoiceChannel | None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            await ctx.reply("Lệnh này chỉ dùng trong máy chủ Discord.", mention_author=False)
            return None
        channel = ctx.author.voice.channel if ctx.author.voice else None
        if not isinstance(channel, discord.VoiceChannel):
            await ctx.reply("Hãy vào một kênh thoại thường trước.", mention_author=False)
            return None
        return channel

    @app_commands.command(name="join", description="Bot vào kênh thoại của bạn")
    async def join(self, interaction: discord.Interaction) -> None:
        channel = await self._voice_channel(interaction)
        if channel is None:
            return
        try:
            player = self.music.player(interaction.guild.id)
            await player.connect(channel)
        except Exception as exc:
            logger.exception("/join failed")
            await interaction.response.send_message(f"Không thể vào kênh thoại: {exc}", ephemeral=True)
            return
        await interaction.response.send_message(f"Đã vào **{channel.name}**.", ephemeral=True)

    @app_commands.command(name="leave", description="Bot rời kênh thoại")
    async def leave(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            return
        player = self.music.player(interaction.guild.id)
        try:
            await player.leave()
        except Exception as exc:
            logger.exception("/leave failed")
            await interaction.response.send_message(f"Không thể rời kênh: {exc}", ephemeral=True)
            return
        await interaction.response.send_message("Bot đã rời kênh thoại.", ephemeral=True)

    @app_commands.command(name="play", description="Phát nhạc YouTube bằng link hoặc tên bài")
    @app_commands.describe(query="Link HTTP(S) hoặc tên bài hát")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        channel = await self._voice_channel(interaction)
        if channel is None:
            return
        await interaction.response.defer(thinking=True)
        try:
            player = self.music.player(interaction.guild.id)
            await player.connect(channel)
            track = await resolve_track(query, interaction.user.id)
            position = await player.enqueue(track)
        except Exception as exc:
            logger.exception("/play failed")
            await interaction.followup.send(f"Không phát được: {exc}", ephemeral=True)
            return
        message = "Đang phát ngay." if position == 1 and player.current is track else f"Đã xếp hàng ở vị trí #{position}."
        await interaction.followup.send(f"🎵 **{track.title}** — {_duration(track.duration)}\n{message}")

    @app_commands.command(name="skip", description="Bỏ qua mục đang phát")
    async def skip(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            return
        skipped = await self.music.player(interaction.guild.id).skip()
        if skipped is None:
            await interaction.response.send_message("Không có mục nào để bỏ qua.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Đã bỏ qua **{skipped.title}**.")

    @app_commands.command(name="pause", description="Tạm dừng phát nhạc/TTS")
    async def pause(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            return
        paused = await self.music.player(interaction.guild.id).pause()
        await interaction.response.send_message("Đã tạm dừng." if paused else "Hiện không có âm thanh đang phát.", ephemeral=True)

    @app_commands.command(name="resume", description="Tiếp tục phát nhạc/TTS")
    async def resume(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            return
        resumed = await self.music.player(interaction.guild.id).resume()
        await interaction.response.send_message("Đã tiếp tục." if resumed else "Không có nội dung đang tạm dừng.", ephemeral=True)

    @app_commands.command(name="stop", description="Dừng và xóa toàn bộ hàng chờ")
    async def stop(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            return
        await self.music.player(interaction.guild.id).stop()
        await interaction.response.send_message("Đã dừng và xóa hàng chờ.", ephemeral=True)

    @app_commands.command(name="queue", description="Xem hàng chờ nhạc và TTS")
    async def queue(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            return
        player = self.music.player(interaction.guild.id)
        lines: list[str] = []
        if player.current:
            lines.append(f"**Đang phát:** {_item_title(player.current)}")
        if player.queue:
            lines.append("**Tiếp theo:**")
            lines.extend(f"`{index}.` {_item_title(item)}" for index, item in enumerate(list(player.queue)[:15], 1))
            if len(player.queue) > 15:
                lines.append(f"… còn {len(player.queue) - 15} mục")
        await interaction.response.send_message("\n".join(lines) if lines else "Hàng chờ đang trống.", ephemeral=True)

    @app_commands.command(name="tts", description="Đọc văn bản tiếng Việt trong kênh thoại")
    @app_commands.describe(text="Nội dung cần đọc", voice="Giọng tiếng Việt")
    @app_commands.choices(voice=[
        app_commands.Choice(name=label, value=voice_id)
        for voice_id, label in VOICE_LABELS.items()
    ])
    async def tts(
        self,
        interaction: discord.Interaction,
        text: str,
        voice: str = DEFAULT_VOICE,
    ) -> None:
        channel = await self._voice_channel(interaction)
        if channel is None:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            player = self.music.player(interaction.guild.id)
            await player.connect(channel)
            position, started = await enqueue_speech(
                player, text, interaction.user.id,
                voice_name=voice,
                max_chars=self.settings.max_tts_chars,
            )
        except Exception as exc:
            logger.exception("/tts failed")
            await interaction.followup.send(f"Không đọc được văn bản: {exc}", ephemeral=True)
            return
        await interaction.followup.send(
            "TTS bắt đầu phát." if started else f"TTS đã xếp hàng ở vị trí #{position}.",
            ephemeral=True,
        )

    @commands.command(name="tts")
    async def tts_prefix(self, ctx: commands.Context, *, text: str) -> None:
        """Compatibility command retained from 102026: .tts <text>."""
        channel = await self._prefix_voice_channel(ctx)
        if channel is None:
            return
        try:
            player = self.music.player(ctx.guild.id)
            await player.connect(channel)
            position, started = await enqueue_speech(
                player, text, ctx.author.id, max_chars=self.settings.max_tts_chars
            )
        except Exception as exc:
            logger.exception(".tts failed")
            await ctx.reply(f"Không đọc được văn bản: {exc}", mention_author=False)
            return
        await ctx.reply(
            "TTS bắt đầu phát." if started else f"TTS đã xếp hàng ở vị trí #{position}.",
            mention_author=False,
        )

    @app_commands.command(name="voice-status", description="Xem trạng thái kết nối voice của bot")
    async def voice_status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if not voice or not voice.is_connected():
            message = "Bot hiện không kết nối voice."
        else:
            current = voice.channel.name if voice.channel else "không rõ kênh"
            player = self.music.get_existing(interaction.guild.id)
            message = f"Bot đang ở **{current}**. "
            if player and player.current:
                message += f"Đang phát: **{player.current.title}**."
            elif voice.is_paused():
                message += "Đang tạm dừng."
            else:
                message += "Đang chờ nội dung."
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="help", description="Xem hướng dẫn lệnh Voice, Music và TTS")
    async def help(self, interaction: discord.Interaction) -> None:
        help_text = (
            "**Voice**\n"
            "`/join` vào voice · `/leave` rời voice · `/voice-status` xem trạng thái\n\n"
            "**Music**\n"
            "`/play <link/tên>` phát nhạc · `/queue` xem hàng chờ · `/skip` bỏ qua\n"
            "`/pause` tạm dừng · `/resume` tiếp tục · `/stop` dừng và xóa hàng chờ\n\n"
            "**TTS**\n"
            "`/tts <văn bản>` hoặc `.tts <văn bản>` để đọc tiếng Việt\n\n"
            "**System**\n"
            "`/ping` kiểm tra độ trễ · `/health` kiểm tra FFmpeg/yt-dlp/Edge TTS"
        )
        await interaction.response.send_message(help_text, ephemeral=True)

    @app_commands.command(name="ping", description="Kiểm tra độ trễ của bot")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong · {latency_ms} ms", ephemeral=True)

    @app_commands.command(name="health", description="Kiểm tra các thành phần voice/audio")
    async def health(self, interaction: discord.Interaction) -> None:
        from ...features.voice.audio.ffmpeg import get_ffmpeg_executable

        try:
            ffmpeg = get_ffmpeg_executable()
            ffmpeg_status = f"OK ({ffmpeg})"
        except Exception as exc:
            ffmpeg_status = f"Lỗi ({exc})"
        try:
            import yt_dlp  # noqa: F401
            ytdlp_status = "OK"
        except ImportError:
            ytdlp_status = "Thiếu yt-dlp"
        try:
            import edge_tts  # noqa: F401
            tts_status = "OK"
        except ImportError:
            tts_status = "Thiếu edge-tts"
        await interaction.response.send_message(
            f"FFmpeg: {ffmpeg_status}\nyt-dlp: {ytdlp_status}\nEdge TTS: {tts_status}",
            ephemeral=True,
        )

