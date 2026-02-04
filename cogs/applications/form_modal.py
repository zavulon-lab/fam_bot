import disnake
from disnake.ui import Modal, TextInput
from disnake import TextInputStyle, Embed, Interaction
from datetime import datetime
from constants import APPLICATIONS_REVIEW_CHANNEL_ID, STAFF_ROLE_ID
from disnake.errors import Forbidden

from .review_view import ApplicationReviewView 


class CompleteApplicationModal(Modal):
    """Модальное окно со ВСЕМИ полями формы (максимум 5)"""
    def __init__(self, bot, form_config: list, message_to_reset: disnake.Message = None):
        self.bot = bot
        self.form_config = form_config
        self.message_to_reset = message_to_reset
        
        components = []
        
        for field in form_config[:5]:
            style_map = {
                "short": TextInputStyle.short,
                "paragraph": TextInputStyle.paragraph
            }
            
            if field.get("type") == "select_menu":
                options_text = " / ".join([opt["label"] for opt in field.get("options", [])[:5]])
                placeholder_text = f"Варианты: {options_text}"
                input_style = TextInputStyle.short
            else:
                placeholder_text = field.get("placeholder", "")
                input_style = style_map.get(field.get("style", "short"), TextInputStyle.short)
            
            text_input = TextInput(
                label=field["label"][:45],
                custom_id=field["custom_id"],
                style=input_style,
                required=field["required"],
                placeholder=placeholder_text[:100],
                min_length=field.get("min_length"),
                max_length=field.get("max_length") if field.get("type") == "text_input" else 200
            )
            components.append(text_input)
        
        super().__init__(
            title="Форма заявки",
            components=components,
            timeout=600
        )
    
    async def callback(self, interaction: Interaction):
        # 1. Сначала откладываем ответ (defer), так как обработка может занять время
        await interaction.response.defer(ephemeral=True)

        # 2. СБРОС МЕНЮ (Reset Select Menu)
        if self.message_to_reset:
            try:
                # Импортируем здесь, чтобы избежать циклического импорта
                from .submit_button import ApplicationChannelView
                # Обновляем сообщение с новым (чистым) View
                await self.message_to_reset.edit(view=ApplicationChannelView(self.bot))
            except Exception as e:
                print(f"[Warning] Не удалось сбросить меню выбора заявок: {e}")

        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send(embed=Embed(title="❌ Ошибка", description="Сервер не найден!", color=0xED4245), ephemeral=True)
                return

            review_channel = guild.get_channel(APPLICATIONS_REVIEW_CHANNEL_ID)
            if not review_channel:
                await interaction.followup.send(embed=Embed(title="❌ Ошибка конфигурации", description="Канал для заявок не найден.", color=0xED4245), ephemeral=True)
                return

            form_data = {}
            for field in self.form_config[:5]:
                form_data[field["custom_id"]] = interaction.text_values.get(field["custom_id"], "Не указано")

            embed = Embed(
                title="✦ Новая заявка на вступление в семью",
                description=(
                    "Спасибо, что решили присоединиться к нам ❤️\n"
                    "Администрация рассмотрит вашу заявку в ближайшее время.\n"
                    "──────────────────────────────"
                ),
                color=0x2B2D31,
                timestamp=datetime.now(),
            )
            
            icon_map = {
                "ник": "🏷️", "имя": "🏷️", "возраст": "🔞",
                "опыт": "⚔️", "стрельба": "🔫", "откаты": "🎥",
                "цель": "🎯", "почему": "❓", "узнал": "📢",
                "семьи": "🏰", "статик": "🆔"
            }

            for field in self.form_config[:5]:
                label_lower = field["label"].lower()
                icon = "📝"
                for key, val in icon_map.items():
                    if key in label_lower:
                        icon = val
                        break
                
                embed.add_field(
                    name=f"{icon} {field['label']}",
                    value=f"```{form_data.get(field['custom_id'], 'Не указано')}```",
                    inline=False
                )

            created_at = interaction.user.created_at.replace(tzinfo=None)
            now = datetime.now()
            delta = now - created_at
            years = delta.days // 365
            days = delta.days % 365
            
            account_age_str = f"{years} лет" if years > 0 else f"{days} дней"

            embed.add_field(name="👤 Пользователь", value=interaction.user.mention, inline=True)
            embed.add_field(name="🆔 ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="📅 Аккаунт создан", value=f"{account_age_str} назад", inline=True)

            embed.set_footer(text=f"Семья • Заявка на вступление • {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            staff_role = guild.get_role(STAFF_ROLE_ID)
            mention = staff_role.mention if staff_role else ""

            await review_channel.send(content=mention, embed=embed, view=ApplicationReviewView())

            confirm_embed = Embed(
                title="✅ Заявка успешно отправлена!",
                description=(
                    "Ваша заявка отправлена администрации.\n"
                    "Ожидайте дальнейших действий."
                ),
                color=0x3BA55D
            )
            
            # Используем followup, так как response.defer уже был вызван
            await interaction.followup.send(embed=confirm_embed, ephemeral=True)

            try:
                dm_embed = Embed(
                    title="✅ Ваша заявка отправлена!",
                    description=(
                        "Ожидайте дальнейших действий от администрации.\n"
                        "Мы свяжемся с вами в ближайшее время."
                    ),
                    color=0x3BA55D
                )
                dm_embed.set_footer(text=f"Семья • {datetime.now().strftime('%d.%m.%Y %H:%M')}")
                await interaction.user.send(embed=dm_embed)
            except Forbidden:
                pass

        except Exception as e:
            print(f"[ERROR] Ошибка в CompleteApplicationModal: {e}")
            import traceback
            traceback.print_exc()
            
            await interaction.followup.send(embed=Embed(title="❌ Ошибка", description="Произошла ошибка при отправке заявки.", color=0xFF0000), ephemeral=True)
