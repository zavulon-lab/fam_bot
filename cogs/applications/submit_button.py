import asyncio
from disnake import Embed, Interaction, SelectOption
from disnake.ui import View, Select
from database import get_application_form, get_applications_status
from .utils import migrate_old_form_data
from .form_modal import CompleteApplicationModal

class ApplicationSelect(Select):
    def __init__(self, bot):
        self.bot = bot
        self.is_enabled = get_applications_status()
        
        options = [
            SelectOption(
                label="Заполнить заявку",
                description="Заполнить заявку на вступление в семью",
                value="start_application",
                emoji="📄"
            )
        ]
        
        placeholder = "Выберите действие..."
        if not self.is_enabled:
            placeholder = "⛔ Набор закрыт"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            custom_id="app_select_menu",
            disabled=not self.is_enabled
        )

    async def callback(self, interaction: Interaction):
        # 1. Проверка статуса
        if not get_applications_status():
             await interaction.response.send_message(
                embed=Embed(title="⛔ Набор закрыт", description="Прием заявок приостановлен.", color=0xED4245),
                ephemeral=True
            )
             # Сбрасываем меню даже при отказе
             await self.reset_view(interaction.message)
             return

        if self.values[0] == "start_application":
            form_config = get_application_form()
            form_config = migrate_old_form_data(form_config)
            
            if not form_config:
                await interaction.response.send_message(
                    embed=Embed(title="❌ Ошибка", description="Форма не настроена.", color=0xED4245),
                    ephemeral=True
                )
                await self.reset_view(interaction.message)
                return
            
            # 2. Открываем модалку
            # Мы передаем message_to_reset=None в модалку, так как сброс сделаем здесь
            await interaction.response.send_modal(CompleteApplicationModal(self.bot, form_config, message_to_reset=None))
            
            # 3. ЗАПУСКАЕМ СБРОС МЕНЮ В ФОНЕ
            # Это сработает параллельно и вернет меню в исходное состояние (Placeholder)
            asyncio.create_task(self.reset_view(interaction.message))

    async def reset_view(self, message):
        """Сбрасывает View сообщения через небольшую паузу"""
        if not message: return
        try:
            await asyncio.sleep(0.5) # Небольшая задержка, чтобы API успел обработать модалку
            # Пересоздаем View, чтобы сбросить выбор в Select
            await message.edit(view=ApplicationChannelView(self.bot))
        except Exception as e:
            print(f"[AppSelect] Ошибка сброса меню: {e}")

class ApplicationChannelView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(ApplicationSelect(bot))
