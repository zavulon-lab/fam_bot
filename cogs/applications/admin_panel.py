"""Админ-панель для управления формой заявок"""

import disnake
from disnake import Embed, TextInputStyle, Interaction, ButtonStyle, SelectOption
from disnake.ui import View, Button, Modal, TextInput, StringSelect
from database import get_application_form, save_application_form, get_applications_status, set_applications_status
from .utils import generate_custom_id, migrate_old_form_data
from constants import APPLICATION_CHANNEL_ID

class FieldTypeSelectView(View):
    """View с селектом для выбора типа поля"""
    def __init__(self, field_index: int = None):
        super().__init__(timeout=300)
        self.field_index = field_index
        
        select = StringSelect(
            placeholder="Выберите тип поля...",
            options=[
                SelectOption(label="Текстовое поле (короткое)", value="text_short", description="Однострочное (Ник, Имя, Возраст)"),
                SelectOption(label="Текстовое поле (длинное)", value="text_long", description="Многострочное (О себе, Опыт, Цели)"),
            ],
            custom_id="field_type_select"
        )
        
        async def select_callback(interaction: Interaction):
            field_type = interaction.data["values"][0]
            style = "short" if field_type == "text_short" else "paragraph"
            await interaction.response.send_modal(TextFieldEditorModal(self.field_index, style=style))
        
        select.callback = select_callback
        self.add_item(select)

class TextFieldEditorModal(Modal):
    """Редактор текстового поля"""
    def __init__(self, field_index: int = None, existing_field: dict = None, style: str = "short"):
        self.field_index = field_index
        self.is_new = field_index is None
        self.existing_field = existing_field
        self.style = style
        
        default_label = existing_field.get("label", "") if existing_field else ""
        default_placeholder = existing_field.get("placeholder", "") if existing_field else ""
        
        components = [
            TextInput(
                label="Название вопроса",
                custom_id="field_label",
                style=TextInputStyle.short,
                required=True,
                max_length=45,
                value=default_label,
                placeholder="Например: Ваше Имя и Возраст"
            ),
            TextInput(
                label="Подсказка внутри поля (необязательно)",
                custom_id="field_placeholder",
                style=TextInputStyle.short,
                required=False,
                max_length=100,
                value=default_placeholder,
                placeholder="Например: Иван, 20 лет"
            )
        ]
        
        title = f"{'Добавить' if self.is_new else 'Изменить'} {'короткое' if style == 'short' else 'длинное'} поле"
        super().__init__(title=title, components=components, timeout=300)

    async def callback(self, interaction: disnake.ModalInteraction):
        try:
            label = interaction.text_values["field_label"].strip()
            placeholder = interaction.text_values["field_placeholder"].strip()
            
            if self.existing_field:
                custom_id = self.existing_field["custom_id"]
            else:
                custom_id = generate_custom_id(label)

            required_view = View(timeout=60)
            required_select = StringSelect(
                placeholder="Это поле обязательно?",
                options=[
                    SelectOption(label="Да, обязательно", value="yes", emoji="✅"),
                    SelectOption(label="Нет, можно пропустить", value="no", emoji="❌")
                ],
                custom_id="required_select"
            )
            
            async def required_callback(inter: Interaction):
                required_value = inter.data["values"][0]
                
                new_field = {
                    "type": "text_input",
                    "label": label,
                    "custom_id": custom_id,
                    "style": self.style,
                    "required": required_value == "yes",
                    "placeholder": placeholder,
                    "min_length": None,
                    "max_length": None,
                    "options": []
                }
                
                current_form = get_application_form()
                current_form = migrate_old_form_data(current_form)
                
                if self.is_new:
                    current_form.append(new_field)
                else:
                    if self.field_index < len(current_form):
                        current_form[self.field_index] = new_field
                
                save_application_form(current_form)
                
                embed = Embed(
                    title="✅ Поле сохранено!",
                    description=f"**Вопрос:** {new_field['label']}\n**Тип:** {'Короткий ответ' if new_field['style']=='short' else 'Длинный ответ'}\n**Обязательно:** {'Да' if new_field['required'] else 'Нет'}",
                    color=0x3BA55D
                )
                await inter.response.send_message(embed=embed, ephemeral=True)
            
            required_select.callback = required_callback
            required_view.add_item(required_select)
            
            req_embed = Embed(
                title="Настройка поля",
                description="Нужно ли обязательно отвечать на этот вопрос?",
                color=0x5865F2
            )
            await interaction.response.send_message(embed=req_embed, view=required_view, ephemeral=True)
            
        except Exception as e:
            print(f"[ERROR] Ошибка в TextFieldEditorModal: {e}")
            error_embed = Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка: `{str(e)}`",
                color=0xED4245
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

