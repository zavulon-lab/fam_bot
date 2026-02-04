import disnake
from disnake import Embed, Interaction, ButtonStyle, TextInputStyle, SelectOption
from disnake.ui import View, Select, TextInput, Button, button, Modal
from datetime import datetime
from constants import *
from database import save_vacation_data, get_vacation_data, delete_vacation_data

class VacationModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Игровой ник", custom_id="vacation_nick", style=TextInputStyle.short, required=True, placeholder="Vladislav Cartel", max_length=32),
            TextInput(label="До какого числа вы берете отпуск?", custom_id="vacation_date", style=TextInputStyle.short, required=True, placeholder="Беру отпуск с 01.01 до 07.01", max_length=50),
            TextInput(label="Причина ухода в отпуск?", custom_id="vacation_reason", style=TextInputStyle.paragraph, required=True, placeholder="Отдых от игры", max_length=200)
        ]
        super().__init__(title="Подать заявку на отпуск", components=components)

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
            
            try:
                dm_embed = Embed(
                    title="✅ Заявка одобрена",
                    description="Ваша заявка на отпуск принята. Роли сохранены.\nЖелаем хорошего отдыха! 🏖️",
                    color=0x3BA55D
                )
                await user.send(embed=dm_embed)
            except: pass 
            
            role_mention = inactive_role.mention if inactive_role else "@Inactive"
            await interaction.followup.send(embed=Embed(description=f"✅ Вы успешно ушли в отпуск. Роль {role_mention} выдана.", color=0x3BA55D), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"❌ Ошибка при смене ролей: {e}", color=0xFF0000), ephemeral=True)

class VacationActionsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Подать заявку на отпуск", style=ButtonStyle.secondary, emoji="📝", custom_id="btn_apply_vacation")
    async def apply_vacation(self, button: Button, interaction: Interaction):
        if get_vacation_data(str(interaction.user.id)):
            await interaction.response.send_message(embed=Embed(description="⚠️ Вы уже находитесь в отпуске!", color=0xFFA500), ephemeral=True)
            return
        await interaction.response.send_modal(VacationModal())

    @button(label="Вернуться из отпуска", style=ButtonStyle.success, emoji="🔄", custom_id="btn_return_vacation")
    async def return_vacation(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        saved_roles_ids = get_vacation_data(str(user.id))
        
        if not saved_roles_ids:
            await interaction.followup.send(embed=Embed(description="⚠️ Вы не числитесь в отпуске (нет данных в БД).", color=0xFFA500), ephemeral=True)
            return

        try:
            roles_to_add = [guild.get_role(rid) for rid in saved_roles_ids if guild.get_role(rid)]
            if roles_to_add: await user.add_roles(*roles_to_add, reason="Возвращение из отпуска")

            inactive_role = guild.get_role(INACTIVE_ROLE_ID)
            if inactive_role and inactive_role in user.roles: await user.remove_roles(inactive_role, reason="Возвращение из отпуска")
            
            delete_vacation_data(str(user.id))

            log_channel = guild.get_channel(VACATION_LOG_CHANNEL_ID)
            if log_channel:
                embed_log = Embed(title="🔄 Возвращение из отпуска", color=0x3BA55D, timestamp=datetime.now())
                embed_log.add_field(name="Пользователь", value=f"{user.mention} ({user.id})")
                embed_log.add_field(name="Ролей восстановлено", value=str(len(roles_to_add)))
                await log_channel.send(embed=embed_log)

            await interaction.followup.send(embed=Embed(description=f"✅ С возвращением! Ваши роли ({len(roles_to_add)} шт.) восстановлены.", color=0x3BA55D), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"❌ Ошибка при восстановлении ролей: {e}", color=0xFF0000), ephemeral=True)
