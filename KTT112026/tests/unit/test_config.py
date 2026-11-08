from ktt112026.config import Settings


def test_settings_defaults_and_invalid_numbers():
    settings = Settings.from_env({"DISCORD_TOKEN": " token ", "KTT_VOICE_KEEPALIVE_SECONDS": "bad"})
    assert settings.discord_token == "token"
    assert settings.command_prefix == "."
    assert settings.voice_keepalive_seconds == 45
    assert settings.voice_channel_id == 0
    assert settings.voice_self_deaf is True
    invalid_bool = Settings.from_env({"KTT_VOICE_SELF_DEAF": "maybe"})
    assert invalid_bool.voice_self_deaf is True


def test_settings_parse_voice_and_limits():
    settings = Settings.from_env({
        "DISCORD_TOKEN": "abc",
        "KTT_VOICE_CHANNEL_ID": "12345",
        "KTT_VOICE_SELF_DEAF": "false",
        "KTT_MAX_MUSIC_QUEUE": "25",
        "KTT_MAX_TTS_CHARS": "420",
        "KTT_LOG_LEVEL": "debug",
    })
    assert settings.voice_channel_id == 12345
    assert settings.voice_self_deaf is False
    assert settings.max_music_queue == 25
    assert settings.max_tts_chars == 420
    assert settings.log_level == "DEBUG"
