import os
import disnake
from disnake.ext import commands
from disnake import Intents
from bottoken import TOKEN


intents = Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True # Важно для работы с участниками!


bot = commands.Bot(command_prefix="!", intents=intents)


# Глобальный кэш для отслеживания созданных каналов
bot.created_channels_cache = {}


@bot.event
async def on_ready():
    print(f'✅ {bot.user} успешно запущен!')
    print('=' * 50)


def load_cogs():
    """Загрузка всех когов из папки cogs (включая подпапки-пакеты)"""
    cogs_path = './cogs'
    
    # Список файлов, которые НЕ нужно загружать как коги
    ignored_files = ['portfolio.py', 'vacation.py', 'verification.py', 'utils.py', 'constants.py', 'database.py']

    for item in os.listdir(cogs_path):
        item_path = os.path.join(cogs_path, item)
        
        # 1. Если это файл .py
        if os.path.isfile(item_path) and item.endswith('.py') and not item.startswith('_'):
            if item in ignored_files:  # <--- ДОБАВЛЕНА ПРОВЕРКА
                continue

            cog_name = item[:-3]
            try:
                bot.load_extension(f'cogs.{cog_name}')
                print(f'✅ Загружен ког (файл): {cog_name}')
            except Exception as e:
                print(f'❌ Ошибка загрузки {cog_name}: {e}')
                
        # 2. Если это папка (пакет) (например cogs/applications/)
        elif os.path.isdir(item_path) and not item.startswith('_') and not item.startswith('.'):
            # Проверяем наличие __init__.py внутри папки
            if os.path.exists(os.path.join(item_path, '__init__.py')):
                try:
                    bot.load_extension(f'cogs.{item}')
                    print(f'✅ Загружен ког (пакет): {item}')
                except Exception as e:
                    print(f'❌ Ошибка загрузки пакета {item}: {e}')


if __name__ == "__main__":
    load_cogs()
    bot.run(TOKEN)
