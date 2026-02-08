import disnake
from disnake.ext import commands
from disnake import Embed, TextInputStyle, Interaction, ButtonStyle, ChannelType, SelectOption
from disnake.ui import View, button, Button, StringSelect, Modal, TextInput
from datetime import datetime
import sys
import os

# --- ИМПОРТ КОНСТАНТ ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from constants import MAIN_CHANNEL_ID, CAPT_CHANNEL_ID, MCL_CHANNEL_ID, CATEGORY_ID
    from database import get_private_channel, set_private_channel
except ImportError:
    MAIN_CHANNEL_ID = 0
    CAPT_CHANNEL_ID = 0
    MCL_CHANNEL_ID = 0
    CATEGORY_ID = 0

    def get_private_channel(u): return None
    def set_private_channel(u, c): pass


# --- 1. ФОРМА ОТКАТА (ФИНАЛЬНЫЙ ШАГ) ---
class RollbackForm(Modal):
    def __init__(self, thread_id: int, thread_name: str):
        self.thread_id = thread_id
        self.thread_name = thread_name
        
        components = [
            TextInput(
                label="Ссылка на откат и таймкоды",
                custom_id="rollback_details",
                style=TextInputStyle.paragraph,
                required=True,
                placeholder="Ссылка: https://...\nТаймкоды: 0:45 нарушение...",
            )
        ]
        super().__init__(title="Отправка отката", components=components, timeout=300)

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        details = interaction.text_values["rollback_details"]

        # Получаем объект ветки заново по ID, чтобы избежать ошибок с устаревшими объектами
        target_thread = interaction.guild.get_thread(self.thread_id)
        
        # Если get_thread вернул None (ветка старая или не в кэше), пробуем fetch
        if not target_thread:
            try:
                target_thread = await interaction.guild.fetch_channel(self.thread_id)
            except disnake.NotFound:
                return await interaction.followup.send("❌ Ветка была удалена и больше недоступна.", ephemeral=True)
            except Exception as e:
                return await interaction.followup.send(f"❌ Ошибка доступа к ветке: {e}", ephemeral=True)

        # Если ветка в архиве — разархивируем
        if target_thread.archived:
            await target_thread.edit(archived=False)

        # Отправляем в выбранную ветку
        public_embed = Embed(
            description=f"**Отправитель:** {interaction.user.mention}\n\n{details}",
            color=0x3A3B3C,
            timestamp=datetime.now()
        )
        public_embed.set_author(name=f"Откат от {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        try:
            await target_thread.send(embed=public_embed)
        except Exception as e:
            return await interaction.followup.send(f"❌ Не удалось отправить сообщение в ветку: {e}", ephemeral=True)

        # Логика ПРИВАТНОГО канала (дублирование)
        try:
            user_id = str(interaction.user.id)
            channel_id = get_private_channel(user_id)
            private_channel = interaction.guild.get_channel(channel_id) if channel_id else None

            if not private_channel:
                category = interaction.guild.get_channel(CATEGORY_ID)
                if category:
                    safe_name = interaction.user.name[:90]
                    # Проверяем, нет ли уже такого канала (на случай рассинхрона базы)
                    existing = disnake.utils.get(category.text_channels, name=safe_name)
                    if existing:
                        private_channel = existing
                    else:
                        private_channel = await interaction.guild.create_text_channel(
                            name=safe_name,
                            category=category,
                            reason="Личный канал"
                        )
                        await private_channel.set_permissions(interaction.guild.default_role, view_channel=False)
                        await private_channel.set_permissions(interaction.user, view_channel=True)
                    
                    set_private_channel(user_id, private_channel.id)

            if private_channel:
                private_embed = Embed(
                    title="✅ Откат отправлен",
                    description=f"**Ветка:** {target_thread.mention}\n**Текст:**\n{details}",
                    color=0x3BA55D,
                    timestamp=datetime.now()
                )
                await private_channel.send(embed=private_embed)
        except Exception as e:
            print(f"Ошибка с личным каналом: {e}")

        await interaction.followup.send(f"✅ Откат успешно отправлен в ветку {target_thread.mention}", ephemeral=True)


# --- 2. ВЫБОР КОНКРЕТНОЙ ВЕТКИ ---
class ThreadSelect(StringSelect):
    def __init__(self, threads):
        options = []
        # Сортируем ветки (сначала новые) и берем последние 25
        # Фильтруем None в created_at на всякий случай
        sorted_threads = sorted(threads, key=lambda t: t.created_at or datetime.min, reverse=True)[:25]
        
        for thread in sorted_threads:
            options.append(SelectOption(
                label=(thread.name or "Без названия")[:100],
                value=str(thread.id),
                emoji="#️⃣"
            ))
        
        if not options:
            options.append(SelectOption(label="Нет активных веток", value="none"))

        super().__init__(
            placeholder="Выберите событие (ветку)...",
            options=options,
            min_values=1,
            max_values=1,
            disabled=len(options) == 0 or options[0].value == "none"
        )

    async def callback(self, interaction: Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Нет веток для выбора.", ephemeral=True)
            return
            
        thread_id = int(self.values[0])
        # Мы можем получить имя из options, чтобы передать в форму для красоты, 
        # но объект потока получим уже внутри формы для надежности.
        selected_option = next((opt for opt in self.options if opt.value == self.values[0]), None)
        thread_name = selected_option.label if selected_option else "Unknown"
        
        await interaction.response.send_modal(RollbackForm(thread_id, thread_name))


class ThreadSelectView(View):
    def __init__(self, threads):
        super().__init__(timeout=60)
        self.add_item(ThreadSelect(threads))


# --- 3. ВЫБОР ТИПА МЕРОПРИЯТИЯ (MCL / CAPT) ---
class CategorySelect(StringSelect):
    def __init__(self):
        options = [
            SelectOption(label="MCL", value="mcl", description="Мероприятия MCL", emoji="🛡️"),
            SelectOption(label="Капт", value="capt", description="Капты", emoji="⚔️"),
        ]
        super().__init__(placeholder="Выберите тип мероприятия...", options=options)

    async def callback(self, interaction: Interaction):
        choice = self.values[0]
        channel_id = MCL_CHANNEL_ID if choice == "mcl" else CAPT_CHANNEL_ID
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel:
            await interaction.response.send_message("❌ Ошибка настройки: Канал не найден.", ephemeral=True)
            return

        # Ищем активные ветки в канале
        threads = channel.threads
        
        if not threads:
            await interaction.response.send_message(
                f"⚠️ В канале {channel.mention} нет активных веток (событий).\nПопросите администратора создать ветку.",
                ephemeral=True
            )
            return
            
        await interaction.response.send_message(
            "Выберите конкретное событие:",
            view=ThreadSelectView(threads),
            ephemeral=True
        )


class CategorySelectView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(CategorySelect())


# --- 4. АДМИНСКАЯ ФОРМА СОЗДАНИЯ ВЕТКИ ---
class AdminCreateThreadModal(Modal):
    def __init__(self, target_channel: disnake.TextChannel):
        self.target_channel = target_channel
        components = [
            TextInput(
                label="Название события",
                custom_id="thread_name",
                style=TextInputStyle.short,
                required=True,
                max_length=50,
                placeholder="Например: Капт против FamQ 18:00"
            )
        ]
        super().__init__(title="Создание события", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        name = interaction.text_values["thread_name"]
        
        try:
            thread = await self.target_channel.create_thread(
                name=name,
                type=ChannelType.public_thread,
                reason=f"Создано администратором {interaction.user}"
            )
            
            # Отправляем стартовое сообщение, чтобы ветка не была пустой
            await thread.send(
                embed=Embed(
                    description=f"📍 **Событие создано.**\nЗагружайте откаты сюда через панель управления.\n**Администратор:** {interaction.user.mention}",
                    color=0x5865F2
                )
            )
            
            await interaction.response.send_message(f"✅ Ветка события создана: {thread.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class AdminChannelSelect(StringSelect):
    def __init__(self):
        options = [
            SelectOption(label="MCL", value="mcl", emoji="🛡️"),
            SelectOption(label="Капт", value="capt", emoji="⚔️"),
        ]
        super().__init__(placeholder="Где создать событие?", options=options)

    async def callback(self, interaction: Interaction):
        channel_id = MCL_CHANNEL_ID if self.values[0] == "mcl" else CAPT_CHANNEL_ID
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            await interaction.response.send_modal(AdminCreateThreadModal(channel))
        else:
            await interaction.response.send_message("❌ Канал не найден", ephemeral=True)


class AdminChannelSelectView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(AdminChannelSelect())


# --- 5. ГЛАВНОЕ МЕНЮ ---
class MainChannelButtons(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="🔄 Оформить откат", style=ButtonStyle.success, custom_id="btn_user_rollback")
    async def user_rollback_btn(self, button: Button, interaction: Interaction):
        await interaction.response.send_message(
            "Выберите тип мероприятия:",
            view=CategorySelectView(),
            ephemeral=True
        )

    @button(label="➕ Создать событие", style=ButtonStyle.primary, custom_id="btn_admin_create_thread")
    async def admin_create_btn(self, button: Button, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Только для администраторов!", ephemeral=True)
            return

        await interaction.response.send_message(
            "В каком канале создать ветку?",
            view=AdminChannelSelectView(),
            ephemeral=True
        )


class ManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Используем Persistent Views
        self.bot.add_view(MainChannelButtons(self.bot))
        
        try:
            main_channel = self.bot.get_channel(MAIN_CHANNEL_ID)
            if main_channel:
                # Обновляем сообщение вместо полного удаления, если оно последнее и от бота
                last_message = None
                async for msg in main_channel.history(limit=1):
                    last_message = msg
                
                embed = Embed(
                    title="🎮 Управление событиями",
                    description=(
                        "**Игрокам:** Нажмите `🔄 Оформить откат`, выберите событие и прикрепите ссылку.\n"
                        "**Админам:** Нажмите `➕ Создать событие`, чтобы открыть новую ветку для откатов."
                    ),
                    color=0x2B2D31,
                )

                if last_message and last_message.author == self.bot.user:
                    await last_message.edit(embed=embed, view=MainChannelButtons(self.bot))
                else:
                    await main_channel.purge(limit=5)
                    await main_channel.send(embed=embed, view=MainChannelButtons(self.bot))
                
                print("✅ [Management] Панель обновлена")
        except Exception as e:
            print(f"❌ [Management] Ошибка: {e}")


def setup(bot):
    bot.add_cog(ManagementCog(bot))
