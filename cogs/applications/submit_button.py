from disnake import Embed, Interaction, SelectOption
from disnake.ui import View, Select
from database import get_application_form
from .utils import migrate_old_form_data
from .form_modal import CompleteApplicationModal

# Глобальная переменная (или импортируйте из конфига/БД)
APPLICATIONS_ENABLED = True

class ApplicationSelect(Select):
    def __init__(self, bot, disabled=False):
        self.bot = bot
        
        # Настройка опций
        options = [
            SelectOption(
                label="Создать заявку",
                description="Создать заявку на вступление в семью",
                value="start_application",
                emoji="📄"
            )
        ]
        
        # Если набор закрыт, placeholder другой
        placeholder = "Выберите действие..."
        if disabled:
            placeholder = "⛔ Набор закрыт"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            custom_id="app_select_menu",
            disabled=disabled # Блокируем само меню
        )

    async def callback(self, interaction: Interaction):
        if self.values[0] == "start_application":
            # Дополнительная проверка на всякий случай
            if not APPLICATIONS_ENABLED:
                await interaction.response.send_message(
                    embed=Embed(title="⛔ Набор закрыт", description="Прием заявок приостановлен.", color=0xED4245),
                    ephemeral=True
                )
                return

            form_config = get_application_form()
            form_config = migrate_old_form_data(form_config)
            
            if not form_config:
                await interaction.response.send_message(
                    embed=Embed(title="❌ Ошибка", description="Форма не настроена.", color=0xED4245),
                    ephemeral=True
                )
                return
            
            # Передаем message, чтобы модалка могла его обновить (сбросить меню)
            await interaction.response.send_modal(CompleteApplicationModal(self.bot, form_config, interaction.message))


class ApplicationChannelView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        # Передаем статус APPLICATIONS_ENABLED в Select
        self.add_item(ApplicationSelect(bot, disabled=not APPLICATIONS_ENABLED))
