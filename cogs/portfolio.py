import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, TextInputStyle, ButtonStyle
from disnake.ui import View, Button, button, TextInput, Modal
from datetime import datetime
from constants import *
from database import get_private_channel, set_private_channel

# === 1. МОДАЛКА (ФОРМА) ===
class CreatePortfolioModal(Modal):
    def __init__(self):
        components = [
            TextInput(
                label="Ваш игровой никнейм", 
                custom_id="game_nickname", 
                style=TextInputStyle.short, 
                required=True, 
                placeholder="Alexis Superior", 
                max_length=32
            )
        ]
        super().__init__(title="Создание личного канала", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        
        nickname = interaction.text_values["game_nickname"]
        guild = interaction.guild
        user = interaction.user

        # 1. Проверка наличия канала в БД
        existing_id = get_private_channel(str(user.id))
        if existing_id:
            existing_channel = guild.get_channel(existing_id)
            if existing_channel:
                await interaction.followup.send(
                    embed=Embed(description=f"⚠️ У вас уже есть личный портфель: {existing_channel.mention}", color=0xFFA500), 
                    ephemeral=True
                )
                return
            # Если в БД есть, а канала нет (удален ручками) — код пойдет дальше и создаст новый.

        # 2. Поиск категории
        try:
            category = guild.get_channel(CATEGORY_ID)
            if not category:
                await interaction.followup.send(embed=Embed(description="❌ Категория для портфелей не найдена.", color=0xFF0000), ephemeral=True)
                return
            
            # Если категория переполнена (50 каналов), ищем следующую или создаем
            if len(category.channels) >= 50:
                 # Простой поиск соседней категории с тем же названием
                 found_next = False
                 for cat in guild.categories:
                    if cat.name.startswith(category.name) and len(cat.channels) < 50:
                        category = cat
                        found_next = True
                        break
                 # Если не нашли — можно было бы создать новую, но пока просто ошибку или используем последнюю
            
            # 3. Создание канала
            new_channel = await guild.create_text_channel(
                name=nickname.lower().replace(" ", "-"), 
                category=category, 
                reason=f"Портфель для {nickname}"
            )
            
            # 4. Настройка прав
            # Everyone - не видит
            await new_channel.set_permissions(guild.default_role, view_channel=False)
            # Владелец - видит, пишет, кидает файлы
            await new_channel.set_permissions(user, view_channel=True, send_messages=True, attach_files=True)
            
            # Роль проверяющих (PRIVATE_THREAD_ROLE_ID) - видит
            role_checker = guild.get_role(PRIVATE_THREAD_ROLE_ID)
            if role_checker: 
                await new_channel.set_permissions(role_checker, view_channel=True)
            
            # 5. Сохранение в БД
            set_private_channel(str(user.id), new_channel.id)
            
            await interaction.followup.send(
                embed=Embed(description=f"✅ Ваш личный канал создан: {new_channel.mention}", color=0x3BA55D), 
                ephemeral=True
            )
            
        except Exception as e:
            print(f"[Portfolio] Error: {e}")
            await interaction.followup.send(embed=Embed(description="❌ Произошла ошибка при создании канала.", color=0xFF0000), ephemeral=True)


# === 2. VIEW С КНОПКОЙ (Вместо селекта) ===
class PortfolioView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Создать личный портфель", style=ButtonStyle.primary, emoji="📁", custom_id="btn_create_portfolio")
    async def create_portfolio_btn(self, button: Button, interaction: Interaction):
        # Просто открываем модалку. Никаких сбросов селектов не нужно, так как это кнопка.
        await interaction.response.send_modal(CreatePortfolioModal())


# === 3. COG ===
class PortfolioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(PortfolioCog(bot))
