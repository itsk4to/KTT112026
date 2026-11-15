"""Độ Kiếp — image + 3 choice buttons."""
from __future__ import annotations

from io import BytesIO

import discord

from ktt112026.game.services.dokiep_service import DokiepService
from ktt112026.game.render.cards import render_dokiep_card


def _file(png: bytes, name: str = "dokiep.png") -> discord.File:
    return discord.File(BytesIO(png), filename=name)


class DokiepView(discord.ui.View):
    def __init__(self, service: DokiepService, owner_id: int, timeout: float = 300) -> None:
        super().__init__(timeout=timeout)
        self.service = service
        self.owner_id = owner_id
        sess = service.session(str(owner_id))
        if sess is not None:
            self.sync_removed(sess.current_hint()["removed"])

    def sync_removed(self, removed: list[int]) -> None:
        """Khóa nút của đáp án đã bị loại ở vòng hiện tại."""
        for i, c in enumerate(self.children[:3]):
            if isinstance(c, discord.ui.Button):
                c.disabled = i in removed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Không phải Lôi Kiếp của đạo hữu.", ephemeral=True)
            return False
        return True

    async def _pick(self, interaction: discord.Interaction, choice: int) -> None:
        try:
            result = self.service.choose(str(self.owner_id), choice)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        sess = result["session"]
        if sess.finished:
            png = render_dokiep_card(
                round_no=5, shields=sess.shields, message=result["message"],
                finished=True, success=sess.success,
            )
            for c in self.children:
                if isinstance(c, discord.ui.Button):
                    c.disabled = True
            await interaction.response.edit_message(attachments=[_file(png)], view=self)
            return
        prompt = sess.prompt()
        self.sync_removed(prompt["removed"])
        png = render_dokiep_card(
            round_no=prompt["round"], shields=prompt["shields"],
            message=result["message"], options=prompt["options"],
            removed=prompt["removed"], notes=prompt["notes"],
        )
        await interaction.response.edit_message(attachments=[_file(png)], view=self)

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary, row=0)
    async def b1(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._pick(interaction, 0)

    @discord.ui.button(label="2", style=discord.ButtonStyle.primary, row=0)
    async def b2(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._pick(interaction, 1)

    @discord.ui.button(label="3", style=discord.ButtonStyle.primary, row=0)
    async def b3(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._pick(interaction, 2)
