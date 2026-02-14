from disnake.ext import commands
from disnake import Embed
import disnake
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
            
            # Один эмбед
            embed = Embed(
                title="Оформление заявки в семью.",
                description=(
                    "Уведомление о приглашении на обзвон отправляется в личные сообщения.\n\n"
                    "> В среднем заявки обрабатываются в течение 1–2 дней — всё зависит от загруженности.\n\n"
                    "Следите за статусом набора. **Если возможности заполнить заявку нет – набор закрыт. Каждое открытие набора сопровождается тегами в этом канале.**\n\n"
                    "> В случае отказа можете подать заявку повторно\n\n"
                    "Подавай заявку! Мы ждем именно **тебя**."
                ),
                color=disnake.Color.from_rgb(54, 57, 63)
            )
            
            # Картинка ВНИЗУ (большой баннер)
            embed.set_image(url="https://cdn.discordapp.com/attachments/1462165491278938204/1470539186263167197/40537AAF-2D0F-4121-BA76-294AB8451EE0.png?ex=698ba9d7&is=698a5857&hm=15d3b47d64d4bddcb80a6b39194de09633cfd4c20582d2e66e8deb50ad5f7735&")
            
            # Автор "Calogero Famq" СНИЗУ (в футере)
            embed.set_footer(text="Calogero Famq", icon_url=self.bot.user.display_avatar.url)
            
            await app_channel.send(embed=embed, view=ApplicationChannelView(self.bot))
            print("[Applications] Канал подачи заявок обновлен.")

        # --- АДМИН ПАНЕЛЬ ---
        admin_channel = self.bot.get_channel(APPLICATION_ADMIN_PANEL_ID)
        if admin_channel:
            await admin_channel.purge(limit=10)
            
            embed = Embed(
                title="🛠️ Управление заявками",
                description=(
                    "Добро пожаловать в панель управления набором!\n"
                    "Здесь вы можете настроить статус приема заявок, изменить вопросы анкеты и управлять процессом рекрутинга.\n\n"
                    "📌 **Доступные действия:**\n"
                    "• 🟢 **Открыть набор** — Разрешить подачу заявок.\n"
                    "• 🔴 **Закрыть набор** — Временно приостановить прием.\n"
                    "• 📝 **Редактировать вопросы** — Изменить анкету для кандидатов.\n"
                    "• 🔄 **Сброс** — Вернуть настройки по умолчанию."
                ),
                color=disnake.Color.from_rgb(54, 57, 63)
            )
            
            
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1336423985794682974/1336423986381754409/6FDCFF59-EFBB-4D26-9E57-50B0F3D61B50.jpg")
            
            # Футер с аватаркой бота
            embed.set_footer(text="Calogero Famq • Admin Panel", icon_url=self.bot.user.display_avatar.url)
            
            await admin_channel.send(embed=embed, view=ApplicationAdminView())
            print("[Applications] Админ-панель обновлена.")


def setup(bot):
    bot.add_cog(ApplicationsCog(bot))
