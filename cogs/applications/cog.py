from disnake.ext import commands
from disnake import Embed
from constants import APPLICATION_CHANNEL_ID, APPLICATION_ADMIN_PANEL_ID
from .submit_button import ApplicationChannelView
from .admin_panel import ApplicationAdminView

class ApplicationsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # --- КАНАЛ ПОДАЧИ ЗАЯВОК ---
        app_channel = self.bot.get_channel(APPLICATION_CHANNEL_ID)
        if app_channel:
            await app_channel.purge(limit=10)
            
            # Эмбед как на скриншоте 2C9E641E...
            embed = Embed(
                title="Оформление заявки в семью.",
                description=(
                    "Уведомление о приглашении на обзвон отправляется в личные сообщения.\n\n"
                    "> В среднем заявки обрабатываются в течение 2–4 дней — всё зависит от загруженности.\n\n"
                    "Следите за статусом набора. **Если возможности создать заявку нет – набор закрыт. Каждое открытие набора сопровождается тегами в этом канале.**\n\n"
                    "> В случае отказа накладывается недельное ограничение на создание новой заявки.\n\n"
                    "Подавай заявку! Мы ждем именно **тебя**."
                ),
                color=0x2B2D31, 
            )
            # Убираем картинку снизу, если нужен стиль "текстового" эмбеда
            # embed.set_footer(...) - можно добавить автора, как на скрине
            embed.set_author(name="cxrpses", icon_url=self.bot.user.display_avatar.url) 
            embed.set_footer(text="Вчера, в 20:15") # Статичный текст для стиля, или real timestamp
            
            await app_channel.send(embed=embed, view=ApplicationChannelView(self.bot))
            print("[Applications] Канал подачи заявок обновлен.")

        # --- АДМИН ПАНЕЛЬ ---
        admin_channel = self.bot.get_channel(APPLICATION_ADMIN_PANEL_ID)
        if admin_channel:
            await admin_channel.purge(limit=10)
            embed = Embed(
                title="🛠️ Управление заявками",
                description="Используйте меню ниже для настройки анкеты и статуса набора.",
                color=0x2B2D31
            )
            await admin_channel.send(embed=embed, view=ApplicationAdminView())
            print("[Applications] Админ-панель обновлена.")

def setup(bot):
    bot.add_cog(ApplicationsCog(bot))
