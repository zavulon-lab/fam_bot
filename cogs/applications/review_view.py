"""View с кнопками управления заявками"""

import disnake
# ✅ SelectOption перенесен сюда
from disnake import Embed, Interaction, ButtonStyle, SelectOption 
from disnake.ui import View, button, Button, Select, user_select, UserSelect 
from disnake.errors import Forbidden
from datetime import datetime
from constants import *
from .utils import extract_user_id_from_embed, create_personal_file
from constants import NEW_MEMBER_LOG_CHANNEL_ID


class CuratorSelectView(View):
    """View для выбора куратора из списка ролей"""
    def __init__(self, original_view, member: disnake.Member, original_message: disnake.Message):
        super().__init__(timeout=60)
        self.original_view = original_view
        self.member = member
        self.original_message = original_message
        
        # Получаем роль куратора из константы
        guild = member.guild
        curator_role = guild.get_role(CURATOR_ROLE_ID)
        
        if not curator_role:
            return
        
        # Фильтруем только членов с ролью куратора
        curators = [m for m in guild.members if curator_role in m.roles and not m.bot]
        
        # Создаем опции для Select (максимум 25)
        options = []
        if curators:
            for curator in curators[:25]:
                options.append(
                    SelectOption(
                        label=curator.display_name[:100],
                        value=str(curator.id),
                        description=f"ID: {curator.id}"
                    )
                )
        else:
            # Если кураторов нет, добавляем заглушку, чтобы не падало
            options.append(SelectOption(label="Нет кураторов", value="none", description="Обратитесь к администратору"))

        
        select = Select(
            placeholder="Выберите куратора...",
            options=options,
            custom_id="select_curator",
            disabled=len(curators) == 0
        )
        
        async def select_callback(interaction: Interaction):
            if interaction.data["values"][0] == "none":
                await interaction.response.send_message("❌ Нет доступных кураторов.", ephemeral=True)
                return

            curator_id = int(interaction.data["values"][0])
            curator = guild.get_member(curator_id)
            
            if not curator:
                await interaction.response.send_message("❌ Куратор не найден!", ephemeral=True)
                return
            
            await self.process_acceptance(interaction, interaction.user, curator)
        
        select.callback = select_callback
        self.add_item(select)
    
    async def process_acceptance(self, interaction: Interaction, recruiter: disnake.Member, curator: disnake.Member):
        """Обрабатывает принятие заявки"""
        await interaction.response.defer(ephemeral=True)
        
        # 1. Выдаем роль
        role = interaction.guild.get_role(ACCEPT_ROLE_ID)
        if not role:
            await interaction.followup.send("❌ Роль ACCEPT_ROLE_ID не найдена.", ephemeral=True)
            return

        try:
            await self.member.add_roles(role, reason=f"Принят рекрутером {recruiter}. Куратор: {curator}")
        except Exception as e:
            await interaction.followup.send(f"⚠️ Роль не выдана: {e}", ephemeral=True)

        # 2. Удаляем чат уточнений
        await self.original_view.find_and_delete_clarification_channel(interaction.guild, self.member.id)

        # 3. Создаем личное дело
        personal_channel = await create_personal_file(interaction.guild, self.member, curator)
        
        # Даем доступ рекрутеру если он не куратор
        if personal_channel and recruiter != curator:
            await personal_channel.set_permissions(recruiter, view_channel=True, send_messages=True)

        # 4. Логируем
        if personal_channel:
            await self.original_view.send_new_member_log(
                interaction.guild, self.member, curator, recruiter, personal_channel
            )

        # 5. Обновляем embed заявки
        original_embed = self.original_message.embeds[0]
        if original_embed:
            original_embed.color = 0x3BA55D
            original_embed.title = "✅ Заявка принята"
            original_embed.add_field(name="👨‍🏫 Куратор", value=curator.mention, inline=True)
            original_embed.add_field(name="🎖️ Рекрутер", value=recruiter.mention, inline=True)
            
            await self.original_message.edit(embed=original_embed, view=None)

        # 6. Ответ рекрутеру
        success_embed = Embed(
            title="✅ Заявка принята",
            description=(
                f"**Кандидат:** {self.member.mention}\n"
                f"**Куратор:** {curator.mention}\n"
                f"**Личное дело:** {personal_channel.mention if personal_channel else '❌ Ошибка'}"
            ),
            color=0x3BA55D
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class ApplicationReviewView(View):
    """Кнопки управления заявкой для администраторов"""
    def __init__(self):
        super().__init__(timeout=None)

    async def get_candidate(self, interaction: Interaction) -> disnake.Member | None:
        """Получает кандидата из эмбеда"""
        if not interaction.message.embeds:
            return None
        
        user_id = extract_user_id_from_embed(interaction.message.embeds[0])
        if not user_id:
            return None
        
        member = interaction.guild.get_member(user_id)
        if member:
            return member
        
        try:
            return await interaction.guild.fetch_member(user_id)
        except:
            return None

    async def send_dm_embed(self, member: disnake.Member, embed: Embed) -> bool:
        """Отправляет красивый embed в DM кандидату"""
        try:
            await member.send(embed=embed)
            return True
        except Forbidden:
            return False

    async def find_and_delete_clarification_channel(self, guild, member_id: int):
        """Находит и удаляет канал уточнений для пользователя"""
        try:
            for channel in guild.text_channels:
                is_topic_match = channel.topic and str(member_id) in channel.topic
                
                if is_topic_match:
                    try:
                        await channel.delete(reason="Заявка закрыта")
                        print(f"[Applications] Удален чат уточнений: {channel.name}")
                        return
                    except Exception as e:
                        print(f"[Applications] Ошибка удаления канала {channel.name}: {e}")
        except Exception as e:
            print(f"[Applications] Ошибка поиска канала для удаления: {e}")

    async def send_new_member_log(self, guild, member, curator, recruiter, personal_channel):
        """Отправляет красивый лог о принятии нового участника"""
        try:
            log_channel = guild.get_channel(NEW_MEMBER_LOG_CHANNEL_ID)
            if not log_channel:
                print(f"[Applications] Канал логов {NEW_MEMBER_LOG_CHANNEL_ID} не найден")
                return

            embed = Embed(
                title="Новый участник принят",
                description=(
                    f"{member.mention} — {recruiter.mention} принял(а)\n"
                    f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                    f"Личное дело: {personal_channel.mention}\n"
                    f"Куратор — {curator.mention}"
                ),
                color=0x2ECC71,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID: {member.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"[Applications] Ошибка лога: {e}")

    @button(label="✅ Принять", style=ButtonStyle.success, custom_id="app_accept")
    async def accept_button(self, button: Button, interaction: Interaction):
        """Принять заявку: Открывает выбор куратора"""
        
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message(
                embed=Embed(title="❌ Ошибка", description="Кандидат не найден.", color=0xED4245), 
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(ACCEPT_ROLE_ID)
        if not role:
            await interaction.response.send_message(
                embed=Embed(title="❌ Ошибка", description="Роль ACCEPT_ROLE_ID не найдена.", color=0xED4245), 
                ephemeral=True
            )
            return

        # Проверяем наличие кураторов
        curator_role = interaction.guild.get_role(CURATOR_ROLE_ID)
        if not curator_role:
            await interaction.response.send_message(
                embed=Embed(title="❌ Ошибка", description="Роль куратора не найдена в constants.py (CURATOR_ROLE_ID)", color=0xED4245), 
                ephemeral=True
            )
            return
        
        view = CuratorSelectView(original_view=self, member=member, original_message=interaction.message)
        
        await interaction.response.send_message(
            f"Для принятия **{member.display_name}** выберите **Куратора** из списка:", 
            view=view, 
            ephemeral=True
        )

    @button(label="👀 Взять на рассмотрение", style=ButtonStyle.secondary, custom_id="app_review")
    async def review_button(self, button: Button, interaction: Interaction):
        """Взять заявку на рассмотрение"""
        await interaction.response.defer(ephemeral=True)
        
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.followup.send("❌ Кандидат не найден.", ephemeral=True)
            return

        original_embed = interaction.message.embeds[0]
        if original_embed:
            original_embed.color = 0xF59E0B
            original_embed.title = "👀 Заявка на рассмотрении"
            await interaction.message.edit(embed=original_embed)

        await interaction.followup.send(
            embed=Embed(title="👀 Взято на рассмотрение", description=f"Вы начали рассматривать заявку {member.mention}", color=0xF59E0B),
            ephemeral=True
        )

    @button(label="📞 Вызвать на обзвон", style=ButtonStyle.primary, custom_id="app_call")
    async def call_button(self, button: Button, interaction: Interaction):
        """Вызвать на обзвон"""
        await interaction.response.defer(ephemeral=True)
        
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.followup.send("❌ Кандидат не найден.", ephemeral=True)
            return

        voice_channel = interaction.guild.get_channel(VOICE_CHANNEL_ID)
        voice_link = f"https://discord.com/channels/{interaction.guild.id}/{VOICE_CHANNEL_ID}" if voice_channel else "Канал не найден"

        call_embed = Embed(
            title="📞 Вызов на обзвон",
            description=f"Администратор **{interaction.user.display_name}** приглашает вас на собеседование!",
            color=0x5865F2
        )
        call_embed.add_field(name="🔊 Канал", value=f"[Перейти]({voice_link})\n**{voice_channel.name if voice_channel else 'Не настроен'}**")
        
        await self.send_dm_embed(member, call_embed)
        
        await interaction.followup.send(
            embed=Embed(title="📞 Вызван на обзвон", description=f"Уведомление отправлено {member.mention}", color=0x5865F2),
            ephemeral=True
        )

    @button(label="❌ Отклонить", style=ButtonStyle.danger, custom_id="app_deny")
    async def deny_button(self, button: Button, interaction: Interaction):
        """Отклонить заявку"""
        await interaction.response.defer(ephemeral=True)
        
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.followup.send("❌ Кандидат не найден.", ephemeral=True)
            return

        await self.send_dm_embed(member, Embed(title="❌ Заявка отклонена", description="К сожалению, ваша заявка отклонена.", color=0xED4245))
        await self.find_and_delete_clarification_channel(interaction.guild, member.id)

        original_embed = interaction.message.embeds[0]
        if original_embed:
            original_embed.color = 0xED4245
            original_embed.title = "❌ Заявка отклонена"
            await interaction.message.edit(embed=original_embed, view=None)

        await interaction.followup.send(
            embed=Embed(title="❌ Отклонено", description=f"Заявка {member.mention} отклонена.", color=0xED4245),
            ephemeral=True
        )

    @button(label="💬 Создать чат", style=ButtonStyle.secondary, custom_id="app_create_chat")
    async def create_chat_button(self, button: Button, interaction: Interaction):
        """Создать чат для уточнений с данными заявки"""
        await interaction.response.defer(ephemeral=True)
        
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.followup.send("❌ Кандидат не найден.", ephemeral=True)
            return

        try:
            guild = interaction.guild
            category = guild.get_channel(CATEGORY_ID)
            
            channel_name = f"заявка-{member.display_name.lower().replace(' ', '-')}"
            
            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                topic=f"Чат для уточнений заявки пользователя {member.id}", 
                reason=f"Уточнение заявки {member}"
            )
            
            await new_channel.set_permissions(guild.default_role, view_channel=False)
            await new_channel.set_permissions(member, view_channel=True)
            role = guild.get_role(ROLE_ID)
            if role: 
                await new_channel.set_permissions(role, view_channel=True)

            original_embed = interaction.message.embeds[0]
            application_link = f"https://discord.com/channels/{guild.id}/{interaction.channel.id}/{interaction.message.id}"
            
            chat_embed = Embed(
                title="📋 Данные заявки",
                description=f"[Перейти к заявке]({application_link})\n\n{original_embed.description or ''}",
                color=0x5865F2
            )
            for f in original_embed.fields:
                chat_embed.add_field(name=f.name, value=f.value, inline=f.inline)
            chat_embed.set_thumbnail(url=member.display_avatar.url)

            await new_channel.send(f"{member.mention}, у модератора {interaction.user.mention} есть вопросы.", embed=chat_embed)
            
            await interaction.followup.send(embed=Embed(title="✅ Чат создан", description=f"Перейти: {new_channel.mention}", color=0x3BA55D), ephemeral=True)
            
            await self.send_dm_embed(member, Embed(title="💬 Вопросы по заявке", description=f"Администратор создал чат для уточнений: {new_channel.mention}", color=0x5865F2))

        except Exception as e:
            print(f"Ошибка создания чата: {e}")
            await interaction.followup.send("❌ Ошибка при создании канала.", ephemeral=True)


