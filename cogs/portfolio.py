import disnake
from disnake.ext import commands
from disnake import Embed, Interaction, TextInputStyle, ButtonStyle, PermissionOverwrite
from disnake.ui import View, Button, button, TextInput, Modal
from constants import CATEGORY_ID, PRIVATE_THREAD_ROLE_ID
from database import get_private_channel, set_private_channel


async def get_target_category(guild: disnake.Guild, base_category_id: int):
    base_category = guild.get_channel(base_category_id)
    if not base_category:
        return None

    if len(base_category.channels) < 50:
        return base_category

    base_name = base_category.name
    
    candidate_categories = []
    
    for cat in guild.categories:
        if cat.id == base_category.id:
            continue
            
        if cat.name.startswith(base_name):
            parts = cat.name.split()
            if parts[-1].isdigit():
                candidate_categories.append(cat)
    
    candidate_categories.sort(key=lambda x: int(x.name.split()[-1]))

    for cat in candidate_categories:
        if len(cat.channels) < 50:
            return cat

    
    if not candidate_categories:
        next_num = 2 
    else:
        last_cat = candidate_categories[-1]
        last_num = int(last_cat.name.split()[-1])
        next_num = last_num + 1

    new_name = f"{base_name} {next_num}"
    
    new_category = await guild.create_category(
        name=new_name,
        overwrites=base_category.overwrites,
        position=base_category.position + next_num, 
        reason="Автоматическое создание новой категории (лимит 50 каналов)"
    )
    
    return new_category


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

        # Проверка БД
        existing_channel_id = get_private_channel(str(user.id))
        if existing_channel_id:
            chan = guild.get_channel(existing_channel_id)
            if chan:
                await interaction.followup.send(
                    f"У вас уже есть портфель: {chan.mention}", 
                    ephemeral=True
                )
                return

        try:
            target_category = await get_target_category(guild, CATEGORY_ID)
            
            if not target_category:
                await interaction.followup.send("Ошибка: Базовая категория не найдена в конфиге.", ephemeral=True)
                return

            safe_name = nickname.strip().lower().replace(" ", "-")
            
            overwrites = {
                guild.default_role: PermissionOverwrite(view_channel=False),
                user: PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
                guild.me: PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }
            
            checker_role = guild.get_role(PRIVATE_THREAD_ROLE_ID)
            if checker_role:
                overwrites[checker_role] = PermissionOverwrite(view_channel=True, send_messages=True)

            new_channel = await guild.create_text_channel(
                name=safe_name,
                category=target_category,
                overwrites=overwrites,
                topic=f"Владелец: {user.mention} ({user.id})",
                reason=f"Портфель: {nickname}"
            )

            set_private_channel(str(user.id), new_channel.id)
            
            embed_welcome = Embed(
                title=f"<:freeiconcreatefolder12075409:1472663668205555784> Портфель: {nickname}",
                description=f"Владелец: {user.mention}\nКанал создан в категории: **{target_category.name}**",
                color=disnake.Color.from_rgb(54, 57, 63)
            )
            await new_channel.send(content=user.mention, embed=embed_welcome)

            await interaction.followup.send(
                f"Портфель создан: {new_channel.mention}", 
                ephemeral=True
            )

        except Exception as e:
            print(f"[Portfolio Error] {e}")
            await interaction.followup.send(f"Ошибка: {e}", ephemeral=True)


class PortfolioView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Создать личный портфель", style=ButtonStyle.primary, emoji="<:freeiconcreatefolder12075409:1472663668205555784>", custom_id="btn_create_portfolio")
    async def create_portfolio_btn(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(CreatePortfolioModal())


class PortfolioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(PortfolioCog(bot))
