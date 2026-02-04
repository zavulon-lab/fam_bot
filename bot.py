import os
import disnake
from disnake.ext import commands
from disnake import Intents
from bottoken import TOKEN

intents = Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# Глобальный кэш
bot.created_channels_cache = {}

@bot.event
async def on_ready():
    print(f'✅ {bot.user} успешно запущен!')
    print('=' * 50)

def load_cogs():
    """Загрузка всех когов"""
    cogs_path = './cogs'
    
    # Убрали portfolio.py, vacation.py, verification.py из игнора
    # Оставили только служебные файлы
    ignored_files = ['utils.py', 'constants.py', 'database.py', '__init__.py']

    for item in os.listdir(cogs_path):
        item_path = os.path.join(cogs_path, item)
        
        if os.path.isfile(item_path) and item.endswith('.py') and not item.startswith('_'):
            if item in ignored_files:
                continue

            cog_name = item[:-3]
            try:
                bot.load_extension(f'cogs.{cog_name}')
                print(f'✅ Загружен ког (файл): {cog_name}')
            except Exception as e:
                print(f'❌ Ошибка загрузки {cog_name}: {e}')
                
        elif os.path.isdir(item_path) and not item.startswith('_') and not item.startswith('.'):
            if os.path.exists(os.path.join(item_path, '__init__.py')):
                try:
                    bot.load_extension(f'cogs.{item}')
                    print(f'✅ Загружен ког (пакет): {item}')
                except Exception as e:
                    print(f'❌ Ошибка загрузки пакета {item}: {e}')

if __name__ == "__main__":
    load_cogs()
    bot.run(TOKEN)
