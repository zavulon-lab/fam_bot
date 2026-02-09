"""Кнопка/Меню подачи заявки в публичном канале"""

from disnake import Embed, Interaction, SelectOption
from disnake.ui import View, Select
from database import get_application_form, get_applications_status
from .utils import migrate_old_form_data
from .form_modal import CompleteApplicationModal

class ApplicationSelect(Select):
    def __init__(self, bot):
        self.bot = bot
        
        # Получаем статус на момент создания View
        self.is_enabled = get_applications_status()
        
        # Настройка опций
        options = [
            SelectOption(
                label="Заполнить заявку",
                description="Заполнить заявку на вступление в семью",
                value="start_application",
                emoji="📄"
            )
        ]
        
        # Если набор закрыт:
        # 1. Меняем placeholder
        # 2. Делаем меню disabled (некликабельным)
        placeholder = "Выберите действие..."
        if not self.is_enabled:
            placeholder = "⛔ Набор закрыт"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            custom_id="app_select_menu",
            disabled=not self.is_enabled # БЛОКИРУЕМ МЕНЮ
        )

    async def callback(self, interaction: Interaction):
        # Двойная проверка на всякий случай (хотя меню заблокировано)
        if not get_applications_status():
             await interaction.response.send_message(
                embed=Embed(title="⛔ Набор закрыт", description="Прием заявок приостановлен.", color=0xED4245),
                ephemeral=True
            )
             return

        if self.values[0] == "start_application":
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
        # При создании View создается Select, который сам проверит статус
        self.add_item(ApplicationSelect(bot))
