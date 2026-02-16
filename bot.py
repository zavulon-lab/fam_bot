import os
import disnake
from disnake.ext import commands
from disnake import Intents
from bottoken import TOKEN

# Настройка интентов (прав бота на получение событий)
intents = Intents.default()
intents.message_content = True # Читать сообщения (для анти-спама и команд)
intents.guilds = True          # Работа с серверами
intents.members = True         # Отслеживание входа/выхода участников
intents.moderation = True      # ВАЖНО: Для работы Аудит-лога (защиты), банов и киков
intents.bans = True            # Отслеживание банов
intents.voice_states = True    # Отслеживание голоса

bot = commands.Bot(command_prefix="!", intents=intents)

# Глобальный кэш
bot.created_channels_cache = {}

@bot.event
async def on_ready():
    print(f'{bot.user} успешно запущен!')
    print(f'ID: {bot.user.id}')
    print('=' * 50)

def load_cogs():
    """Загрузка всех когов"""
    cogs_path = './cogs'
    
    # Файлы, которые НЕ являются когами
    ignored_files = ['utils.py', 'constants.py', 'database.py', 'config.py', '__init__.py']

    if not os.path.exists(cogs_path):
        print(f"Папка {cogs_path} не найдена!")
        return

    for item in os.listdir(cogs_path):
        item_path = os.path.join(cogs_path, item)
        
        if os.path.isfile(item_path) and item.endswith('.py') and not item.startswith('_'):
            if item in ignored_files:
                continue

            cog_name = item[:-3]
            try:
                full_cog_name = f'cogs.{cog_name}'
                if full_cog_name in bot.extensions:
                    bot.reload_extension(full_cog_name)
                    print(f'Перезагружен ког (файл): {cog_name}')
                else:
                    bot.load_extension(full_cog_name)
                    print(f'Загружен ког (файл): {cog_name}')
            except Exception as e:
                print(f'Ошибка загрузки {cog_name}: {e}')
                # Выводим полный текст ошибки для отладки
                import traceback
                traceback.print_exc()
                
        elif os.path.isdir(item_path) and not item.startswith('_') and not item.startswith('.'):
            if os.path.exists(os.path.join(item_path, '__init__.py')):
                try:
                    full_cog_name = f'cogs.{item}'
                    if full_cog_name in bot.extensions:
                        bot.reload_extension(full_cog_name)
                        print(f'Перезагружен ког (пакет): {item}')
                    else:
                        bot.load_extension(full_cog_name)
                        print(f'Загружен ког (пакет): {item}')
                except Exception as e:
                    print(f'Ошибка загрузки пакета {item}: {e}')
                    import traceback
                    traceback.print_exc()

if __name__ == "__main__":
    load_cogs()
    bot.run(TOKEN)
