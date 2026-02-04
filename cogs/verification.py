import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, ButtonStyle, TextInputStyle, SelectOption
from disnake.ui import View, Select, TextInput, Button, button, Modal
from datetime import datetime
from constants import *

# === ВАШИ КЛАССЫ (БЕЗ ИЗМЕНЕНИЙ) ===

class VerificationFinalDecisionView(View):
    def __init__(self, user: disnake.User):
        super().__init__(timeout=None)
        self.user = user

    @button(label="✅ Подтвердить (Выдать роль)", style=ButtonStyle.success, custom_id="final_accept")
    async def final_accept(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            role = interaction.guild.get_role(VERIFIED_ROLE_ID)
            if role:
                await self.user.add_roles(role, reason="Верификация пройдена")
                
                await interaction.followup.send(
                    embed=Embed(description=f"✅ Роль {role.mention} успешно выдана пользователю {self.user.mention}!", color=0x3BA55D),
                    ephemeral=True
                )
                
                embed_notify = Embed(
                    title="✅ Верификация успешна",
                    description=f"Поздравляем! Вы успешно прошли проверку и получили доступ к серверу.",
                    color=0x3BA55D,
                    timestamp=datetime.now()
                )
                embed_notify.set_thumbnail(url=self.user.display_avatar.url)
                notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
                if notification_channel:
                    await notification_channel.send(content=self.user.mention, embed=embed_notify)

                log_channel = interaction.guild.get_channel(VERIFICATION_LOG_CHANNEL_ID)
                if log_channel:
                    embed_log = Embed(title="✅ Верификация: ОДОБРЕНО", color=0x3BA55D, timestamp=datetime.now())
                    embed_log.add_field(name="Пользователь", value=f"{self.user.mention}\n`{self.user.id}`", inline=True)
                    embed_log.add_field(name="Администратор", value=interaction.user.mention, inline=True)
                    await log_channel.send(embed=embed_log)
            else:
                await interaction.followup.send(
                    embed=Embed(description="❌ Ошибка: Роль VERIFIED_ROLE_ID не найдена в настройках.", color=0xFF0000),
                    ephemeral=True
                )
            
            for child in self.children: child.disabled = True
            await interaction.edit_original_response(view=self)
            
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"❌ Ошибка выдачи роли: {e}", color=0xFF0000), ephemeral=True)

    @button(label="❌ Отказать после проверки", style=ButtonStyle.danger, custom_id="final_reject")
    async def final_reject(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
        if notification_channel:
            embed = Embed(
                title="❌ Верификация отклонена",
                description=f"К сожалению, вы не прошли проверку.",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            await notification_channel.send(content=self.user.mention, embed=embed)

        log_channel = interaction.guild.get_channel(VERIFICATION_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = Embed(title="❌ Верификация: ОТКАЗАНО (После проверки)", color=0xFF0000, timestamp=datetime.now())
            embed_log.add_field(name="Пользователь", value=f"{self.user.mention}\n`{self.user.id}`", inline=True)
            embed_log.add_field(name="Администратор", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=embed_log)

        await interaction.followup.send(embed=Embed(description=f"❌ Верификация {self.user.mention} отклонена.", color=0xFF0000), ephemeral=True)
        for child in self.children: child.disabled = True
        await interaction.edit_original_response(view=self)

class VerificationAdminButtons(View):
    def __init__(self, user: disnake.User):
        super().__init__(timeout=None)
        self.user = user

    @button(label="✅ Принять (Вызвать на проверку)", style=ButtonStyle.success, custom_id="accept_verif")
    async def accept(self, button: Button, interaction: Interaction):
        is_allowed = interaction.user.guild_permissions.administrator or \
                     any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)
        if not is_allowed:
            await interaction.response.send_message(embed=Embed(description="❌ У вас нет прав!", color=0xFF0000), ephemeral=True)
            return

        notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
        voice_channel = interaction.guild.get_channel(VOICE_CHANNEL_ID)

        if not notification_channel:
            await interaction.response.send_message(embed=Embed(description="❌ Канал уведомлений не настроен!", color=0xFF0000), ephemeral=True)
            return

        embed = Embed(
            title="📞 Вызов на проверку",
            description=(
                "Ваша заявка рассмотрена. Вас вызывают на устную проверку.\n\n"
                f"🔽 **Пожалуйста, подключитесь к голосовому каналу:**\n"
                f"🔊 {voice_channel.mention if voice_channel else 'Voice Channel'}\n\n"
                "Ожидайте подключения администратора."
            ),
            color=0x3A3B3C,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=self.user.display_avatar.url)
        await notification_channel.send(content=self.user.mention, embed=embed)

        await interaction.response.send_message(
            embed=Embed(description=f"✅ Вызов отправлен {self.user.mention}. Проведите проверку и выберите решение ниже.", color=0x3BA55D),
            view=VerificationFinalDecisionView(self.user),
            ephemeral=True
        )

        for child in self.children: child.disabled = True
        await interaction.message.edit(view=self)

    @button(label="❌ Отказать", style=ButtonStyle.danger, custom_id="reject_verif")
    async def reject(self, button: Button, interaction: Interaction):
        is_allowed = interaction.user.guild_permissions.administrator or \
                     any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)
        if not is_allowed:
            await interaction.response.send_message(embed=Embed(description="❌ У вас нет прав!", color=0xFF0000), ephemeral=True)
            return

        notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
        if notification_channel:
            embed = Embed(
                title="❌ Верификация отклонена",
                description=f"Ваша заявка на верификацию была отклонена администрацией.",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            await notification_channel.send(content=self.user.mention, embed=embed)

        log_channel = interaction.guild.get_channel(VERIFICATION_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = Embed(title="❌ Верификация: ОТКАЗАНО (По заявке)", color=0xFF0000, timestamp=datetime.now())
            embed_log.add_field(name="Пользователь", value=f"{self.user.mention}\n`{self.user.id}`", inline=True)
            embed_log.add_field(name="Администратор", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=embed_log)

        await interaction.response.send_message(embed=Embed(description="❌ Заявка отклонена.", color=0xFF0000), ephemeral=True)
        for child in self.children: child.disabled = True
        await interaction.message.edit(view=self)

class VerificationRequestModal(Modal):
    def __init__(self, message_to_reset: disnake.Message = None):
        self.message_to_reset = message_to_reset
        components = [
            TextInput(
                label="Причина запроса",
                custom_id="reason",
                style=TextInputStyle.paragraph,
                required=True,
                placeholder="Опишите, почему вы хотите получить верификацию...",
                max_length=500
            )
        ]
        super().__init__(title="Запрос верификации", components=components, timeout=300)

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        
        if self.message_to_reset:
            try: await self.message_to_reset.edit(view=VerificationView())
            except: pass 

        reason = interaction.text_values["reason"]
        admin_channel = interaction.guild.get_channel(VERIFICATION_ADMIN_CHANNEL_ID)
        
        if not admin_channel:
            await interaction.followup.send(embed=Embed(description="❌ Админский канал не найден!", color=0xFF0000), ephemeral=True)
            return

        embed = Embed(
            title="🔔 Новый запрос на верификацию",
            description=(
                f"**Пользователь:** {interaction.user.mention}\n"
                f"**ID:** `{interaction.user.id}`\n"
                f"**Дата регистрации:** {interaction.user.created_at.strftime('%d.%m.%Y')}\n\n"
                f"**Причина запроса:**\n{reason}"
            ),
            color=0x3A3B3C,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Запрос от {interaction.user.display_name}")

        await admin_channel.send(embed=embed, view=VerificationAdminButtons(interaction.user))
        await interaction.followup.send(
            embed=Embed(
                title="✅ Запрос отправлен!",
                description="Ваш запрос передан администрации. Ожидайте уведомления о вызове на проверку.",
                color=0x3BA55D
            ),
            ephemeral=True
        )

class VerificationSelect(Select):
    def __init__(self):
        options = [
            SelectOption(label="Подать запрос на верификацию", value="request_verify", description="Нажмите, чтобы заполнить анкету", emoji="📝")
        ]
        super().__init__(placeholder="Выберите действие...", min_values=1, max_values=1, options=options, custom_id="verif_select")

    async def callback(self, interaction: Interaction):
        if self.values[0] == "request_verify":
            await interaction.response.send_modal(VerificationRequestModal(interaction.message))

class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerificationSelect())

# === ДОБАВЛЕНО: КЛАСС COG ДЛЯ ЗАГРУЗКИ ===
class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Автоматическая отправка меню в канал запросов
        channel = self.bot.get_channel(VERIFICATION_REQUEST_CHANNEL_ID)
        if channel:
            await channel.purge(limit=10)
            embed = Embed(
                title="Верификация",
                description="Для получения доступа к каналам сервера необходимо пройти верификацию.",
                color=0x2B2D31
            )
            await channel.send(embed=embed, view=VerificationView())
            print("[Verification] Меню верификации обновлено.")

def setup(bot):
    bot.add_cog(VerificationCog(bot))