class FieldDeleteSelectView(View):
    """View для удаления поля"""
    def __init__(self):
        super().__init__(timeout=300)
        current_form = get_application_form()
        current_form = migrate_old_form_data(current_form)
        
        options = []
        for i, field in enumerate(current_form):
            options.append(
                SelectOption(
                    label=f"{i+1}. {field['label'][:90]}",
                    value=str(i),
                    description="Нажмите, чтобы удалить"
                )
            )
        
        select = StringSelect(
            placeholder="Выберите поле для удаления...",
            options=options,
            custom_id="delete_field_select"
        )
        
        async def select_callback(interaction: Interaction):
            field_index = int(interaction.data["values"][0])
            
            current = get_application_form()
            current = migrate_old_form_data(current)
            
            if field_index < len(current):
                deleted_field = current.pop(field_index)
                save_application_form(current)
                
                embed = Embed(
                    title="🗑️ Поле удалено",
                    description=f"Удален вопрос: **{deleted_field['label']}**",
                    color=0x3BA55D
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                error_embed = Embed(
                    title="❌ Ошибка",
                    description="Поле не найдено!",
                    color=0xED4245
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        
        select.callback = select_callback
        self.add_item(select)

class ApplicationAdminSelect(StringSelect):
    """Главное меню админ-панели"""
    def __init__(self):
        self.is_enabled = get_applications_status()
        status_emoji = "✅" if self.is_enabled else "⛔"
        status_label = "ВЫКЛЮЧИТЬ прием заявок" if self.is_enabled else "ВКЛЮЧИТЬ прием заявок"
        
        options = [
            SelectOption(label="Настроить форму", value="configure_form", description="Добавить или изменить вопросы", emoji="⚙️"),
            SelectOption(label="Посмотреть текущую форму", value="view_form", description="Как выглядит анкета сейчас", emoji="📋"),
            SelectOption(label="Удалить вопрос", value="delete_field", description="Убрать лишний вопрос", emoji="🗑️"),
            SelectOption(label=status_label, value="toggle_status", description="Открыть/Закрыть набор", emoji=status_emoji),
            SelectOption(label="Сбросить настройки", value="reset_form", description="Вернуть стандартную анкету", emoji="🔄"),
        ]
        
        super().__init__(
            placeholder="Выберите действие...",
            options=options,
            custom_id="application_admin_select"
        )

    async def callback(self, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            error_embed = Embed(
                title="🔒 Доступ запрещен",
                description="Доступно только администраторам!",
                color=0xED4245
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        choice = self.values[0]
        
        if choice == "toggle_status":
            await self.toggle_applications_status(interaction)
        elif choice == "configure_form":
            try: await interaction.message.edit(view=ApplicationAdminView())
            except: pass
            await self.show_form_configuration(interaction)
        elif choice == "view_form":
            try: await interaction.message.edit(view=ApplicationAdminView())
            except: pass
            await self.view_current_form(interaction)
        elif choice == "delete_field":
            try: await interaction.message.edit(view=ApplicationAdminView())
            except: pass
            await self.delete_specific_field(interaction)
        elif choice == "reset_form":
            try: await interaction.message.edit(view=ApplicationAdminView())
            except: pass
            await self.reset_to_default(interaction)

    async def toggle_applications_status(self, interaction: Interaction):
        current_status = get_applications_status()
        new_status = not current_status
        set_applications_status(new_status)
        
        status_text = "ОТКРЫТ" if new_status else "ЗАКРЫТ"
        color = 0x3BA55D if new_status else 0xED4245
        
        # 1. Отправляем уведомление админу
        embed = Embed(
            title="✅ Статус набора изменен" if new_status else "⛔ Статус набора изменен",
            description=f"Прием заявок теперь **{status_text}**.",
            color=color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # 2. Обновляем админ-меню (чтобы сменилась кнопка вкл/выкл)
        try:
            await interaction.message.edit(view=ApplicationAdminView())
        except:
            pass
        
        # 3. Обновляем ПУБЛИЧНОЕ сообщение (делаем кнопку неактивной/активной)
        # Импортируем View здесь, чтобы избежать циклических импортов
        from .submit_button import ApplicationChannelView
        
        try:
            channel = interaction.guild.get_channel(APPLICATION_CHANNEL_ID)
            if channel:
                # Ищем последнее сообщение бота в канале заявок
                async for msg in channel.history(limit=5):
                    if msg.author == interaction.guild.me and msg.embeds:
                        # Обновляем View с новым статусом
                        await msg.edit(view=ApplicationChannelView(interaction.bot))
                        break
                
                # Если ОТКРЫЛИ набор - тегаем everyone
                if new_status:
                    try:
                        await channel.send(
                            content="@everyone", 
                            embed=Embed(
                                title="📢 Набор открыт!",
                                description="Прием заявок в семью снова открыт. Ждем ваших анкет!",
                                color=0x3BA55D
                            ),
                            delete_after=300 # Удалить через 5 минут, чтобы не спамить
                        )
                    except: pass
        except Exception as e:
            print(f"[ERROR] Не удалось обновить публичное сообщение: {e}")

    async def show_form_configuration(self, interaction: Interaction):
        current_form = get_application_form()
        current_form = migrate_old_form_data(current_form)
        save_application_form(current_form)
        
        if len(current_form) == 0:
            view = View(timeout=300)
            add_button = Button(label="Создать первый вопрос", style=ButtonStyle.success, custom_id="add_field")
            
            async def add_callback(inter: Interaction):
                await inter.response.send_message(embed=Embed(title="Тип вопроса", description="Выберите тип:", color=0x5865F2), view=FieldTypeSelectView(), ephemeral=True)
            
            add_button.callback = add_callback
            view.add_item(add_button)
            
            await interaction.response.send_message(embed=Embed(title="Настройка формы", description="Анкета пуста.", color=0x5865F2), view=view, ephemeral=True)
            return
        
        view = View(timeout=300)
        
        edit_options = []
        for i, field in enumerate(current_form):
            edit_options.append(
                SelectOption(
                    label=f"{i+1}. {field['label'][:50]}",
                    value=str(i),
                    description="Нажмите, чтобы изменить"
                )
            )
        
        edit_select = StringSelect(
            placeholder="Выберите вопрос для изменения...",
            options=edit_options,
            custom_id="edit_field_select"
        )
        
        async def edit_select_callback(inter: Interaction):
            idx = int(inter.data["values"][0])
            field = current_form[idx]
            await inter.response.send_modal(TextFieldEditorModal(field_index=idx, existing_field=field, style=field.get("style", "short")))
        
        edit_select.callback = edit_select_callback
        view.add_item(edit_select)
        
        add_button = Button(label="Добавить новый вопрос", style=ButtonStyle.success, custom_id="add_field")
        
        async def add_callback(inter: Interaction):
            await inter.response.send_message(embed=Embed(title="Тип вопроса", description="Выберите тип:", color=0x5865F2), view=FieldTypeSelectView(), ephemeral=True)
        
        add_button.callback = add_callback
        view.add_item(add_button)
        
        fields_desc = []
        for i, field in enumerate(current_form, 1):
            req_mark = "✅" if field["required"] else "❌"
            type_mark = "Короткий" if field.get("style") == "short" else "Длинный"
            fields_desc.append(f"**{i}. {field['label']}**\n└ {type_mark} | Обязательно: {req_mark}")
        
        embed = Embed(
            title="⚙️ Конструктор анкеты",
            description="\n\n".join(fields_desc) if fields_desc else "Нет вопросов",
            color=0x5865F2
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def view_current_form(self, interaction: Interaction):
        current_form = get_application_form()
        
        if not current_form:
            error_embed = Embed(
                title="❌ Форма пуста",
                description="Анкета не содержит вопросов.",
                color=0xED4245
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
            
        embed = Embed(title="📋 Предпросмотр анкеты", color=0x5865F2)
        for i, field in enumerate(current_form, 1):
            embed.add_field(name=f"{i}. {field['label']}", value=f"Подсказка: {field.get('placeholder', '-')}", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def delete_specific_field(self, interaction: Interaction):
        current_form = get_application_form()
        if not current_form:
            error_embed = Embed(
                title="❌ Нечего удалять",
                description="Анкета не содержит вопросов.",
                color=0xED4245
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        await interaction.response.send_message(
            embed=Embed(title="Удаление вопроса", description="Выберите вопрос для удаления:", color=0xFF5555),
            view=FieldDeleteSelectView(),
            ephemeral=True
        )

    async def reset_to_default(self, interaction: Interaction):
        from database import get_default_application_form
        save_application_form(get_default_application_form())
        
        success_embed = Embed(
            title="🔄 Анкета сброшена",
            description="Анкета сброшена к стандартным настройкам.",
            color=0x3BA55D
        )
        await interaction.response.send_message(embed=success_embed, ephemeral=True)

class ApplicationAdminView(View):
    """Главный View админ-панели"""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationAdminSelect())
