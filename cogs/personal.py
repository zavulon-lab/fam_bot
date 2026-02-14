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

    @button(label="Отпуск", style=ButtonStyle.secondary, emoji="📅", custom_id="btn_main_vacation")
    async def vacation_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="📅 Подать заявку на отпуск",
            description=(
                "👇 Устали от игры или есть другие причины взять паузу? Просто заполните анкету — её рассмотрят наши модераторы.\n\n"
                "• Если заявка будет одобрена, бот автоматически снимет с вас все текущие роли и выдаст роль Inactive.\n"
                "• Когда будете готовы вернуться, нажмите кнопку \"Вернуться из отпуска\"."
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3143/3143636.png")
        
        # Добавляем футер
        embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=VacationActionsView(), ephemeral=True)


    @button(label="Получение Tier", style=ButtonStyle.gray, emoji="📹", custom_id="btn_main_tier")
    async def tier_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="📁 Создание портфеля",
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


    @button(label="Верификация", style=ButtonStyle.gray, emoji="✅", custom_id="btn_main_verif")
    async def verif_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="🔍 Верификация и проверка на ПО",
            description=(
                "Для доступа к закрытым мероприятиям (капты, турниры) необходимо пройти полную проверку.\n\n"
                "• **Этапы проверки:**\n"
                "• **Запрос:** Нажмите «Подать запрос» в меню ниже и укажите причину.\n"
                "• **Рассмотрение:** Модераторы проверят вашу заявку.\n"
                "• **Проверка:** Вас вызовут в голосовой канал для проверки на стороннее ПО (читы, макросы).\n\n"
                "• *Любая попытка скрыть софт, отказ от проверки или выход из игры во время вызова приведет к бану и ЧС семьи.*"
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
            
        # Устанавливаем футер с текстом и аватаркой бота
        embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=VerificationView(), ephemeral=True)


    # --- КНОПКА ОТКАТОВ (С ГАЙДОМ) ---
    @button(label="Оформить откат", style=ButtonStyle.gray, emoji="🔄", custom_id="btn_main_rollback")
    async def rollback_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="📹 Как оформить откат",
            description=(
                "**Инструкция:**\n"
                "1. Залейте видео на хостинг.\n"
                "2. Скопируйте ссылку.\n"
                "3. Подготовьте таймкоды (если нужно).\n\n"
                "👇 **Выберите тип мероприятия в меню ниже:**"
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2965/2965279.png")
        
        # Добавляем футер с именем и аватаркой бота
        embed.set_footer(text="Calogero Famq", icon_url=interaction.client.user.display_avatar.url)
        
        # Теперь RollbackGuideView содержит сразу Select, а не кнопку
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
                    title="⚙️ Взаимодействие с функционалом бота",
                    description=(
                        "> **Отпуск** — Взять долгосрочный отпуск, отдых от игры\n"
                        "> **Тир** — Создание портфеля, получить Tier роль\n"
                        "> **Верификация** — Пройти проверку для доступа к каптам\n"
                        "> **Откат** — Загрузить запись с мероприятия"
                    ),
                    color=0x2B2D31
                )
                embed.set_image(url="https://media.discordapp.net/attachments/1336423985794682974/1336423986381754409/6FDCFF59-EFBB-4D26-9E57-50B0F3D61B50.jpg") 
                
                embed.set_footer(text="Calogero Famq", icon_url=self.bot.user.display_avatar.url)
                
                await channel.send(embed=embed, view=MainMenuButtons())
                print("[Personal] Главное меню обновлено")
        except Exception as e:
            print(f"[Personal] Ошибка: {e}")



def setup(bot):
    bot.add_cog(PersonalCog(bot))
