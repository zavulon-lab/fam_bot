import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, ButtonStyle
from disnake.ui import View, Button, button
import sys
import os

# Импорт констант
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from constants import PERSONAL_CHANNEL_REQUEST_ID
except ImportError:
    PERSONAL_CHANNEL_REQUEST_ID = 0

# Импорт ваших вьюшек
from .vacation import VacationActionsView
from .portfolio import PortfolioView
from .verification import VerificationView

# --- ВАЖНО: Импорт логики откатов из соседнего кога ---
# Убедитесь, что путь правильный (cogs.management.cog)
try:
    from cogs.management import RollbackGuideView
except ImportError:
    print("⚠️ [Personal] Не удалось импортировать RollbackGuideView. Кнопка откатов не будет работать.")
    class RollbackGuideView(View): pass 


class MainMenuButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Отпуск", style=ButtonStyle.secondary, emoji="<:vocation:1472655821845299302>", custom_id="btn_main_vacation")
    async def vacation_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="<:vocation:1472655821845299302> Подать заявку на отпуск",
            description=(
                "Устали от игры или есть другие причины взять паузу? Просто заполните анкету.\n\n"
                "• При отправке формы для отпуска с вас будут сняты все роли и выдана роль инактив\n"
                "• Когда будете готовы вернуться, нажмите кнопку \"Вернуться из отпуска\"."
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1462165491278938204/1472657274949337138/image.png?ex=69935e76&is=69920cf6&hm=589aef1828709b445bb13026f3ed41c95f6cd55e00c4aba78bb445e1e06246af&")
        
        # Добавляем футер
        embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=VacationActionsView(), ephemeral=True)


    @button(label="Получение Tier", style=ButtonStyle.gray, emoji="<:Radiant_Rank:1472659589701963787>", custom_id="btn_main_tier")
    async def tier_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="<:freeiconopenfolder12075402:1472674638239633590> Создание портфеля",
            description=(
                "• В приватном канале люди с опытом оценят ваши откаты и решат — повысить вам тир.\n"
                "• Видеоматериалы желательно заливать на [YouTube](https://youtube.com), [Rutube](https://rutube.ru)\n"
                "• Профиль можно создавать только один раз, после создания профиля откаты и скрины отправляйте в свой личный профиль"
            ),  
            color=disnake.Color.from_rgb(54, 57, 63) 
        )
        embed.set_thumbnail(url="https://em-content.zobj.net/source/microsoft-teams/337/file-folder_1f4c1.png") 
        
        # Добавляем футер
        embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=PortfolioView(), ephemeral=True)


    @button(label="Верификация", style=ButtonStyle.gray, emoji="<:freeiconverified4314696:1472660305015341118>", custom_id="btn_main_verif")
    async def verif_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="<:freeiconverified4314696:1472660305015341118> Верификация и проверка на ПО",
            description=(
                "Для доступа к закрытым мероприятиям (капт, mcl) необходимо пройти полную проверку.\n\n"
                "• **Этапы проверки:**\n"
                "• **Запрос:** Нажмите «Подать запрос» в меню ниже и укажите причину.\n"
                "• **Рассмотрение:** Модераторы проверят вашу заявку.\n"
                "• **Проверка:** Вас вызовут в голосовой канал для проверки на стороннее ПО (читы, макросы).\n\n"
                "• *Любая попытка скрыть софт, отказ от проверки или выход из игры во время вызова приведет к бану и ЧС семьи.*"
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1462165491278938204/1472660927445729351/free-icon-assurance-4157131.png?ex=699361dd&is=6992105d&hm=a2bde169c1ef45f7e2ed2b415b38efcb779d5c7201dca8ba052ca4cb40dfcfad&")
            
        embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=VerificationView(), ephemeral=True)


    # --- КНОПКА ОТКАТОВ (С ГАЙДОМ) ---
    @button(label="Оформить откат", style=ButtonStyle.gray, emoji="<:freeiconyoutube1384060:1472661242941411458>", custom_id="btn_main_rollback")
    async def rollback_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="<:freeiconyoutube1384060:1472661242941411458> Как оформить откат",
            description=(
                "**Инструкция:**\n"
                "1. Залейте видео на хостинг.\n"
                "2. Скопируйте ссылку.\n"
                "3. Подготовьте таймкоды (если нужно).\n\n"
                "**Выберите тип мероприятия в меню ниже:**"
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1462165491278938204/1472661416002720008/free-icon-photograph-2201587.png?ex=69936252&is=699210d2&hm=2a0a10fc30f528ae81c6fdc5e9dbd89146ec5dc1638a029ca06d5ddeaf557bf3&")
        
        embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=RollbackGuideView(), ephemeral=True)



class PersonalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            channel = self.bot.get_channel(PERSONAL_CHANNEL_REQUEST_ID)
            if channel:
                self.bot.add_view(MainMenuButtons())
                
                await channel.purge(limit=10)
                
                embed = Embed(
                    title="Взаимодействие с функционалом бота",
                    description=(
                        "> **Отпуск** — Взять долгосрочный отпуск, отдых от игры\n"
                        "> **Тир** — Создание портфеля, получить Tier роль\n"
                        "> **Верификация** — Пройти проверку для доступа к каптам\n"
                        "> **Откат** — Загрузить запись с мероприятия"
                    ),
                    color=disnake.Color.from_rgb(54, 57, 63)
                )

                # Установка маленькой иконки справа (thumbnail)
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1462165491278938204/1472658385102049392/free-icon-boy-4537055.png") 

                # Футер с названием семьи и аватаркой бота
                embed.set_footer(text="Calogero Famq", icon_url=self.bot.user.display_avatar.url)

                
                await channel.send(embed=embed, view=MainMenuButtons())
                print("[Personal] Главное меню обновлено")
        except Exception as e:
            print(f"[Personal] Ошибка: {e}")



def setup(bot):
    bot.add_cog(PersonalCog(bot))
