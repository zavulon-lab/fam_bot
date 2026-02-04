import disnake
from disnake import Embed, Interaction, TextInputStyle, SelectOption
from disnake.ui import View, Select, TextInput, Modal
from datetime import datetime
from constants import *
from database import get_private_channel, set_private_channel

class CreatePortfolioModal(Modal):
    def __init__(self, message_to_reset: disnake.Message = None):
        self.message_to_reset = message_to_reset
        components = [TextInput(label="Ваш игровой никнейм", custom_id="game_nickname", style=TextInputStyle.short, required=True, placeholder="Vladislav Cartel", max_length=32)]
        super().__init__(title="Создание личного канала", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        
        if self.message_to_reset:
            try: await self.message_to_reset.edit(view=PortfolioView())
            except: pass

        nickname = interaction.text_values["game_nickname"]
        guild = interaction.guild
        user = interaction.user

        if get_private_channel(str(user.id)):
            existing = guild.get_channel(get_private_channel(str(user.id)))
            if existing:
                await interaction.followup.send(embed=Embed(description=f"⚠️ У вас уже есть личный портфель: {existing.mention}", color=0xFFA500), ephemeral=True)
                return

        try:
            category = guild.get_channel(CATEGORY_ID)
            if not category:
                await interaction.followup.send(embed=Embed(description="❌ Категория не найдена.", color=0xFF0000), ephemeral=True)
                return
            if len(category.channels) >= 50:
                 for cat in guild.categories:
                    if cat.name.startswith(category.name) and len(cat.channels) < 50:
                        category = cat
                        break
            
            new_channel = await guild.create_text_channel(name=nickname.lower().replace(" ", "-"), category=category, reason=f"Портфель для {nickname}")
            await new_channel.set_permissions(guild.default_role, view_channel=False)
            await new_channel.set_permissions(user, view_channel=True, send_messages=True, attach_files=True)
            role = guild.get_role(PRIVATE_THREAD_ROLE_ID)
            if role: await new_channel.set_permissions(role, view_channel=True)
            
            set_private_channel(str(user.id), new_channel.id)
            
            inner_embed = Embed(
                title="📂 Личный портфель",
                description=f"**Владелец:** {user.mention}\n**Игровой ник:** {nickname}\n**Дата создания:** {datetime.now().strftime('%d.%m.%Y')}\n\nСюда вы можете загружать свои откаты и отчеты.",
                color=0x2B2D31
            )
            inner_embed.set_thumbnail(url=user.display_avatar.url)
            await new_channel.send(f"{user.mention}", embed=inner_embed)
            await interaction.followup.send(embed=Embed(description=f"✅ Личный портфель создан: {new_channel.mention}", color=0x3BA55D), ephemeral=True)
        except Exception as e:
            print(f"Error: {e}")
            await interaction.followup.send(embed=Embed(description="❌ Ошибка создания.", color=0xFF0000), ephemeral=True)

class PortfolioSelect(Select):
    def __init__(self):
        options = [SelectOption(label="Создание личного портфеля", value="create_portfolio", description="Нажмите для создания канала", emoji="📹")]
        super().__init__(placeholder="Получение Tier роли", min_values=1, max_values=1, options=options, custom_id="portfolio_select")
    async def callback(self, interaction: Interaction):
        if self.values[0] == "create_portfolio":
             await interaction.response.send_modal(CreatePortfolioModal(interaction.message))

class PortfolioView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PortfolioSelect())
