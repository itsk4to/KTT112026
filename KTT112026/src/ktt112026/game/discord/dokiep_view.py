"""Độ Kiếp buttons — maps visible slots 1..n."""
from __future__ import annotations

import discord
from discord.ext import commands

from ktt112026.game.render.cards import render_dokiep_card
from ktt112026.game.services.dokiep_service import DokiepService


class DokiepView(discord.ui.View):
    def __init__(self, service: DokiepService, owner_id: int, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.service = service
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Không phải Lôi Kiếp của đạo hữu.", ephemeral=True)
            return False
        return True

    async def _pick(self, interaction: discord.Interaction, slot: int) -> None:
        try:
            result = self.service.choose(str(self.owner_id), slot)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        sess = result["session"]
        if sess.finished:
            png = render_dokiep_card(
                round_no=5,
                shields=sess.shields,
                message=result["message"],
                finished=True,
                success=sess.success,
                hints=sess.hints,
            )
            file = discord.File(__import__("io").BytesIO(png), filename="dokiep.png")
            await interaction.response.edit_message(attachments=[file], view=None)
            self.stop()
            return
        prompt = sess.prompt()
        png = render_dokiep_card(
            round_no=prompt["round"],
            shields=prompt["shields"],
            message=result["message"],
            options=prompt["options"],
            hints=prompt["hints"],
        )
        file = discord.File(__import__("io").BytesIO(png), filename="dokiep.png")
        # rebuild buttons for visible count
        self.clear_items()
        for i in range(len(prompt["options"])):
            self.add_item(_ChoiceButton(i, str(i + 1)))
        await interaction.response.edit_message(attachments=[file], view=self)

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary, row=0)
    async def b1(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._pick(interaction, 0)

    @discord.ui.button(label="2", style=discord.ButtonStyle.primary, row=0)
    async def b2(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._pick(interaction, 1)

    @discord.ui.button(label="3", style=discord.ButtonStyle.primary, row=0)
    async def b3(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._pick(interaction, 2)


class _ChoiceButton(discord.ui.Button):
    def __init__(self, slot: int, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0)
        self.slot = slot

    async def callback(self, interaction: discord.Interaction) -> None:
        view: DokiepView = self.view  # type: ignore
        await view._pick(interaction, self.slot)
