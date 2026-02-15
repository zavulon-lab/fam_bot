import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, ButtonStyle, TextInputStyle, PermissionOverwrite
from disnake.ui import View, TextInput, Button, button, Modal
from datetime import datetime
from constants import *
import asyncio




class VerificationFinalDecisionView(View):
    def __init__(self, user: disnake.User):
        super().__init__(timeout=None)
        self.user = user

    async def _close_channel(self, interaction: Interaction):
       
        await interaction.channel.send("**Канал будет удален через 5 секунд...**")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except disnake.NotFound:
            pass
        except Exception as e:
            pass 

    @button(label=" Подтвердить (Выдать роль)", style=ButtonStyle.success, custom_id="final_accept", emoji="<:tik:1472654073814581268>")
    async def final_accept(self, button: Button, interaction: Interaction):
        await interaction.response.defer()
        try:
            role = interaction.guild.get_role(VERIFIED_ROLE_ID)
            member = interaction.guild.get_member(self.user.id)

            if role and member:
                await member.add_roles(role, reason="Верификация пройдена")
                
                await interaction.followup.send(
                    embed=Embed(description=f"Роль {role.mention} выдана пользователю {self.user.mention}!", color=disnake.Color.from_rgb(54, 57, 63))
                )
                
                notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
                if notification_channel:
                    embed_notify = Embed(
                        title="<:tik:1472654073814581268> Верификация успешна",
                        description=f"Поздравляем! Вы успешно прошли проверку и получили доступ к серверу.",
                        color=0x3BA55D,
                        timestamp=datetime.now()
                    )
                    embed_notify.set_thumbnail(url=self.user.display_avatar.url)
                    try:
                        await notification_channel.send(content=self.user.mention, embed=embed_notify)
                    except: pass

                log_channel = interaction.guild.get_channel(VERIFICATION_LOG_CHANNEL_ID)
                if log_channel:
                    embed_log = Embed(title="<:tik:1472654073814581268> Верификация: ОДОБРЕНО", color=0x3BA55D, timestamp=datetime.now())
                    embed_log.add_field(name="Пользователь", value=f"{self.user.mention}\n`{self.user.id}`", inline=True)
                    embed_log.add_field(name="Администратор", value=interaction.user.mention, inline=True)
                    await log_channel.send(embed=embed_log)
            
            elif not member:
                 await interaction.followup.send("ользователь вышел с сервера.", ephemeral=True)
            else:
                await interaction.followup.send("Ошибка: Роль VERIFIED_ROLE_ID не найдена.", ephemeral=True)
            
            # Отключаем кнопки и удаляем канал
            for child in self.children: child.disabled = True
            await interaction.edit_original_response(view=self)
            
            await self._close_channel(interaction)
            
        except Exception as e:
            await interaction.followup.send(embed=Embed(description=f"Ошибка: {e}", color=0xFF0000))


    @button(label=" Отказать", style=ButtonStyle.danger, custom_id="final_reject", emoji="<:cross:1472654174788255996>")
    async def final_reject(self, button: Button, interaction: Interaction):
        await interaction.response.defer()
        
        notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
        if notification_channel:
            embed = Embed(
                title="<:cross:1472654174788255996> Верификация отклонена",
                description=f"К сожалению, вы не прошли проверку.",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            try:
                await notification_channel.send(content=self.user.mention, embed=embed)
            except: pass

        log_channel = interaction.guild.get_channel(VERIFICATION_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = Embed(title="<:cross:1472654174788255996> Верификация: ОТКАЗАНО (После проверки)", color=0xFF0000, timestamp=datetime.now())
            embed_log.add_field(name="Пользователь", value=f"{self.user.mention}\n`{self.user.id}`", inline=True)
            embed_log.add_field(name="Администратор", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=embed_log)

        await interaction.followup.send(embed=Embed(description=f"<:cross:1472654174788255996> Верификация {self.user.mention} отклонена.", color=0xFF0000))
        
        for child in self.children: child.disabled = True
        await interaction.edit_original_response(view=self)
        
        await self._close_channel(interaction)


class VerificationAdminButtons(View):
    def __init__(self, user: disnake.User):
        super().__init__(timeout=None)
        self.user = user

    @button(label="На проверку (Создать канал)", style=ButtonStyle.success, custom_id="accept_verif", emoji="<:tik:1472654073814581268>")
    async def accept(self, button: Button, interaction: Interaction):
        # Проверка прав
        is_allowed = interaction.user.guild_permissions.administrator or \
                     any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)
        if not is_allowed:
            await interaction.response.send_message(embed=Embed(description="У вас нет прав!", color=0xFF0000), ephemeral=True)
            return

        category = interaction.guild.get_channel(VERIFICATION_CATEGORY_ID)
        if not category:
            await interaction.response.send_message(f"Категория для проверок (ID: {VERIFICATION_CATEGORY_ID}) не найдена!", ephemeral=True)
            return
            
        target_member = interaction.guild.get_member(self.user.id)
        if not target_member:
             await interaction.response.send_message("Пользователь покинул сервер.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=True)

        try:
            overwrites = {
                interaction.guild.default_role: PermissionOverwrite(read_messages=False), # Everyone - нельзя
                interaction.guild.me: PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True), # Бот - можно
                interaction.user: PermissionOverwrite(read_messages=True, send_messages=True), # Админ - можно
                target_member: PermissionOverwrite(read_messages=True, send_messages=True) # Юзер - можно
            }

            channel_name = f"verify-{target_member.display_name}"
            new_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Проверка {target_member.name} от {interaction.user.name}"
            )

            voice_channel = interaction.guild.get_channel(VOICE_CHANNEL_ID)
            voice_text = voice_channel.mention if voice_channel else "голосовой канал"
            
            embed_verify = Embed(
                title="<:freeiconselect1570717:1472654722463961189> Проверка на ПО",
                description=(
                    f"{target_member.mention}, вас вызвал на проверку администратор {interaction.user.mention}.\n\n"
                    f"**Инструкция:**\n"
                    f"1. Зайдите в {voice_text}.\n"
                    f"2. Включите демонстрацию экрана.\n"
                    f"3. Следуйте указаниям администратора.\n\n"
                    "⚠️ **Попытка выхода с сервера, игнорирование или отказ от проверки приведет к блокировке.**"
                ),
                color=disnake.Color.from_rgb(54, 57, 63)
            )
            await new_channel.send(content=f"{target_member.mention} {interaction.user.mention}", embed=embed_verify, view=VerificationFinalDecisionView(self.user))

            await interaction.followup.send(f"Канал проверки создан: {new_channel.mention}", ephemeral=True)

            button.disabled = True
            button.label = "На проверке"
            button.style = ButtonStyle.secondary
            
            embed = interaction.message.embeds[0]
            embed.add_field(name="Статус", value=f"В процессе (Канал: {new_channel.mention})", inline=False)
            
            await interaction.message.edit(embed=embed, view=self)

            notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
            if notification_channel:
                notify_embed = Embed(
                    title="<:freeiconcall3870799:1472668017170186331> Вызов на проверку",
                    description=f"Вас вызвали на проверку. Перейдите в канал: {new_channel.mention}",
                    color=disnake.Color.from_rgb(54, 57, 63)
                )
                try:
                    await notification_channel.send(content=target_member.mention, embed=notify_embed)
                except: pass

        except disnake.Forbidden:
             await interaction.followup.send("У бота нет прав создавать каналы или управлять ими в этой категории.", ephemeral=True)
        except Exception as e:
             await interaction.followup.send(f"Ошибка при создании канала: {e}", ephemeral=True)


    @button(label="Отказать (Сразу)", style=ButtonStyle.danger, custom_id="reject_verif", emoji="<:cross:1472654174788255996>")
    async def reject(self, button: Button, interaction: Interaction):
        is_allowed = interaction.user.guild_permissions.administrator or \
                     any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)
        if not is_allowed:
            await interaction.response.send_message(embed=Embed(description="У вас нет прав!", color=0xFF0000), ephemeral=True)
            return

        notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
        if notification_channel:
            embed = Embed(
                title="<:cross:1472654174788255996> Верификация отклонена",
                description=f"Ваша заявка на верификацию была отклонена администрацией.",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            try:
                await notification_channel.send(content=self.user.mention, embed=embed)
            except: pass

        log_channel = interaction.guild.get_channel(VERIFICATION_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = Embed(title="<:cross:1472654174788255996> Верификация: ОТКАЗАНО (По заявке)", color=0xFF0000, timestamp=datetime.now())
            embed_log.add_field(name="Пользователь", value=f"{self.user.mention}\n`{self.user.id}`", inline=True)
            embed_log.add_field(name="Администратор", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=embed_log)

        await interaction.response.send_message(embed=Embed(description="<:cross:1472654174788255996> Заявка отклонена.", color=0xFF0000), ephemeral=True)
        for child in self.children: child.disabled = True
        await interaction.message.edit(view=self)


class VerificationRequestModal(Modal):
    def __init__(self):
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
        
        reason = interaction.text_values["reason"]
        admin_channel = interaction.guild.get_channel(VERIFICATION_ADMIN_CHANNEL_ID)
        
        if not admin_channel:
            await interaction.followup.send(embed=Embed(description="Админский канал не найден!", color=0xFF0000), ephemeral=True)
            return

        embed = Embed(
            title="<:freeiconnewmessage11401280:1472666483443105913> Новый запрос на верификацию",
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

        await admin_channel.send(embed=embed, view=VerificationAdminButtons(interaction.user))
        await interaction.followup.send(
            embed=Embed(
                title="Запрос отправлен!",
                description="Ваш запрос передан администрации. Ожидайте уведомления.",
                color=0x3BA55D
            ),
            ephemeral=True
        )


class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Подать запрос на верификацию", style=ButtonStyle.success, emoji="<:freeiconassurance4157131:1472660870613041184>", custom_id="btn_request_verify")
    async def request_verify_btn(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(VerificationRequestModal())


class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(VERIFICATION_REQUEST_CHANNEL_ID)
        if channel:
            embed = Embed(
                title="Верификация",
                description="Для получения доступа к каналам сервера необходимо пройти верификацию.",
                color=0x2B2D31
            )
            
            last_msg = None
            async for msg in channel.history(limit=10):
                if msg.author == self.bot.user:
                    last_msg = msg
                    break

            if last_msg:
                await last_msg.edit(embed=embed, view=VerificationView())
                print("[Verification] Меню ОБНОВЛЕНО (edit).")
            else:
                await channel.purge(limit=10)
                await channel.send(embed=embed, view=VerificationView())
                print("[Verification] Меню СОЗДАНО (purge & send).")

def setup(bot):
    bot.add_cog(VerificationCog(bot))
