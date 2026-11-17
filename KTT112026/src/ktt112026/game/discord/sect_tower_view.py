"""Sect tower continue / retreat."""
from __future__ import annotations

from io import BytesIO

import discord

from ktt112026.game.render.cards import render_tower_card
from ktt112026.game.services.sect_tower_service import SectTowerService


def _file(png: bytes) -> discord.File:
    return discord.File(BytesIO(png), filename="tongthap.png")


class SectTowerView(discord.ui.View):
    def __init__(self, service: SectTowerService, owner_id: int, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.service = service
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Không phải lượt của đạo hữu.", ephemeral=True)
            return False
        return True

    def _card(self, run, message: str):
        return render_tower_card(
            floor=run.floor, risk=run.risk, stones=run.bag_stones,
            cult=run.bag_contrib, alive=run.alive, message=message[:180],
        )

    @discord.ui.button(label="Tiếp tục", style=discord.ButtonStyle.danger, row=0)
    async def cont(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            run = self.service.advance(str(self.owner_id), continue_=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        log = " | ".join(run.last_log[-2:]) if run.last_log else run.risk
        png = self._card(run, log if run.alive else run.risk)
        if not run.alive:
            for c in self.children:
                if isinstance(c, discord.ui.Button):
                    c.disabled = True
        await interaction.response.edit_message(attachments=[_file(png)], view=self)

    @discord.ui.button(label="Rút lui", style=discord.ButtonStyle.success, row=0)
    async def retreat(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            run = self.service.advance(str(self.owner_id), continue_=False)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        for c in self.children:
            if isinstance(c, discord.ui.Button):
                c.disabled = True
        png = self._card(run, run.risk)
        await interaction.response.edit_message(attachments=[_file(png)], view=self)
