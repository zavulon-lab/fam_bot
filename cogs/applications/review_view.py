
import disnake
from disnake import Embed, Interaction, ButtonStyle, SelectOption, TextInputStyle
from disnake.ui import View, button, Button, Select, Modal, TextInput
from disnake.errors import Forbidden
from datetime import datetime
from constants import *
from .utils import extract_user_id_from_embed, create_personal_file

class DenyReasonModal(Modal):
    def __init__(self, review_view, member, original_interaction):
        self.review_view = review_view
        self.member = member
        self.original_interaction = original_interaction
        
        components = [
            TextInput(
                label="Причина отказа",
                custom_id="deny_reason",
                style=TextInputStyle.paragraph,
                placeholder="Стрельба, мувмент...",
                required=True,
                max_length=200
            )
        ]
        super().__init__(title="Отклонение заявки", components=components)

    async def callback(self, interaction: Interaction):
        reason = interaction.text_values["deny_reason"]
        await self.review_view.process_denial(interaction, self.member, reason)

# === ВЫБОР КУРАТОРА (ДЛЯ ПРИНЯТИЯ ПОСЛЕ ОБЗВОНА) ===
class CuratorSelectView(View):
    def __init__(self, original_view, member: disnake.Member, original_message: disnake.Message):
        super().__init__(timeout=60)
        self.original_view = original_view
        self.member = member
        self.original_message = original_message
        
        guild = member.guild
        curator_role = guild.get_role(CURATOR_ROLE_ID)
        
        if not curator_role:
            return
        
        curators = [m for m in guild.members if curator_role in m.roles and not m.bot]
        
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
            
            await self.original_view.process_acceptance(interaction, self.member, curator, self.original_message)
        
        select.callback = select_callback
        self.add_item(select)

# === ОСНОВНОЙ КЛАСС УПРАВЛЕНИЯ ===

