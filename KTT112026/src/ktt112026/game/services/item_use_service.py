"""Use consumables (.dung [n]) driven by danduoc.json effects."""
from __future__ import annotations

from datetime import date
from typing import Any

from ktt112026.game.content.loader import load_danduoc
from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.models.player import STAT_HARD_CAP
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num

ROOT_ORDER = ["tap", "chan", "dia", "thien", "hon_don"]


class ItemUseService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self._pills = {x["id"]: x for x in load_danduoc()}

    def use(self, user_id: str, item_id: str, qty: int = 1) -> dict[str, Any]:
        item_id = item_id.strip().lower()
        qty = max(1, min(50, int(qty)))
        pill = self._pills.get(item_id)
        if pill is None:
            raise ValueError("Chỉ dùng được đan dược trong danh mục. Ví dụ: `.dung linhdan 3`.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        have = self.repo.inventory_qty(user_id, item_id)
        if have < 1:
            raise ValueError("Túi không có đan này.")
        if p.major_realm < int(pill.get("major_min", 1)):
            raise ValueError("Cảnh giới chưa đủ để dùng đan này.")

        limits = pill.get("limits") or {}
        usage = self.repo.get_use_limit(user_id, item_id)
        today = date.today().isoformat()
        day_count = usage["day_count"] if usage["day_key"] == today else 0
        if "per_day" in limits:
            remain = max(0, int(limits["per_day"]) - day_count)
            if remain <= 0:
                raise ValueError(f"Hôm nay đã dùng tối đa {limits['per_day']} viên.")
            qty = min(qty, remain)
        if "per_life" in limits:
            remain = max(0, int(limits["per_life"]) - int(usage["life_count"]))
            if remain <= 0:
                raise ValueError(f"Đã đạt giới hạn đời ({limits['per_life']} viên).")
            qty = min(qty, remain)
        qty = min(qty, have)

        all_msgs: list[str] = []
        used = 0
        for _ in range(qty):
            msgs = self._apply_one(p, pill)
            all_msgs.extend(msgs)
            used += 1
            self.repo.bump_use_limit(
                user_id,
                item_id,
                day="per_day" in limits,
                life="per_life" in limits,
            )

        if not self.repo.inventory_remove(user_id, item_id, used):
            raise ValueError("Không trừ được đan trong túi.")
        self.repo.save(p)
        # compress messages
        summary = f"Đã dùng {used}× {pill.get('name', item_id)}"
        return {
            "item": pill,
            "qty": used,
            "messages": [summary] + all_msgs[:6],
            "player": p,
        }

    def _apply_one(self, p, pill: dict) -> list[str]:
        effect = pill.get("effect") or {}
        etype = effect.get("type")
        messages: list[str] = []

        if etype == "cultivation_flat":
            need = stage_requirement(p.major_realm, p.minor_stage)
            amt = int(effect.get("amount", 0))
            before = p.cultivation
            p.cultivation = min(need, p.cultivation + amt)
            messages.append(f"+{fmt_num(p.cultivation - before)} Tu Vi")
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
            messages.append(f"+{p.cultivate_bonus_pct}% Tu Vi khi `.tu` ({p.cultivate_bonus_charges} lần)")
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
            messages.append("Hồi phục căn cơ (ngoài trận)")
        elif etype == "dokiep_shield_bonus":
            p.dokiep_extra_shield = min(5, p.dokiep_extra_shield + int(effect.get("amount", 1)))
            messages.append(f"+{effect.get('amount', 1)} Hộ Thể cho lần `.dokiep` tới")
        elif etype == "dokiep_remove_wrong":
            p.dokiep_remove_wrong = max(p.dokiep_remove_wrong, 1)
            messages.append("Loại đáp án sai khi `.dokiep`")
        elif etype == "dokiep_remove_wrong_all_rounds":
            p.dokiep_remove_wrong = max(p.dokiep_remove_wrong, int(effect.get("amount", 1)))
            messages.append("Loại đáp án sai mọi vòng `.dokiep`")
        elif etype == "dokiep_fail_loss_pct":
            p.dokiep_fail_loss_pct = int(effect.get("amount", 5))
            messages.append(f"Thất bại chỉ mất {p.dokiep_fail_loss_pct}% Tu Vi")
        elif etype == "dokiep_first_miss_immune_and_shield":
            p.dokiep_first_immune = 1
            p.dokiep_extra_shield = min(5, p.dokiep_extra_shield + int(effect.get("shield", 1)))
            messages.append("Miễn lần sai đầu + khiên khi `.dokiep`")
        elif etype == "dokiep_damage_reduce_pct":
            p.dokiep_extra_shield = min(5, p.dokiep_extra_shield + 1)
            messages.append(f"Hộ Tâm: +1 Hộ Thể (giảm {effect.get('amount', 20)}% áp lực lôi)")
        elif etype and str(etype).startswith("dokiep"):
            messages.append("Đan Độ Kiếp đã ghi nhận cho lần `.dokiep` tới")
        else:
            messages.append(f"Đã dùng — hiệu ứng `{etype}` được ghi nhận")

        for se in pill.get("side_effects") or []:
            if se.get("permanent") and se.get("stat") in ("can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van"):
                stat = se["stat"]
                delta = int(se.get("delta", 0))
                cur = getattr(p.stats, stat)
                setattr(p.stats, stat, max(1, min(STAT_HARD_CAP, cur + delta)))
                messages.append(f"phụ: {stat} {delta:+d}")
        return messages
