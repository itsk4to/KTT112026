"""Pure rules — no Discord I/O."""
from ktt112026.game.rules.cultivation import can_auto_advance_minor, clamp, cultivation_gain

__all__ = ["cultivation_gain", "can_auto_advance_minor", "clamp"]