class ApplicationReviewView(View):
    """Кнопки управления заявкой для администраторов"""
    def __init__(self):
        super().__init__(timeout=None)

    async def get_candidate(self, interaction: Interaction) -> disnake.Member | None:
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

    async def send_dm_embed(self, member: disnake.Member, embed: Embed, content: str = None) -> bool:
        try:
            await member.send(content=content, embed=embed)
            return True
        except Forbidden:
            return False

    async def find_and_delete_clarification_channel(self, guild, member_id: int):
        try:
            for channel in guild.text_channels:
                is_topic_match = channel.topic and str(member_id) in channel.topic
                if is_topic_match:
                    try:
                        await channel.delete(reason="Заявка закрыта")
                    except Exception:
                        pass
        except Exception:
            pass

    async def send_result_log(self, guild, content: str, embed: Embed):
        try:
            channel = guild.get_channel(APPLICATION_RESULTS_CHANNEL_ID)
            if channel:
                await channel.send(content=content, embed=embed)
            else:
                print(f"[Warning] Канал итогов {APPLICATION_RESULTS_CHANNEL_ID} не найден.")
        except Exception as e:
            print(f"[Error] Не удалось отправить итог заявки: {e}")

    async def process_denial(self, interaction: Interaction, member: disnake.Member, reason: str):
        await interaction.response.defer(ephemeral=True)
        recruiter = interaction.user

        await self.find_and_delete_clarification_channel(interaction.guild, member.id)

        original_embed = interaction.message.embeds[0]
        if original_embed:
            original_embed.color = 0xED4245 
            
            original_embed.set_footer(text=f"Отклонил: {recruiter.display_name} • Причина: {reason}") 
            
            await interaction.message.edit(embed=original_embed, view=None)

        result_embed = Embed(
            description=(
                f"Заявка от пользователя {member.mention}\n\n"
                f"На Вступление в семью была отклонена. ❌\n\n"
                f"Причина: {reason}\n"
                f"Рассматривал заявку: {recruiter.mention}"
            ),
            color=0xED4245
        )
        result_embed.set_thumbnail(url=member.display_avatar.url)
        result_embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await self.send_result_log(interaction.guild, content=member.mention, embed=result_embed)

        # 2. ЛС
        await self.send_dm_embed(member, result_embed, content=member.mention)

        await interaction.followup.send(f"❌ Заявка {member.mention} отклонена.", ephemeral=True)


    # === ЛОГИКА ПРИНЯТИЯ (ВНУТРЕННЯЯ) ===
    # === ЛОГИКА ПРИНЯТИЯ (ВНУТРЕННЯЯ) ===
    async def process_acceptance(self, interaction: Interaction, member: disnake.Member, curator: disnake.Member, message: disnake.Message):
        """
        ФИНАЛЬНОЕ ПРИНЯТИЕ ПОСЛЕ ОБЗВОНА.
        """
        await interaction.response.defer(ephemeral=True)
        recruiter = interaction.user

        # 1. Роль
        role = interaction.guild.get_role(ACCEPT_ROLE_ID)
        if role:
            try: await member.add_roles(role, reason=f"Принят: {recruiter}. Куратор: {curator}")
            except: pass

        # 2. Удаляем чат уточнений
        await self.find_and_delete_clarification_channel(interaction.guild, member.id)

        # 3. Личное дело
        personal_channel = await create_personal_file(interaction.guild, member, curator)
        if personal_channel and recruiter != curator:
            await personal_channel.set_permissions(recruiter, view_channel=True, send_messages=True)

        original_embed = message.embeds[0]
        if original_embed:
            original_embed.color = 0x3BA55D
            
            # Добавляем разделитель или просто поля вниз, сохраняя анкету
            original_embed.add_field(name="▬▬▬▬▬▬▬▬▬▬", value="**✅ ПРИНЯТ**", inline=False)
            original_embed.add_field(name="👨‍🏫 Куратор", value=curator.mention, inline=True)
            original_embed.add_field(name="🎖️ Рекрутер", value=recruiter.mention, inline=True)
            
            await message.edit(embed=original_embed, view=None)

        try:
            academy_channel = interaction.guild.get_channel(ACADEMY_CHANNEL_ID) 
            if academy_channel:
                academy_embed = Embed(
                    title="Новый участник принят",
                    description=(
                        f"{member.mention} — {recruiter.mention} принял(а)\n"
                        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                        f"Личное дело: {personal_channel.mention if personal_channel else 'Не создано'}\n"
                        f"Куратор — {curator.mention}"
                    ),
                    color=0x2B2D31, 
                )
                # Картинка Луны/Планеты
                academy_embed.set_thumbnail(url="https://media.discordapp.net/attachments/1336423985794682974/1336423986381754409/6FDCFF59-EFBB-4D26-9E57-50B0F3D61B50.jpg") 
                academy_embed.set_footer(text=f"ID: {member.id} • {datetime.now().strftime('%d.%m.%Y %H:%M')}")
                
                await academy_channel.send(embed=academy_embed)
        except Exception as e:
            print(f"[Error] Лог академии: {e}")

        # ЛС о финальном принятии
        await self.send_dm_embed(member, Embed(
            title="🎉 Добро пожаловать!", 
            description=f"Вы официально приняты в семью!\nВаш куратор: {curator.mention}", 
            color=0x3BA55D
        ))

        await interaction.followup.send(f"✅ {member.mention} принят. Лог отправлен в академию.", ephemeral=True)


    @button(label="✅ Принять (После обзвона)", style=ButtonStyle.success, custom_id="app_accept")
    async def accept_button(self, button: Button, interaction: Interaction):
        """Финал: Назначение куратора и выдача ролей"""
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message("❌ Кандидат не найден.", ephemeral=True)
            return

        view = CuratorSelectView(original_view=self, member=member, original_message=interaction.message)
        await interaction.response.send_message("Выберите куратора для нового участника:", view=view, ephemeral=True)

    @button(label="👀 Взять на рассмотрение", style=ButtonStyle.secondary, custom_id="app_review")
    async def review_button(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        member = await self.get_candidate(interaction)
        if not member: return

        original_embed = interaction.message.embeds[0]
        original_embed.color = 0xF59E0B
        original_embed.title = "👀 Заявка на рассмотрении"
        original_embed.set_footer(text=f"Рассматривает: {interaction.user.display_name}")
        await interaction.message.edit(embed=original_embed)
        await interaction.followup.send("👀 Статус обновлен.", ephemeral=True)

    @button(label="📞 Вызвать на обзвон", style=ButtonStyle.primary, custom_id="app_call")
    async def call_button(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        member = await self.get_candidate(interaction)
        recruiter = interaction.user
        if not member: return

        voice_channel = interaction.guild.get_channel(VOICE_CHANNEL_ID)
        voice_mention = voice_channel.mention if voice_channel else "#не-настроен"
        
        # 1. ПУБЛИЧНЫЙ ЛОГ (ЗЕЛЕНЫЙ)
        result_embed = Embed(
            description=(
                f"Заявка от пользователя {member.mention}\n\n"
                f"На Вступление в семью была рассмотрена! ✅\n\n"
                f"Для прохода обзвона ожидаем вас в канале :\n"
                f"{voice_mention}\n\n"
                f"Рассматривал заявку: {recruiter.mention}"
            ),
            color=0x3BA55D
        )
        result_embed.set_thumbnail(url=member.display_avatar.url)
        result_embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await self.send_result_log(interaction.guild, content=member.mention, embed=result_embed)
        
        await self.send_dm_embed(member, result_embed, content=member.mention)


        original_embed = interaction.message.embeds[0]
        original_embed.color = 0x5865F2
        original_embed.title = "📞 Вызван на обзвон"
        original_embed.set_footer(text=f"Вызвал: {recruiter.display_name}")
        await interaction.message.edit(embed=original_embed)

        await interaction.followup.send(f"{member.mention} вызван на обзвон.", ephemeral=True)

    @button(label="❌ Отклонить", style=ButtonStyle.danger, custom_id="app_deny")
    async def deny_button(self, button: Button, interaction: Interaction):
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message("Кандидат не найден.", ephemeral=True)
            return
        await interaction.response.send_modal(DenyReasonModal(self, member, interaction))

    @button(label="💬 Создать чат", style=ButtonStyle.secondary, custom_id="app_create_chat")
    async def create_chat_button(self, button: Button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        member = await self.get_candidate(interaction)
        
        # Если кандидат не найден
        if not member: 
            await interaction.followup.send(
                "❌ Кандидат не найден (возможно, вышел с сервера).", 
                ephemeral=True, 
                delete_after=20
            )
            return

        try:
            guild = interaction.guild
            cat = guild.get_channel(APPLICATIONS_CATEGORY_ID) 
            
            # Если категория не найдена
            if not cat:
                await interaction.followup.send(
                    "❌ Категория для заявок не найдена в настройках.", 
                    ephemeral=True, 
                    delete_after=20
                )
                return

            # Создаем канал
            chan = await guild.create_text_channel(
                name=f"заявка-{member.display_name}", 
                category=cat,
                topic=f"ID: {member.id} | Обсуждение заявки"
            )
            
            # Настраиваем права
            await chan.set_permissions(guild.default_role, view_channel=False)
            await chan.set_permissions(member, view_channel=True, send_messages=True)
            await chan.set_permissions(interaction.user, view_channel=True, send_messages=True)
            
            # Формируем Embed для канала
            original_embed = interaction.message.embeds[0]
            app_url = f"https://discord.com/channels/{guild.id}/{interaction.channel.id}/{interaction.message.id}"
            
            chat_embed = Embed(
                title="📋 Обсуждение заявки",
                description=f"Администратор {interaction.user.mention} создал этот чат для уточнения деталей.\n\n**[Перейти к сообщению с заявкой]({app_url})**",
                color=0x2B2D31
            )
            
            # Копируем поля из заявки
            if original_embed and original_embed.fields:
                for f in original_embed.fields:
                    chat_embed.add_field(name=f.name, value=f.value, inline=f.inline)
            
            chat_embed.set_thumbnail(url=member.display_avatar.url)
            chat_embed.set_footer(text=f"ID: {member.id}")

            # Отправляем сообщение в новый канал
            await chan.send(content=f"{member.mention}, администратор {interaction.user.mention} хочет уточнить детали вашей заявки.", embed=chat_embed)
            
            # === ОТПРАВКА УВЕДОМЛЕНИЯ В ЛС ===
            dm_embed = Embed(
                title="💬 Уточнение по заявке",
                description=(
                    f"Администратор **{interaction.user.display_name}** хочет задать вам вопросы по поводу вашей заявки.\n\n"
                    f"Пожалуйста, перейдите в созданный канал: {chan.mention}\n"
                    f"([Прямая ссылка на канал]({chan.jump_url}))"
                ),
                color=0x5865F2
            )
            try:
                await member.send(embed=dm_embed)
                dm_status = "✅ Уведомление отправлено в ЛС."
            except Forbidden:
                dm_status = "⚠️ ЛС закрыты, уведомление не отправлено."
            except Exception:
                dm_status = "❌ Ошибка отправки ЛС."

            # Итоговое сообщение (удаляется через 20 секунд)
            await interaction.followup.send(
                f"✅ Чат создан: {chan.mention}\n{dm_status}", 
                ephemeral=True, 
                delete_after=20
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при создании чата: {e}", 
                ephemeral=True, 
                delete_after=20
            )


            await interaction.followup.send(f"Чат создан: {chan.mention}\n{dm_status}", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Ошибка при создании чата: {e}", ephemeral=True)
