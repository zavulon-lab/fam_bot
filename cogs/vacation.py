import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, ButtonStyle, TextInputStyle
from disnake.ui import View, TextInput, Button, button, Modal
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import *
from database import save_vacation_data, get_vacation_data, delete_vacation_data


class VacationModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Игровой ник", custom_id="vacation_nick", style=TextInputStyle.short, required=True, placeholder="Alexis Superior", max_length=32),
            TextInput(label="Сроки (с - по)", custom_id="vacation_date", style=TextInputStyle.short, required=True, placeholder="01.01 - 07.01", max_length=50),
            TextInput(label="Причина", custom_id="vacation_reason", style=TextInputStyle.paragraph, required=True, placeholder="Отдых / Учеба", max_length=200)
        ]
        super().__init__(title="Заявка на отпуск", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        
        nick = interaction.text_values["vacation_nick"]
        date_range = interaction.text_values["vacation_date"]
        reason = interaction.text_values["vacation_reason"]
        user = interaction.user
        guild = interaction.guild
        me = guild.me 

        roles_to_save_ids = []
        roles_to_remove = []

        for role in user.roles:
            if role.is_default() or role.is_premium_subscriber() or role.managed:
                continue
            
            roles_to_save_ids.append(role.id)

            if role.position < me.top_role.position:
                roles_to_remove.append(role)
        
        save_vacation_data(str(user.id), roles_to_save_ids, date_range, date_range, reason)
        
        try:
            if roles_to_remove:
                await user.remove_roles(*roles_to_remove, reason="Уход в отпуск")
            
            inactive_role = guild.get_role(INACTIVE_ROLE_ID)
            if inactive_role:
                if inactive_role.position < me.top_role.position:
                    await user.add_roles(inactive_role, reason="Уход в отпуск")
                else:
                    await interaction.followup.send("Ошибка: Роль 'Отпуск' выше роли бота. Обратитесь к администратору.", ephemeral=True)
                    return
            
            log_channel = guild.get_channel(VACATION_LOG_CHANNEL_ID)
            if log_channel:
                embed_log = Embed(title="<:freeiconcoconuttree3226180:1472661945537789963> Уход в отпуск", color=disnake.Color.from_rgb(54, 57, 63), timestamp=datetime.now())
                embed_log.add_field(name="Пользователь", value=f"{user.mention}\nID: {user.id}", inline=False)
                embed_log.add_field(name="Ник", value=nick, inline=True)
                embed_log.add_field(name="Сроки", value=date_range, inline=True)
                embed_log.add_field(name="Причина", value=reason, inline=False)
                
                skipped_roles = [r.name for r in user.roles if r.id in roles_to_save_ids and r not in roles_to_remove]
                if skipped_roles:
                     embed_log.add_field(name=" Не сняты (выше бота)", value=", ".join(skipped_roles), inline=False)

                await log_channel.send(embed=embed_log)
            
            await interaction.followup.send(embed=Embed(description="Вы успешно ушли в отпуск. Роли сохранены.", color=disnake.Color.from_rgb(54, 57, 63)), ephemeral=True)
            
        except disnake.Forbidden:
            await interaction.followup.send(embed=Embed(description="Ошибка прав доступа (403). Поднимите роль бота выше в настройках сервера!", color=disnake.Color.from_rgb(54, 57, 63)), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"Ошибка: {e}", color=disnake.Color.from_rgb(54, 57, 63)), ephemeral=True)


class VacationActionsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Взять отпуск", style=ButtonStyle.primary, custom_id="vacation_take", emoji="<:freeiconcoconuttree3226180:1472661945537789963>")
    async def take_vacation(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(VacationModal())

    @button(label="Вернуться", style=ButtonStyle.success, custom_id="vacation_return", emoji="<:freeiconhistory1800170:1472662096696049916>")
    async def return_vacation(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        me = guild.me
        
        role_ids = get_vacation_data(str(user.id))
        
        if role_ids is None:
            await interaction.followup.send(embed=Embed(description="Вы не числитесь в отпуске в базе данных.", color=0xFFA500), ephemeral=True)
            return
            
        roles_to_add = []
        for rid in role_ids:
            role = guild.get_role(rid)
            if role and role.position < me.top_role.position:
                roles_to_add.append(role)
        
        try:
            if roles_to_add:
                await user.add_roles(*roles_to_add, reason="Возврат из отпуска")
            
            inactive_role = guild.get_role(INACTIVE_ROLE_ID)
            if inactive_role and inactive_role in user.roles:
                if inactive_role.position < me.top_role.position:
                    await user.remove_roles(inactive_role, reason="Возврат из отпуска")
                
            delete_vacation_data(str(user.id))
            
            log_channel = guild.get_channel(VACATION_LOG_CHANNEL_ID)
            if log_channel:
                embed_log = Embed(title="<:freeiconhistory1800170:1472662096696049916> Возвращение", color=disnake.Color.from_rgb(54, 57, 63), timestamp=datetime.now())
                embed_log.add_field(name="Пользователь", value=f"{user.mention} вернулся в строй.")
                await log_channel.send(embed=embed_log)

            await interaction.followup.send(embed=Embed(description="Вы вернулись из отпуска. Роли выданы.", color=disnake.Color.from_rgb(54, 57, 63)), ephemeral=True)
            
        except disnake.Forbidden:
            await interaction.followup.send(embed=Embed(description="Ошибка прав (403). Бот не может выдать роли, которые выше его роли.", color=disnake.Color.from_rgb(54, 57, 63)), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"Ошибка при выдаче ролей: {e}", color=disnake.Color.from_rgb(54, 57, 63)), ephemeral=True)


class VacationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(VacationCog(bot))
