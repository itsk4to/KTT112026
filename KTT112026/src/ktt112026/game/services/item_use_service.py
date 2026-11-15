"""Use consumables (.dung) driven by danduoc.json effects."""
from __future__ import annotations

from datetime import date

from ktt112026.game.services._tx import atomic
from ktt112026.game.content.loader import load_danduoc
from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.models.player import STAT_HARD_CAP
from ktt112026.game.repo.players import PlayerRepository

ROOT_ORDER = ["tap", "chan", "dia", "thien", "hon_don"]


class ItemUseService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self._pills = {x["id"]: x for x in load_danduoc()}

    @atomic
    def use(self, user_id: str, item_id: str) -> dict:
        item_id = item_id.strip().lower()
        pill = self._pills.get(item_id)
        if pill is None:
            raise ValueError("Chỉ dùng được đan dược trong danh mục (`.dung <ma_do>`).")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if self.repo.inventory_qty(user_id, item_id) < 1:
            raise ValueError("Túi không có đan này.")
        if p.major_realm < int(pill.get("major_min", 1)):
            raise ValueError("Cảnh giới chưa đủ để dùng đan này.")

        limits = pill.get("limits") or {}
        usage = self.repo.get_use_limit(user_id, item_id)
        today = date.today().isoformat()
        day_count = usage["day_count"] if usage["day_key"] == today else 0
        if "per_day" in limits and day_count >= int(limits["per_day"]):
            raise ValueError(f"Hôm nay đã dùng tối đa {limits['per_day']} viên.")
        if "per_life" in limits and usage["life_count"] >= int(limits["per_life"]):
            raise ValueError(f"Đã đạt giới hạn đời ({limits['per_life']} viên).")

        effect = pill.get("effect") or {}
        etype = effect.get("type")
        messages: list[str] = []

        if etype == "cultivation_flat":
            need = stage_requirement(p.major_realm, p.minor_stage)
            amt = int(effect.get("amount", 0))
            before = p.cultivation
            p.cultivation = min(need, p.cultivation + amt)
            messages.append(f"+{p.cultivation - before:,} Tu Vi")
        elif etype == "stamina_flat":
            amt = int(effect.get("amount", 0))
            before = p.stamina
            p.stamina = min(p.max_stamina, p.stamina + amt)
            messages.append(f"+{p.stamina - before} Thể Lực")
        elif etype == "stat_permanent":
            for stat in ("can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van"):
                if stat in effect:
                    delta = int(effect[stat])
                    cur = getattr(p.stats, stat)
                    setattr(p.stats, stat, max(1, min(STAT_HARD_CAP, cur + delta)))
                    messages.append(f"{stat} {delta:+d}")
        elif etype == "cultivate_bonus_pct":
            p.cultivate_bonus_pct = int(effect.get("amount", 0))
            p.cultivate_bonus_charges = int(effect.get("charges", 0))
            messages.append(f"+{p.cultivate_bonus_pct}% Tu Vi .tu ({p.cultivate_bonus_charges} lần)")
        elif etype == "root_quality_up":
            import random
            rate = float(effect.get("success_rate", 0.5))
            if random.random() <= rate:
                idx = ROOT_ORDER.index(p.root_quality) if p.root_quality in ROOT_ORDER else 0
                if idx < len(ROOT_ORDER) - 1:
                    p.root_quality = ROOT_ORDER[idx + 1]
                    messages.append(f"Linh căn lên {p.root_quality}")
                else:
                    messages.append("Linh căn đã tối đa")
            else:
                messages.append("Tịnh hóa thất bại (mất đan)")
        elif etype == "heal_full_out_of_combat":
            messages.append("Hồi phục căn cơ (HP/MP ngoài trận — placeholder)")
        elif str(etype).startswith("dokiep_"):
            # Hiệu lực ở lần `.dokiep` kế tiếp (một lần). Dùng lại đan cùng loại sẽ ghi đè, không cộng dồn.
            self.repo.buff_set(user_id, str(etype), dict(effect))
            messages.append("Đã kích hoạt — có hiệu lực ở lần `.dokiep` kế tiếp")
        else:
            # combat buffs: acknowledge consume, full combat later
            messages.append(f"Đã dùng — hiệu ứng `{etype}` được ghi nhận (combat sẽ kích hoạt khi hệ đó mở đầy đủ)")

        # permanent side effects on stats
        for se in pill.get("side_effects") or []:
            if se.get("permanent") and se.get("stat") in ("can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van"):
                stat = se["stat"]
                delta = int(se.get("delta", 0))
                cur = getattr(p.stats, stat)
                setattr(p.stats, stat, max(1, min(STAT_HARD_CAP, cur + delta)))
                messages.append(f"phụ: {stat} {delta:+d}")

        if not self.repo.inventory_remove(user_id, item_id, 1):
            raise ValueError("Không trừ được đan trong túi.")
        self.repo.save(p)
        self.repo.bump_use_limit(
            user_id,
            item_id,
            day="per_day" in limits,
            life="per_life" in limits,
        )
        return {"item": pill, "messages": messages, "player": p}
