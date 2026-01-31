import disnake
import re
from disnake.ui import Select, View, button, Button
from disnake import Interaction, CategoryChannel, SelectOption, TextChannel, ButtonStyle, Embed, TextInputStyle
from disnake.errors import NotFound, HTTPException, Forbidden
from datetime import datetime
from constants import *
from database import getprivatechannel, setprivatechannel, addcreatedchannel

# ====== СИСТЕМА ЗАЯВОК (ОБНОВЛЕННАЯ) ======

class CompleteApplicationModal(disnake.ui.Modal):
    """Модальное окно для заполнения заявки"""
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="📝 Имя и фамилия",
                custom_id="name",
                style=TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="📚 Опыт РП",
                custom_id="rp_experience",
                style=TextInputStyle.paragraph,
                required=True,
            ),
            disnake.ui.TextInput(
                label="🎯 Стрельба",
                custom_id="shooting",
                style=TextInputStyle.paragraph,
                required=True,
            ),
            disnake.ui.TextInput(
                label="⏰ LVL онлайна (2-10)",
                custom_id="lvl_online",
                style=TextInputStyle.short,
                required=True,
                max_length=10,
            ),
            disnake.ui.TextInput(
                label="👨‍👩‍👧‍👦 Опыт в семьях",
                custom_id="family_experience",
                style=TextInputStyle.paragraph,
                required=True,
            ),
        ]
        super().__init__(title="✦ Анкета на вступление в семью", components=components, timeout=300)

    async def callback(self, interaction: disnake.ModalInteraction):
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ Ошибка: гильдия не найдена!", ephemeral=True)
                return

            # Получаем канал для отправки заявок
            review_channel = guild.get_channel(APPLICATIONS_REVIEW_CHANNEL_ID)
            if not review_channel:
                await interaction.response.send_message(
                    "❌ Канал для заявок не найден. Сообщите администрации.",
                    ephemeral=True
                )
                return

            # Получаем данные формы
            name = interaction.text_values["name"]
            rp_experience = interaction.text_values["rp_experience"]
            shooting = interaction.text_values["shooting"]
            lvl_online = interaction.text_values["lvl_online"]
            family_experience = interaction.text_values["family_experience"]

            # Создаем embed заявки
            embed = Embed(
                title="✦ Новая заявка на вступление в семью",
                description=(
                    "Спасибо, что решили присоединиться к нам ❤️\n"
                    "Администрация рассмотрит вашу заявку в ближайшее время.\n"
                    "──────────────────────────────"
                ),
                color=0x2B2D31,
                timestamp=datetime.now(),
            )

            # Добавляем поля анкеты
            embed.add_field(name="📝 Имя и фамилия", value=f"```{name}```", inline=False)
            embed.add_field(name="📚 Опыт РП", value=f"```{rp_experience}```", inline=False)
            embed.add_field(name="🎯 Стрельба", value=f"```{shooting}```", inline=False)
            embed.add_field(name="⏰ LVL онлайна", value=f"```{lvl_online}```", inline=False)
            embed.add_field(name="👨‍👩‍👧‍👦 Опыт в семьях", value=f"```{family_experience}```", inline=False)

            # Информация о кандидате
            embed.add_field(name="👤 Пользователь", value=interaction.user.mention, inline=True)
            embed.add_field(name="🆔 ID", value=f"`{interaction.user.id}`", inline=True)

            embed.set_footer(text=f"Отправлено {interaction.user.display_name}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            # Упоминание роли (опционально)
            staff_role = guild.get_role(STAFF_ROLE_ID)
            mention = staff_role.mention if staff_role else ""

            # Отправляем заявку в канал рассмотрения
            await review_channel.send(content=mention, embed=embed, view=ApplicationReviewView())

            # Уведомление кандидату (ephemeral)
            await interaction.response.send_message(
                "✅ Ваша заявка отправлена. Ожидайте дальнейших действий от администрации.",
                ephemeral=True
            )

            # Попытка отправить DM
            try:
                await interaction.user.send(
                    "✅ **Ваша заявка отправлена!**\n\n"
                    "Ожидайте дальнейших действий от администрации. "
                    "Мы свяжемся с вами в ближайшее время."
                )
            except Forbidden:
                pass  # Если ЛС закрыты - ничего страшного

        except Exception as e:
            print(f"❌ Ошибка в CompleteApplicationModal: {e}")
            error_embed = Embed(
                title="❌ Ошибка",
                description="Произошла ошибка при отправке заявки. Попробуйте позже.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


class ApplicationReviewView(View):
    """Кнопки управления заявкой для админов"""
    def __init__(self):
        super().__init__(timeout=None)

    async def get_candidate(self, interaction: Interaction) -> disnake.Member | None:
        """Извлекает кандидата из embed заявки"""
        uid = self.extract_user_id_from_message(interaction.message)
        if not uid:
            return None
        m = interaction.guild.get_member(uid)
        if m:
            return m
        try:
            return await interaction.guild.fetch_member(uid)
        except:
            return None

    @staticmethod
    def extract_user_id_from_message(message: disnake.Message) -> int | None:
        """Достает ID кандидата из embed"""
        if not message.embeds:
            return None
        emb = message.embeds[0]
        for f in emb.fields:
            m = re.search(r"\d{17,20}", f.value or "")
            if m:
                return int(m.group(0))
        m = re.search(r"\d{17,20}", emb.description or "")
        return int(m.group(0)) if m else None

    async def dm_candidate(self, member: disnake.Member, text: str) -> bool:
        """Отправляет DM кандидату, возвращает успешность"""
        try:
            await member.send(text)
            return True
        except Forbidden:
            return False

    @button(label="✅ Принять", style=ButtonStyle.success, custom_id="app_accept")
    async def accept_button(self, button: Button, interaction: Interaction):
        """Принять заявку: выдать роль + DM"""
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message(
                "❌ Не смог найти кандидата по этой заявке.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(ACCEPT_ROLE_ID)
        if not role:
            await interaction.response.send_message(
                "❌ Роль ACCEPT_ROLE_ID не найдена в constants.py",
                ephemeral=True
            )
            return

        await member.add_roles(role, reason=f"Заявка принята {interaction.user}")
        dm_ok = await self.dm_candidate(
            member,
            "✅ **Поздравляем!**\n\nВаша заявка принята! Вам выдана роль на сервере. Добро пожаловать в семью! ❤️"
        )

        status = "✅ Принято: роль выдана, кандидату отправлено ЛС." if dm_ok else "✅ Принято: роль выдана (ЛС недоступны)."
        await interaction.response.send_message(status, ephemeral=True)

        # Отключаем кнопки
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @button(label="👀 Взять на рассмотрение", style=ButtonStyle.secondary, custom_id="app_review")
    async def review_button(self, button: Button, interaction: Interaction):
        """Взять заявку на рассмотрение: DM кандидату"""
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message(
                "❌ Не смог найти кандидата по этой заявке.",
                ephemeral=True
            )
            return

        dm_ok = await self.dm_candidate(
            member,
            f"👀 **Ваша заявка взята на рассмотрение!**\n\n"
            f"Администратор **{interaction.user.display_name}** начал рассматривать вашу заявку. "
            f"Ожидайте дальнейших действий."
        )

        status = "👀 Взято на рассмотрение, кандидату отправлено ЛС." if dm_ok else "👀 Взято на рассмотрение (ЛС недоступны)."
        await interaction.response.send_message(status, ephemeral=True)

    @button(label="📞 Вызвать на обзвон", style=ButtonStyle.primary, custom_id="app_call")
    async def call_button(self, button: Button, interaction: Interaction):
        """Вызвать кандидата на обзвон: DM"""
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message(
                "❌ Не смог найти кандидата по этой заявке.",
                ephemeral=True
            )
            return

        dm_ok = await self.dm_candidate(
            member,
            f"📞 **Вас вызывают на обзвон!**\n\n"
            f"Администратор **{interaction.user.display_name}** хочет пообщаться с вами голосом. "
            f"Пожалуйста, зайдите в голосовой канал или свяжитесь с администрацией."
        )

        status = "📞 Кандидат вызван на обзвон, ЛС отправлено." if dm_ok else "📞 Кандидат вызван (ЛС недоступны)."
        await interaction.response.send_message(status, ephemeral=True)

    @button(label="❌ Отклонить", style=ButtonStyle.danger, custom_id="app_reject")
    async def reject_button(self, button: Button, interaction: Interaction):
        """Отклонить заявку: DM"""
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message(
                "❌ Не смог найти кандидата по этой заявке.",
                ephemeral=True
            )
            return

        dm_ok = await self.dm_candidate(
            member,
            "❌ **К сожалению, ваша заявка отклонена.**\n\n"
            "Спасибо за интерес к нашей семье. Возможно, вы сможете подать заявку позже."
        )

        status = "❌ Заявка отклонена, кандидату отправлено ЛС." if dm_ok else "❌ Заявка отклонена (ЛС недоступны)."
        await interaction.response.send_message(status, ephemeral=True)

        # Отключаем кнопки
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @button(label="💬 Создать чат", style=ButtonStyle.secondary, custom_id="app_create_chat")
    async def create_chat_button(self, button: Button, interaction: Interaction):
        """Создать приватный канал для уточнений в той же категории"""
        member = await self.get_candidate(interaction)
        if not member:
            await interaction.response.send_message(
                "❌ Не смог найти кандидата по этой заявке.",
                ephemeral=True
            )
            return

        try:
            guild = interaction.guild
            category = guild.get_channel(CATEGORY_ID)
            if not category or not isinstance(category, CategoryChannel):
                await interaction.response.send_message(
                    "❌ Категория CATEGORY_ID не найдена!",
                    ephemeral=True
                )
                return

            # Создаем канал в той же категории
            channel_name = f"заявка-{member.display_name.lower().replace(' ', '-')}"
            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                reason=f"Чат для уточнений по заявке {member}"
            )

            # Права доступа
            role = guild.get_role(ROLE_ID)
            await new_channel.set_permissions(guild.default_role, view_channel=False)
            if role:
                await new_channel.set_permissions(role, view_channel=True)
            await new_channel.set_permissions(member, view_channel=True)

            # Сообщение в канале
            embed = Embed(
                title="💬 Чат для уточнений",
                description=(
                    f"Этот канал создан для обсуждения заявки кандидата {member.mention}.\n\n"
                    f"**Создал:** {interaction.user.mention}\n"
                    f"**Кандидат:** {member.mention}\n"
                    f"**ID кандидата:** `{member.id}`"
                ),
                color=0x3A3B3C,
                timestamp=datetime.now(),
            )
            await new_channel.send(embed=embed)

            # Уведомляем администратора
            await interaction.response.send_message(
                f"✅ Создан канал {new_channel.mention} для уточнений.",
                ephemeral=True
            )

            # DM кандидату
            await self.dm_candidate(
                member,
                f"💬 **Для вас создан канал для уточнений!**\n\n"
                f"Перейдите в {new_channel.mention} для общения с администрацией."
            )

            # Сохраняем в БД
            addcreatedchannel(new_channel.id, interaction.user.id, new_channel.name)

        except Exception as e:
            print(f"❌ Ошибка создания чата: {e}")
            await interaction.response.send_message(
                "❌ Ошибка при создании канала.",
                ephemeral=True
            )


class ApplicationChannelButtonsView(View):
    """Кнопка 'Подать заявку' в канале"""
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="📝 Подать заявку", style=ButtonStyle.primary)
    async def submit_application_button(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(CompleteApplicationModal())


# ====== ОСТАЛЬНЫЕ СИСТЕМЫ (БЕЗ ИЗМЕНЕНИЙ) ======

class VerificationRequestModal(disnake.ui.Modal):
    """Модальное окно для верификации"""
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="📝 Причина запроса",
                custom_id="reason",
                style=TextInputStyle.paragraph,
                required=True,
                placeholder="Опишите причину...",
            ),
        ]
        super().__init__(title="🔐 Запрос верификации", components=components, timeout=300)

    async def callback(self, interaction: disnake.ModalInteraction):
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ Ошибка: гильдия не найдена!", ephemeral=True)
                return

            admin_channel = guild.get_channel(VERIFICATION_ADMIN_CHANNEL_ID)
            if not admin_channel:
                await interaction.response.send_message("❌ Канал администрации не найден!", ephemeral=True)
                return

            reason = interaction.text_values["reason"]

            embed = Embed(
                title="🔐 Запрос на верификацию",
                description=(
                    f"**Пользователь:** {interaction.user.mention}\n"
                    f"**ID:** `{interaction.user.id}`\n"
                    f"**Аккаунт создан:** {interaction.user.created_at.strftime('%d.%m.%Y')}\n\n"
                    f"**Причина:**\n{reason}"
                ),
                color=0x3A3B3C,
                timestamp=datetime.now(),
            )
            embed.set_footer(text=f"Запрос от {interaction.user.display_name}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await admin_channel.send(embed=embed, view=VerificationAdminButtonsView(interaction.user))

            confirm_embed = Embed(
                title="✅ Запрос отправлен!",
                description="Ваш запрос на верификацию отправлен администрации. Ожидайте решения.",
                color=0x3BA55D,
                timestamp=datetime.now(),
            )
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Ошибка в VerificationRequestModal: {e}")
            error_embed = Embed(
                title="❌ Ошибка",
                description="Произошла ошибка при отправке запроса. Попробуйте позже.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


class PersonalChannelModal(disnake.ui.Modal):
    """Модальное окно для создания личного канала"""
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="📹 Ссылка на YouTube/Imgur",
                custom_id="media_link",
                style=TextInputStyle.short,
                required=True,
                placeholder="https://www.youtube.com/... или https://imgur.com/...",
            ),
        ]
        super().__init__(title="📹 Создание личного канала", components=components, timeout=300)

    async def callback(self, interaction: disnake.ModalInteraction):
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ Ошибка: гильдия не найдена!", ephemeral=True)
                return

            category = guild.get_channel(CATEGORY_ID)
            if not category or not isinstance(category, CategoryChannel):
                await interaction.response.send_message("❌ Категория не найдена!", ephemeral=True)
                return

            media_link = interaction.text_values["media_link"]

            # Проверка на достижение лимита в 50 каналов
            if len(category.channels) >= 50:
                category_name_base = category.name if category else "Категория"
                new_category = None
                category_index = 1

                for cat in guild.categories:
                    if cat.name.startswith(category_name_base) and len(cat.channels) < 50:
                        new_category = cat
                        break

                if not new_category:
                    while True:
                        new_category_name = f"{category_name_base} {category_index}" if category_index > 1 else category_name_base
                        try:
                            new_category = await guild.create_category(
                                name=new_category_name,
                                reason="Категория переполнена (50 каналов)"
                            )
                            if category:
                                for target, permission_overwrite in category.overwrites.items():
                                    await new_category.set_permissions(target, overwrite=permission_overwrite)
                            break
                        except HTTPException as http_err:
                            if http_err.code == 50035 and "Maximum number" in str(http_err):
                                category_index += 1
                                continue
                            elif http_err.code == 50035 and "Guild has reached" in str(http_err):
                                await interaction.response.send_message("❌ Сервер достиг лимита категорий!", ephemeral=True)
                                return
                            raise

                category = new_category

            user_id = str(interaction.user.id)

            # Проверка существования личного канала
            personal_channel = None
            channel_id = getprivatechannel(user_id)
            if channel_id:
                personal_channel = guild.get_channel(channel_id)

            if not personal_channel:
                personal_channel = await guild.create_text_channel(
                    name=f"🔒{interaction.user.display_name}",
                    category=category,
                    reason="Создание личного канала",
                )
                await personal_channel.set_permissions(guild.default_role, view_channel=False)
                await personal_channel.set_permissions(interaction.user, view_channel=True)

                role = guild.get_role(PRIVATE_THREAD_ROLE_ID)
                if role:
                    await personal_channel.set_permissions(role, view_channel=True)

                setprivatechannel(user_id, personal_channel.id)

            embed = Embed(
                title="📹 Новая ссылка на медиа",
                description=(
                    f"**От:** {interaction.user.mention}\n"
                    f"**Ссылка:** {media_link}"
                ),
                color=0x3A3B3C,
                timestamp=datetime.now(),
            )
            embed.set_footer(text=f"Отправлено {interaction.user.display_name}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await personal_channel.send(embed=embed)

            confirm_embed = Embed(
                title="✅ Успешно!",
                description=f"Ваша ссылка отправлена в {personal_channel.mention}.",
                color=0x3BA55D,
                timestamp=datetime.now(),
            )
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Ошибка в PersonalChannelModal: {e}")
            error_embed = Embed(
                title="❌ Ошибка",
                description="Произошла ошибка при создании канала.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


class ChannelSelect(Select):
    """Выбор категории для создания канала"""
    def __init__(self):
        super().__init__(
            placeholder="Выберите категорию...",
            options=[
                SelectOption(label="Категория 1", value=str(CATEGORY1_ID)),
                SelectOption(label="Категория 2", value=str(CATEGORY2_ID)),
            ],
        )

    async def callback(self, interaction: Interaction):
        selected_category_id = int(self.values[0])
        selected_category = interaction.guild.get_channel(selected_category_id)
        if not selected_category or not isinstance(selected_category, CategoryChannel):
            await interaction.response.send_message("❌ Категория не найдена!", ephemeral=True)
            return

        if len(selected_category.channels) >= 50:
            await interaction.response.send_message("❌ Категория переполнена (50 каналов)!", ephemeral=True)
            return

        await interaction.response.send_modal(CreateChannelModal(selected_category))


class CreateChannelModal(disnake.ui.Modal):
    """Модальное окно для создания канала"""
    def __init__(self, category: CategoryChannel):
        self.category = category
        components = [
            disnake.ui.TextInput(
                label="📝 Название канала",
                custom_id="nickname",
                style=TextInputStyle.short,
                required=True,
                max_length=50,
                placeholder="my-channel",
            ),
        ]
        super().__init__(
            title="✨ Создание канала",
            components=components,
            timeout=300,
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        try:
            if len(self.category.channels) >= 50:
                await interaction.response.send_message("❌ Категория переполнена (50 каналов)!", ephemeral=True)
                return

            nickname = interaction.text_values["nickname"]
            channel_name = nickname.lower().replace(" ", "-")

            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=self.category,
                reason="Создание канала через команду",
            )

            addcreatedchannel(channel.id, interaction.user.id, channel.name)

            embed = Embed(
                title="✅ Канал создан!",
                description=(
                    f"**Название:** {nickname}\n"
                    f"**Категория:** {self.category.name}\n"
                    f"**Создатель:** {interaction.user.mention}\n"
                    f"**Ссылка:** {channel.mention}"
                ),
                color=0x3BA55D,
                timestamp=datetime.now(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Ошибка в CreateChannelModal: {e}")
            error_embed = Embed(
                title="❌ Ошибка",
                description="Произошла ошибка при создании канала.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


class ChannelSelectViewSelect(Select):
    """Выбор канала для отката"""
    def __init__(self, channels_list: list[TextChannel]):
        options = [
            SelectOption(
                label=f"{channel.category.name if channel.category else '❓ Без категории'} - {channel.name}",
                value=str(channel.id),
            )
            for channel in channels_list
        ]
        super().__init__(placeholder="Выберите канал...", options=options)

    async def callback(self, interaction: Interaction):
        selected_channel_id = int(self.values[0])
        selected_channel = interaction.guild.get_channel(selected_channel_id)
        if not selected_channel:
            await interaction.response.send_message("❌ Канал не найден!", ephemeral=True)
            return
        await interaction.response.send_modal(RollbackForm(selected_channel))


class VerificationRequestButtonsView(View):
    """Кнопка 'Запросить верификацию'"""
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="🔐 Запросить верификацию", style=ButtonStyle.primary, custom_id="verification_request_button")
    async def verification_request_button(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(VerificationRequestModal())


class PersonalChannelButtonsView(View):
    """Кнопка 'Создать личный канал'"""
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="📹 Создать личный канал", style=ButtonStyle.primary, custom_id="personal_channel_button")
    async def personal_channel_button(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(PersonalChannelModal())


class VerificationAdminButtonsView(View):
    """Кнопки для админов (принять/отклонить верификацию)"""
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @button(label="✅ Принять", style=ButtonStyle.success, custom_id="accept_verification_button")
    async def accept_verification_button(self, button: Button, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator and not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
            return

        try:
            notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
            voice_channel = interaction.guild.get_channel(VOICE_CHANNEL_ID)

            if not notification_channel or not voice_channel:
                await interaction.response.send_message("❌ Каналы не найдены!", ephemeral=True)
                return

            embed = Embed(
                title="✅ Верификация принята",
                description=(
                    f"Поздравляем, {self.user.mention}! Ваша верификация одобрена.\n\n"
                    f"Теперь вы можете зайти в голосовой канал: {voice_channel.mention}"
                ),
                color=0x3BA55D,
                timestamp=datetime.now(),
            )
            embed.set_footer(text=f"Одобрено {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            embed.set_thumbnail(url=self.user.display_avatar.url)

            await notification_channel.send(content=self.user.mention, embed=embed)
            await interaction.response.send_message(f"✅ {self.user.mention} верифицирован!", ephemeral=True)

            self.children[0].disabled = True
            self.children[1].disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await interaction.response.send_message("❌ Ошибка.", ephemeral=True)

    @button(label="❌ Отклонить", style=ButtonStyle.danger, custom_id="reject_verification_button")
    async def reject_verification_button(self, button: Button, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator and not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
            return

        try:
            notification_channel = interaction.guild.get_channel(VERIFICATION_NOTIFICATION_CHANNEL_ID)
            if not notification_channel:
                await interaction.response.send_message("❌ Канал не найден!", ephemeral=True)
                return

            embed = Embed(
                title="❌ Верификация отклонена",
                description=f"{self.user.mention}, к сожалению, ваша верификация отклонена. Попробуйте позже.",
                color=0xFF0000,
                timestamp=datetime.now(),
            )
            embed.set_footer(text=f"Отклонено {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            embed.set_thumbnail(url=self.user.display_avatar.url)

            await notification_channel.send(embed=embed)
            await interaction.response.send_message(f"❌ {self.user.mention} отклонен!", ephemeral=True)

            self.children[0].disabled = True
            self.children[1].disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await interaction.response.send_message("❌ Ошибка.", ephemeral=True)


class ChannelSelectViewView(View):
    """View для выбора каналов категорий при откате"""
    def __init__(self, channels_category1=None, channels_category2=None):
        super().__init__()

        if channels_category1 is None:
            channels_category1 = []
        if channels_category2 is None:
            channels_category2 = []

        if channels_category1:
            for i in range(0, len(channels_category1), 25):
                group = channels_category1[i:i + 25]
                options_category1 = [SelectOption(label=channel.name, value=str(channel.id)) for channel in group]
                select_category1 = Select(
                    custom_id=f"category1_select_{i}",
                    placeholder=f"Категория 1 ({i // 25 + 1})",
                    options=options_category1
                )
                select_category1.callback = self.on_select_category1
                self.add_item(select_category1)

        if channels_category2:
            for i in range(0, len(channels_category2), 25):
                group = channels_category2[i:i + 25]
                options_category2 = [SelectOption(label=channel.name, value=str(channel.id)) for channel in group]
                select_category2 = Select(
                    custom_id=f"category2_select_{i}",
                    placeholder=f"Категория 2 ({i // 25 + 1})",
                    options=options_category2
                )
                select_category2.callback = self.on_select_category2
                self.add_item(select_category2)

    async def on_select_category1(self, interaction: Interaction):
        selected_channel_id = int(interaction.data["values"][0])
        selected_channel = interaction.guild.get_channel(selected_channel_id)
        if selected_channel:
            await interaction.response.send_modal(RollbackForm(selected_channel))
        else:
            await interaction.response.send_message("❌ Канал не найден.", ephemeral=True)

    async def on_select_category2(self, interaction: Interaction):
        selected_channel_id = int(interaction.data["values"][0])
        selected_channel = interaction.guild.get_channel(selected_channel_id)
        if selected_channel:
            await interaction.response.send_modal(RollbackForm(selected_channel))
        else:
            await interaction.response.send_message("❌ Канал не найден.", ephemeral=True)


class MainChannelButtonsView(View):
    """Кнопки главного канала"""
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="🔄 Откатить действия", style=ButtonStyle.success, custom_id="send_rollback_button")
    async def send_rollback_button(self, button: Button, interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            category1 = interaction.guild.get_channel(CATEGORY1_ID)
            category2 = interaction.guild.get_channel(CATEGORY2_ID)

            if not category1 or not category2:
                await interaction.followup.send("❌ Категории не найдены!", ephemeral=True)
                return

            channels_category1 = sorted(
                [channel for channel in category1.channels if isinstance(channel, TextChannel)],
                key=lambda x: x.created_at,
                reverse=True,
            )
            channels_category2 = sorted(
                [channel for channel in category2.channels if isinstance(channel, TextChannel)],
                key=lambda x: x.created_at,
                reverse=True,
            )

            if not channels_category1 and not channels_category2:
                await interaction.followup.send("❌ Нет доступных каналов!", ephemeral=True)
                return

            view = ChannelSelectViewView(channels_category1, channels_category2)
            await interaction.followup.send("Выберите канал:", view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Ошибка в send_rollback_button: {e}")
            await interaction.followup.send("❌ Ошибка.", ephemeral=True)

    @button(label="➕ Создать канал", style=ButtonStyle.primary, custom_id="create_channel_button")
    async def create_channel_button(self, button: Button, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Только администраторы могут создавать каналы!", ephemeral=True)
            return

        view = View()
        view.add_item(ChannelSelect())
        await interaction.response.send_message("Выберите категорию:", view=view, ephemeral=True)


class RollbackForm(disnake.ui.Modal):
    """Форма отката действий в канале"""
    def __init__(self, channel: TextChannel):
        self.channel = channel
        components = [
            disnake.ui.TextInput(
                label="📝 Детали отката",
                custom_id="rollback_details",
                style=TextInputStyle.paragraph,
                required=True,
                placeholder="Опишите, что нужно откатить...",
            ),
        ]
        super().__init__(title="🔄 Откат действий", components=components, timeout=300)

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)

        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ Ошибка: гильдия не найдена!", ephemeral=True)
                return

            rollback_details = interaction.text_values["rollback_details"]

            public_embed = Embed(
                title="🔄 Откат действий",
                description=f"{rollback_details}\n\n**Отправитель:** {interaction.user.mention}",
                color=0x3A3B3C,
                timestamp=datetime.now(),
            )
            public_embed.set_footer(text=f"Отправлено {interaction.user.display_name}")

            await self.channel.send(embed=public_embed)

            private_channel = guild.get_channel(PRIVATE_CHANNEL_ID)
            if not private_channel:
                await interaction.followup.send("❌ Приватный канал не найден!", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            channel_id = getprivatechannel(user_id)

            if channel_id:
                private_channel_instance = guild.get_channel(channel_id)
            else:
                private_channel_instance = None

            if not private_channel_instance:
                private_channel_instance = await guild.create_text_channel(
                    name=f"🔒{interaction.user.name}",
                    category=guild.get_channel(CATEGORY_ID),
                    reason="Создание приватного канала для отката",
                )
                await private_channel_instance.set_permissions(guild.default_role, view_channel=False)
                await private_channel_instance.set_permissions(interaction.user, view_channel=True)

                role = guild.get_role(PRIVATE_THREAD_ROLE_ID)
                if role:
                    await private_channel_instance.set_permissions(role, view_channel=True)

                setprivatechannel(user_id, private_channel_instance.id)

            private_embed = Embed(
                title="🔄 Откат действий",
                description=(
                    f"**Канал:** {self.channel.mention}\n"
                    f"**Детали:**\n{rollback_details}"
                ),
                color=0x3A3B3C,
                timestamp=datetime.now(),
            )
            private_embed.set_footer(text=f"Отправлено {interaction.user.display_name}")

            await private_channel_instance.send(embed=private_embed)

            confirm_embed = Embed(
                title="✅ Откат отправлен!",
                description=f"Откат отправлен в {self.channel.mention} и {private_channel_instance.mention}.",
                color=0x3BA55D,
                timestamp=datetime.now(),
            )
            await interaction.followup.send(embed=confirm_embed, ephemeral=True)

        except NotFound:
            await interaction.followup.send("❌ Канал был удалён. Попробуйте снова.", ephemeral=True)
        except Exception as e:
            print(f"❌ Ошибка в RollbackForm: {e}")
            error_embed = Embed(
                title="❌ Ошибка",
                description="Произошла ошибка при откате действий.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
