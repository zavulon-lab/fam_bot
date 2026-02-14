import asyncio
import disnake
from disnake.ext import commands
from disnake import Embed, TextInputStyle, Interaction, ButtonStyle, ChannelType, SelectOption
from disnake.ui import View, button, Button, StringSelect, Modal, TextInput
from datetime import datetime
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__)) 
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)


try:
    from constants import MCL_CHANNEL_ID, CAPT_CHANNEL_ID, CATEGORY_ID, ADMIN_MANAGEMENT_CHANNEL_ID
    from database import get_private_channel, set_private_channel
except ImportError:
    MCL_CHANNEL_ID = 1441434753369636894
    CAPT_CHANNEL_ID = 1441434661237690509
    ADMIN_MANAGEMENT_CHANNEL_ID = 1470910876860027021
    CATEGORY_ID = 0
    def get_private_channel(u): return None
    def set_private_channel(u, c): pass


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

        target_thread = interaction.guild.get_thread(self.thread_id)
        if not target_thread:
            try:
                target_thread = await interaction.guild.fetch_channel(self.thread_id)
            except disnake.NotFound:
                return await interaction.followup.send("Ветка была удалена и больше недоступна.", ephemeral=True)
            except Exception as e:
                return await interaction.followup.send(f"Ошибка доступа к ветке: {e}", ephemeral=True)

        if target_thread.archived:
            await target_thread.edit(archived=False)

        public_embed = Embed(
            description=f"**Отправитель:** {interaction.user.mention}\n\n{details}",
            color=disnake.Color.from_rgb(54, 57, 63),
            timestamp=datetime.now()
        )
        public_embed.set_author(name=f"Откат от {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        try:
            await target_thread.send(embed=public_embed)
        except Exception as e:
            return await interaction.followup.send(f"Не удалось отправить сообщение в ветку: {e}", ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            channel_id = get_private_channel(user_id)
            private_channel = interaction.guild.get_channel(channel_id) if channel_id else None
            
            if channel_id and not private_channel:
                 try: private_channel = await interaction.guild.fetch_channel(channel_id)
                 except: pass

            if not private_channel and CATEGORY_ID:
                category = interaction.guild.get_channel(CATEGORY_ID)
                if not category:
                     try: category = await interaction.guild.fetch_channel(CATEGORY_ID)
                     except: pass
                
                if category:
                    safe_name = interaction.user.name[:90]
                    existing = disnake.utils.get(category.text_channels, name=safe_name)
                    if existing:
                        private_channel = existing
                    else:
                        private_channel = await interaction.guild.create_text_channel(
                            name=safe_name, category=category, reason="Личный канал"
                        )
                        await private_channel.set_permissions(interaction.guild.default_role, view_channel=False)
                        await private_channel.set_permissions(interaction.user, view_channel=True)
                    set_private_channel(user_id, private_channel.id)

            if private_channel:
                private_embed = Embed(
                    title="Откат отправлен",
                    description=f"**Ветка:** {target_thread.mention}\n**Текст:**\n{details}",
                    color=0x3BA55D,
                    timestamp=datetime.now()
                )
                await private_channel.send(embed=private_embed)
        except Exception as e:
            print(f"Ошибка с личным каналом: {e}")

        await interaction.followup.send(f"Откат успешно отправлен в ветку {target_thread.mention}", ephemeral=True)


class ThreadSelect(StringSelect):
    def __init__(self, view_parent, threads_chunk):
        self.view_parent = view_parent
        
        options = []
        for thread in threads_chunk:
            label = (thread.name or "Без названия")[:95]
            options.append(SelectOption(
                label=label,
                value=str(thread.id),
                emoji="#️⃣"
            ))
            
        super().__init__(
            placeholder="Выберите событие (ветку)...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="thread_select"
        )

    async def callback(self, interaction: Interaction):
        thread_id = int(self.values[0])
        # Ищем имя для красоты
        selected_option = next((opt for opt in self.options if opt.value == self.values[0]), None)
        thread_name = selected_option.label if selected_option else "Unknown"
        
        await interaction.response.send_modal(RollbackForm(thread_id, thread_name))


class ThreadSelectView(View):
    def __init__(self, threads, page=0):
        super().__init__(timeout=180) # Тайм-аут 3 минуты
        self.threads = sorted(threads, key=lambda t: t.created_at or datetime.min, reverse=True)
        self.page = page
        self.items_per_page = 25
        self.total_pages = (len(self.threads) - 1) // self.items_per_page + 1

        self.update_components()

    def update_components(self):
        self.clear_items()

        start = self.page * self.items_per_page
        end = start + self.items_per_page
        chunk = self.threads[start:end]

        if chunk:
            self.add_item(ThreadSelect(self, chunk))
        else:
             sel = StringSelect(custom_id="empty", placeholder="Нет доступных веток", options=[SelectOption(label="Пусто", value="none")], disabled=True)
             self.add_item(sel)

        if self.total_pages > 1:
            prev_btn = Button(
                label="◀️ Назад",
                style=ButtonStyle.secondary,
                custom_id="prev_page",
                disabled=(self.page == 0)
            )
            prev_btn.callback = self.prev_callback
            self.add_item(prev_btn)

            info_btn = Button(
                label=f"Стр. {self.page + 1}/{self.total_pages}",
                style=ButtonStyle.secondary,
                custom_id="info_page",
                disabled=True
            )
            self.add_item(info_btn)

            next_btn = Button(
                label="Вперед ▶️",
                style=ButtonStyle.secondary,
                custom_id="next_page",
                disabled=(self.page == self.total_pages - 1)
            )
            next_btn.callback = self.next_callback
            self.add_item(next_btn)
            
        cancel_btn = Button(label="🔙 Вернуться к выбору типа", style=ButtonStyle.gray, row=2)
        cancel_btn.callback = self.cancel_callback
        self.add_item(cancel_btn)

    async def prev_callback(self, interaction: Interaction):
        if self.page > 0:
            self.page -= 1
            self.update_components()
            await interaction.response.edit_message(view=self)

    async def next_callback(self, interaction: Interaction):
        if self.page < self.total_pages - 1:
            self.page += 1
            self.update_components()
            await interaction.response.edit_message(view=self)
            
    async def cancel_callback(self, interaction: Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=Embed(
                title="📹 Как оформить откат",
                description="Выберите тип мероприятия в меню ниже:",
                color=disnake.Color.from_rgb(54, 57, 63)
            ),
            view=RollbackGuideView() 
        )


class CategorySelect(StringSelect):
    def __init__(self):
        options = [
            SelectOption(label="MCL", value="mcl", description="MCL", emoji="🛡️"),
            SelectOption(label="Капт", value="capt", description="Капт", emoji="⚔️"),
        ]
        super().__init__(placeholder="Выберите тип мероприятия...", options=options, custom_id="guide_category_select")

    async def callback(self, interaction: Interaction):
        choice = self.values[0]
        channel_id = int(MCL_CHANNEL_ID) if choice == "mcl" else int(CAPT_CHANNEL_ID)
        
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            try: channel = await interaction.guild.fetch_channel(channel_id)
            except: pass
            
        if not channel:
            await interaction.response.edit_message(content="Канал не найден, попробуйте позже.", view=RollbackGuideView())
            return

        threads = channel.threads
        if not threads:
             try: threads = await channel.active_threads()
             except: pass

        if not threads:
            await interaction.response.edit_message(
                content=f"В канале {channel.mention} нет активных событий.",
                view=RollbackGuideView() 
            )
            return
            
        paginated_view = ThreadSelectView(threads, page=0)
        
        await interaction.response.edit_message(
            content=f"📂 События в канале **{channel.name}**:\nВыберите ветку для загрузки отката:",
            embed=None,
            view=paginated_view
        )

class RollbackGuideView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategorySelect())


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
            await thread.send(
                embed=Embed(
                    description=f"📍 **Событие создано.**\nЗагружайте откаты через 'Личный кабинет'.\n**Администратор:** {interaction.user.mention}",
                    color=0x5865F2
                )
            )
            await interaction.response.send_message(f"Ветка события создана: {thread.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ошибка: {e}", ephemeral=True)


class AdminChannelSelect(StringSelect):
    def __init__(self):
        options = [
            SelectOption(label="MCL", value="mcl", emoji="🛡️"),
            SelectOption(label="Капт", value="capt", emoji="⚔️"),
        ]
        super().__init__(
            placeholder="Создать событие (выберите канал)...", 
            options=options, 
            custom_id="admin_channel_select"
        )

    async def callback(self, interaction: Interaction):
        channel_id = int(MCL_CHANNEL_ID) if self.values[0] == "mcl" else int(CAPT_CHANNEL_ID)
        
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            try: channel = await interaction.guild.fetch_channel(channel_id)
            except: pass
            
        if channel:
            await interaction.response.send_modal(AdminCreateThreadModal(channel))
            
            asyncio.create_task(self.reset_menu(interaction.message))
        else:
            await interaction.response.send_message(f"❌ Канал {channel_id} не найден.", ephemeral=True)
            # Тоже сбрасываем, чтобы убрать выделение
            asyncio.create_task(self.reset_menu(interaction.message))

    async def reset_menu(self, message):
        if not message: return
        try:
            await asyncio.sleep(1) 
            await message.edit(view=AdminButtons())
        except Exception as e:
            print(f"Ошибка сброса админ-меню: {e}")



class AdminChannelSelectView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(AdminChannelSelect())


class AdminButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(AdminChannelSelect())


class ManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(AdminButtons())
        self.bot.add_view(RollbackGuideView())

        try:
            channel_id = int(ADMIN_MANAGEMENT_CHANNEL_ID)
            admin_channel = self.bot.get_channel(channel_id)
            if not admin_channel:
                 try: admin_channel = await self.bot.fetch_channel(channel_id)
                 except: pass

            if admin_channel:
                embed = Embed(
                    title="Админ-панель событий",
                    description="Управление ветками для откатов и настройки.",
                    color=0x2B2D31,
                )
                
                last_msg = None
                async for msg in admin_channel.history(limit=5):
                    if msg.author == self.bot.user:
                        last_msg = msg
                        break
                
                if last_msg:
                    await last_msg.edit(embed=embed, view=AdminButtons())
                else:
                    await admin_channel.purge(limit=5)
                    await admin_channel.send(embed=embed, view=AdminButtons())
                
                print("[Management] Админ-панель обновлена")
        except Exception as e:
            print(f"[Management] Ошибка: {e}")


def setup(bot):
    bot.add_cog(ManagementCog(bot))
