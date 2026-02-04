import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, ButtonStyle, TextInputStyle
from disnake.ui import View, TextInput, Button, button, Modal
from datetime import datetime
from constants import *
from database import save_vacation_data, get_vacation_data, delete_vacation_data

class VacationModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Игровой ник", custom_id="vacation_nick", style=TextInputStyle.short, required=True, placeholder="Vladislav Cartel", max_length=32),
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
        
        roles_to_save = [role.id for role in user.roles if role.name != "@everyone" and not role.is_premium_subscriber() and not role.managed]
        save_vacation_data(str(user.id), roles_to_save, date_range, date_range, reason)
        
        try:
            roles_objects = [guild.get_role(rid) for rid in roles_to_save if guild.get_role(rid)]
            if roles_objects:
                await user.remove_roles(*roles_objects, reason="Уход в отпуск")
            
            inactive_role = guild.get_role(INACTIVE_ROLE_ID)
            if inactive_role: 
                await user.add_roles(inactive_role, reason="Уход в отпуск")
            
            log_channel = guild.get_channel(VACATION_LOG_CHANNEL_ID)
            if log_channel:
                embed_log = Embed(title="🏖️ Уход в отпуск", color=0xFFA500, timestamp=datetime.now())
                embed_log.add_field(name="Пользователь", value=f"{user.mention} ({user.id})")
                embed_log.add_field(name="Ник", value=nick, inline=True)
                embed_log.add_field(name="Сроки", value=date_range, inline=True)
                embed_log.add_field(name="Причина", value=reason, inline=False)
                await log_channel.send(embed=embed_log)
            
            await interaction.followup.send(embed=Embed(description="✅ Вы успешно ушли в отпуск. Роли сохранены.", color=0x3BA55D), ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"❌ Ошибка: {e}", color=0xFF0000), ephemeral=True)

# !!! ПЕРЕИМЕНОВАЛ КЛАСС, ЧТОБЫ СОВПАДАЛ С ИМПОРТОМ В PERSONAL.PY !!!
class VacationActionsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Взять отпуск", style=ButtonStyle.primary, custom_id="vacation_take", emoji="🏖️")
    async def take_vacation(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(VacationModal())

    @button(label="Вернуться", style=ButtonStyle.success, custom_id="vacation_return", emoji="🔙")
    async def return_vacation(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        
        # get_vacation_data возвращает СПИСОК ID ролей (например: [123456, 789012])
        role_ids = get_vacation_data(str(user.id))
        
        if role_ids is None: # Проверка на None, так как пустой список [] это тоже валидные данные
            await interaction.followup.send(embed=Embed(description="⚠️ Вы не числитесь в отпуске в базе данных.", color=0xFFA500), ephemeral=True)
            return
            
        # Убрали data['roles'], используем сразу role_ids
        roles_to_add = [guild.get_role(rid) for rid in role_ids if guild.get_role(rid)]
        
        try:
            if roles_to_add:
                await user.add_roles(*roles_to_add, reason="Возврат из отпуска")
            
            inactive_role = guild.get_role(INACTIVE_ROLE_ID)
            if inactive_role and inactive_role in user.roles:
                await user.remove_roles(inactive_role, reason="Возврат из отпуска")
                
            delete_vacation_data(str(user.id))
            
            log_channel = guild.get_channel(VACATION_LOG_CHANNEL_ID)
            if log_channel:
                embed_log = Embed(title="🔄 Возвращение", color=0x3BA55D, timestamp=datetime.now())
                embed_log.add_field(name="Пользователь", value=f"{user.mention} вернулся в строй.")
                await log_channel.send(embed=embed_log)

            await interaction.followup.send(embed=Embed(description="✅ Вы вернулись из отпуска. Роли выданы.", color=0x3BA55D), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"❌ Ошибка при выдаче ролей: {e}", color=0xFF0000), ephemeral=True)


class VacationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # on_ready здесь можно убрать, так как меню вызывается из personal.py
    # Но если нужен отдельный лог-канал с панелью, можно оставить.
    
def setup(bot):
    bot.add_cog(VacationCog(bot))
