import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, ButtonStyle
from disnake.ui import View, Button, button
from constants import PERSONAL_CHANNEL_REQUEST_ID

from .vacation import VacationActionsView
from .portfolio import PortfolioView
from .verification import VerificationView

class MainMenuButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Отпуск", style=ButtonStyle.secondary, emoji="📅", custom_id="btn_main_vacation")
    async def vacation_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="📅 Подать заявку на отпуск",
            description=(
                "👇 Устали от игры или есть другие причины взять паузу? Просто заполните анкету — её рассмотрят наши модераторы.\n\n"
                "• Если заявка будет одобрена, бот автоматически снимет с вас все текущие роли и выдаст роль @Inactive.\n"
                "• Когда будете готовы вернуться, нажмите кнопку \"Вернуться из отпуска\"."
            ),
            color=0x2B2D31
        )
        # Картинка thumbnail
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3143/3143636.png")
        await interaction.response.send_message(embed=embed, view=VacationActionsView(), ephemeral=True)

    @button(label="Получение Tier", style=ButtonStyle.primary, emoji="📹", custom_id="btn_main_tier")
    async def tier_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="📁 Создание портфеля",
            description=(
                "• В приватном канале люди с опытом оценят ваши откаты и решат — повысить вам тир.\n"
                "• Видеоматериалы желательно заливать на [YouTube](https://youtube.com), [Rutube](https://rutube.ru)"
            ),
            color=0x2B2D31 
        )
        embed.set_thumbnail(url="https://em-content.zobj.net/source/microsoft-teams/337/file-folder_1f4c1.png") 
        await interaction.response.send_message(embed=embed, view=PortfolioView(), ephemeral=True)

    @button(label="Верификация", style=ButtonStyle.success, emoji="✅", custom_id="btn_main_verif")
    async def verif_btn(self, button: Button, interaction: Interaction):
        embed = Embed(
            title="🔍 Верификация и проверка на ПО",
            description=(
                "Для доступа к закрытым мероприятиям (капты, турниры) необходимо пройти полную проверку.\n\n"
                "**Этапы проверки:**\n"
                "1️⃣ **Запрос:** Нажмите «Подать запрос» в меню ниже и укажите причину.\n"
                "2️⃣ **Рассмотрение:** Модераторы проверят вашу заявку.\n"
                "3️⃣ **Проверка:** Вас вызовут в голосовой канал для проверки на стороннее ПО (читы, макросы).\n\n"
                "⚠️ *Любая попытка скрыть софт, отказ от проверки или выход из игры во время вызова приведет к бану и ЧС семьи.*"
            ),
            color=0x3A3B3C,
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="Administration Cartel Famq")
        
        await interaction.response.send_message(embed=embed, view=VerificationView(), ephemeral=True)

class PersonalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            channel = self.bot.get_channel(PERSONAL_CHANNEL_REQUEST_ID)
            if channel:
                await channel.purge(limit=10)
                embed = Embed(
                    title="⚙️ Взаимодействие с функционалом бота",
                    description=(
                        "📅 **Отпуск** — Взять долгосрочный отпуск, отдых от игры\n"
                        "📹 **Тир** — Создание портфеля, получить Tier роль\n"
                        "✅ **Верификация** — Пройти проверку для доступа к каптам"
                    ),
                    color=0x2B2D31
                )
                # Ваша картинка
                embed.set_image(url="https://media.discordapp.net/attachments/1336423985794682974/1336423986381754409/6FDCFF59-EFBB-4D26-9E57-50B0F3D61B50.jpg") 
                await channel.send(embed=embed, view=MainMenuButtons())
                print("✅ [Personal] Главное меню обновлено")
        except Exception as e:
            print(f"❌ [Personal] Ошибка: {e}")

def setup(bot):
    bot.add_cog(PersonalCog(bot))
