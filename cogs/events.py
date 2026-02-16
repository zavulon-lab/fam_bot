import disnake
from disnake.ext import commands
from disnake.ui import Modal, TextInput, View, Button, Select
from disnake import Interaction, ButtonStyle, Color, Embed
import sqlite3
import json
import uuid
import time
import re
from pathlib import Path
import asyncio
import sys
import os
from datetime import datetime

# --- КОНФИГУРАЦИЯ И ИМПОРТЫ ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from constants import (
        EVENTS_CHANNEL_ID, EVENTS_ADMIN_CHANNEL_ID,
        LOG_ADMIN_ACTIONS_ID, LOG_EVENT_HISTORY_ID, LOG_USER_ACTIONS_ID
    )
    try: from constants import EVENT_VOICE_CHANNEL_ID 
    except: EVENT_VOICE_CHANNEL_ID = 1469489179766292755
    try: from constants import EVENTS_TAG_CHANNEL_ID 
    except: EVENTS_TAG_CHANNEL_ID = 1469491042679128164
    try: from constants import EVENTS_PRIORITY_ROLE_ID
    except: EVENTS_PRIORITY_ROLE_ID = 123456789012345678
    
    VOD_SUBMIT_CHANNEL_ID = 1472985007403307191 
    
except ImportError:
    EVENTS_CHANNEL_ID = 0
    EVENTS_ADMIN_CHANNEL_ID = 0
    LOG_ADMIN_ACTIONS_ID = 0
    LOG_EVENT_HISTORY_ID = 0
    LOG_USER_ACTIONS_ID = 0
    EVENT_VOICE_CHANNEL_ID = 1469489179766292755
    EVENTS_TAG_CHANNEL_ID = 1469491042679128164
    EVENTS_PRIORITY_ROLE_ID = 123456789012345678
    VOD_SUBMIT_CHANNEL_ID = 1472985007403307191

DB_PATH = Path("events.db")
AUX_COLOR = disnake.Color.from_rgb(54, 57, 63)

# ===== КАСТОМНЫЕ ЭМОДЗИ =====
# Формат: "<:emoji_name:emoji_id>" или "<a:emoji_name:emoji_id>" для анимированных
# Получить ID: Discord Dev Portal → Emoji → скопировать ID

# Админ-панель (MainAdminView)
EMOJI_DICE = "<:freeiconstart1768113:1472677948036350023>"              # Начать регистрацию
EMOJI_TRASH = "<:freeicongameover3475329:1472678254409285776>"             # Завершить и очистить
EMOJI_PLUS = "<:freeiconplus1828819:1472681225935392858>"              # Внести в основной список
EMOJI_MINUS = "<:freeiconminus10263924:1472681399512334409>"             # Перевести в резервный список
EMOJI_MIC = "🎙️"              # Проверка голосового канала
EMOJI_CHAT = "💬"              # Тегнуть основной список
EMOJI_MEGAPHONE = "<:freeiconmegaphone716224:1472678446454014046>"         # Пингануть everyone
EMOJI_GEAR = "<:freeicongear889744:1472678585277092084>"              # Меню управления

# Публичная панель (EventUserView)
EMOJI_JOIN = "<:freeiconplus1828819:1472681225935392858>"              # Записаться
EMOJI_LEAVE = "<:freeiconminus10263924:1472681399512334409>"             # Покинуть список

# Меню управления (OtherOptionsView) - Select Options
EMOJI_STAR = "<:freeiconstar7408613:1472654730902765678>"              # White List
EMOJI_INBOX = "<:freeiconfile3286303:1472678951599083603>"             # WL → Основа
EMOJI_PLUS_CIRCLE = "<:freeiconplus1828819:1472681225935392858>"       # Внести в резерв
EMOJI_SETTINGS = "<:freeiconedit1040228:1472654696891158549>"          # Редактировать Embed
EMOJI_PAUSE = "<:freeiconstop394592:1472679253177925808>"             # Пауза
EMOJI_RESUME = "<:freeiconpowerbutton4943421:1472679504714666056>"            # Старт
EMOJI_DOOR = "<:freeiconbroom2954880:1472654679128145981>"              # Кик
EMOJI_CAMERA = "<:freeiconyoutube1384060:1472661242941411458>"            # Запрос откатов

# Меню управления - кнопки внутри (динамические View)
EMOJI_PLUS_BTN = "<:freeiconplus1828819:1472681225935392858>"          # Добавить ID (WL)
EMOJI_MINUS_BTN = "<:freeiconminus10263924:1472681399512334409>"         # Удалить ID (WL)
EMOJI_EYE = "<:freeiconeye8050820:1472679869992407257>"              # Показать WL
EMOJI_BIN = "<:freeicondelete1214428:1472680867284385854>"              # Очистить весь WL
EMOJI_CHECK = "<:tik:1472654073814581268>"             # Выполнить (WL Mass Add)
EMOJI_PENCIL = "<:freeiconedit1040228:1472654696891158549>"            # Редактировать (Edit)
EMOJI_PLAY = "<:freeiconpowerbutton4943421:1472679504714666056>"              # Возобновить регистрацию (Resume)
EMOJI_PAUSE_BTN = "<:freeiconstop394592:1472679253177925808>"         # Остановить регистрацию (Pause)
EMOJI_DOOR_BTN = "<:freeiconbroom2954880:1472654679128145981>"          # Удалить участника (Kick)
EMOJI_CAMERA_BTN = "<:freeiconyoutube1384060:1472661242941411458>"        # Отправить запрос (VODs)

# Закрыть меню
EMOJI_CROSS = "<:cross:1472654174788255996>"             # Закрыть

# --- РАБОТА С БАЗОЙ ДАННЫХ ---

def init_events_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            name TEXT,
            organizer TEXT,
            event_time TEXT,
            description TEXT,
            image_url TEXT,
            max_slots INTEGER,
            status TEXT,
            message_id INTEGER,
            admin_message_id INTEGER,
            channel_id INTEGER,
            participants TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS global_whitelist (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def get_global_whitelist():
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM global_whitelist")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_to_global_whitelist(user_ids):
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for uid in user_ids:
        try: cursor.execute("INSERT OR IGNORE INTO global_whitelist (user_id) VALUES (?)", (uid,))
        except: pass
    conn.commit()
    conn.close()

def remove_from_global_whitelist(user_ids):
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for uid in user_ids:
        cursor.execute("DELETE FROM global_whitelist WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()

def clear_global_whitelist():
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM global_whitelist")
    conn.commit()
    conn.close()

def get_current_event():
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE status IN ("active", "draft", "paused") ORDER BY created_at DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_event_by_id(event_id):
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_event(data):
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    parts_data = data.get("participants", {"main": [], "reserve": []})
    parts_json = json.dumps(parts_data) if not isinstance(parts_data, str) else parts_data
    cursor.execute('''
        INSERT OR REPLACE INTO events 
        (id, name, organizer, event_time, description, image_url, max_slots, status, message_id, admin_message_id, channel_id, participants)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data["id"], data["name"], data["organizer"], data["event_time"], 
        data["description"], data.get("image_url"), data["max_slots"], 
        data["status"], data.get("message_id"), data.get("admin_message_id"), 
        data.get("channel_id"), parts_json
    ))
    conn.commit()
    conn.close()

def close_all_active_events():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE events SET status = "closed" WHERE status IN ("active", "draft", "paused")')
    conn.commit()
    conn.close()

def get_participants_struct(data):
    val = data.get("participants")
    default = {"main": [], "reserve": []}
    if not val: return default
    parsed = val
    if isinstance(val, str):
        try: parsed = json.loads(val)
        except: return default
    if isinstance(parsed, list): return {"main": [], "reserve": parsed}
    return parsed

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def extract_ids(text):
    ids = re.findall(r'<@!?(\d+)>|(\d{17,20})', text)
    result = []
    for match in ids:
        uid = match[0] if match[0] else match[1]
        if uid: result.append(int(uid))
    return list(set(result))

def push_to_reserve_if_full(struct, max_slots):
    """Переносит лишних из основы в резерв."""
    if len(struct["main"]) <= max_slots:
        return struct
    while len(struct["main"]) > max_slots:
        overflow_user = struct["main"].pop(-1)
        struct["reserve"].insert(0, overflow_user)
    return struct

# --- СИСТЕМА ЛОГИРОВАНИЯ ---

async def send_log(bot, channel_id, title, description, color=0x2B2D31, user=None):
    """Универсальная отправка лога."""
    if not channel_id: return
    channel = bot.get_channel(channel_id)
    if not channel: return
    embed = Embed(title=title, description=description, color=color, timestamp=datetime.now())
    if user:
        embed.set_footer(text=f"Выполнил: {user.display_name}", icon_url=user.display_avatar.url)
    try: await channel.send(embed=embed)
    except: pass

async def log_admin_action(bot, action_name, details, user):
    await send_log(bot, LOG_ADMIN_ACTIONS_ID, f"<:freeicontoolbox4873901:1472933974094647449> Админ-действие: {action_name}", details, disnake.Color.from_rgb(54, 57, 63), user)

async def log_user_action(bot, action_name, details, user, is_negative=False):
    col = Color.red() if is_negative else Color.green()
    await send_log(bot, LOG_USER_ACTIONS_ID, f"<:freeiconteam2763403:1472654736489451581> Участники: {action_name}", details, col, user)

async def log_event_history(bot, event_data):
    """Отправляет финальный отчет о закрытом ивенте."""
    if not LOG_EVENT_HISTORY_ID: return
    channel = bot.get_channel(LOG_EVENT_HISTORY_ID)
    if not channel: return
    
    struct = get_participants_struct(event_data)
    main_txt = "\n".join([f"{i+1}. <@{p['user_id']}>" for i, p in enumerate(struct['main'])]) or "Пусто"
    res_txt = "\n".join([f"{i+1}. <@{p['user_id']}>" for i, p in enumerate(struct['reserve'])]) or "Пусто"
    
    embed = Embed(title=f"<:freeiconstop394592:1472679253177925808> Ивент завершен: {event_data['name']}", color=0x2B2D31, timestamp=datetime.now())
    embed.add_field(name="Инфо", value=f"Орг: {event_data['organizer']}\nВремя: {event_data['event_time']}", inline=False)
    
    if len(main_txt) > 1000: main_txt = main_txt[:950] + "\n..."
    if len(res_txt) > 1000: res_txt = res_txt[:950] + "\n..."
    
    embed.add_field(name=f"Основа ({len(struct['main'])})", value=main_txt, inline=False)
    embed.add_field(name=f"Резерв ({len(struct['reserve'])})", value=res_txt, inline=False)
    
    try: await channel.send(embed=embed)
    except: pass

# --- ГЕНЕРАЦИЯ ЭМБЕДОВ ---

def generate_admin_embeds(data=None, bot=None): # <-- Добавлен bot
    """Возвращает СПИСОК с одним эмбедом, содержащим и основу, и резерв"""
    
    embed = Embed(color=0x2B2D31)
    
    # Пытаемся получить иконку бота, если передан bot
    icon_url = None
    if bot:
        icon_url = bot.user.display_avatar.url
    
    if not data:
        embed.description = "**Регистрация:** не активна"
        if icon_url: embed.set_footer(text="Calogero Famq", icon_url=icon_url) # <-- Используем тут
        else: embed.set_footer(text="Calogero Famq")
        return [embed]

    struct = get_participants_struct(data)
    main_list = struct["main"]
    reserve_list = struct["reserve"]
    max_slots = data["max_slots"]
    
    if data["status"] == "paused": status_text = "ПАУЗА <:freeiconstop394592:1472679253177925808>"
    elif data["status"] == "draft": status_text = "приостановлена"
    else: status_text = "доступна <:tik:1472654073814581268> "
    
    desc_text = (
        f"**Мероприятие:** {data['name']}\n"
        f"**Регистрация:** {status_text}\n\n"
        f"> **Время:** {data['event_time']}\n"
        f"> **Примечание:** {data['description']}\n"
    )
    embed.description = desc_text
    
    embed.add_field(
        name=f"**Зарегистрированные участники: {len(main_list) + len(reserve_list)}**",
        value=f"**Основной состав ({len(main_list)}/{max_slots}):**",
        inline=False
    )
    
    # Генерация колонок ОСНОВЫ
    USERS_PER_COLUMN = 20
    all_lines = [f"{i+1}) <@{p['user_id']}>" for i, p in enumerate(main_list)]
    chunks = [all_lines[i:i + USERS_PER_COLUMN] for i in range(0, len(all_lines), USERS_PER_COLUMN)]
    
    if not chunks:
        embed.add_field(name="⠀", value="*Список пуст*", inline=False)
    else:
        for i, chunk in enumerate(chunks):
            if i >= 6:
                embed.add_field(name="...", value=f"... еще {len(main_list) - (i*USERS_PER_COLUMN)} ...", inline=False)
                break
            embed.add_field(name="⠀", value="\n".join(chunk), inline=True)

    # ЗАГОЛОВОК РЕЗЕРВА (сразу после основы, без разрыва)
    embed.add_field(
        name="⠀",
        value=f"**Резервный список ({len(reserve_list)}):**",
        inline=False
    )
    
    # Генерация колонок РЕЗЕРВА
    if reserve_list:
        res_lines = [f"{i+1}) <@{p['user_id']}>" for i, p in enumerate(reserve_list)]
        res_chunks = [res_lines[i:i + USERS_PER_COLUMN] for i in range(0, len(res_lines), USERS_PER_COLUMN)]
        
        for i, chunk in enumerate(res_chunks):
            if i >= 6:
                embed.add_field(name="...", value="... (список слишком велик) ...", inline=False)
                break
            embed.add_field(name="⠀", value="\n".join(chunk), inline=True)
    else:
        embed.add_field(name="⠀", value="*Резерв пуст*", inline=False)

    if data.get("image_url"):
        embed.set_image(url=data["image_url"])
    
    # Установка футера
    if icon_url:
        embed.set_footer(text="Calogero Famq", icon_url=icon_url)
    else:
        embed.set_footer(text="Calogero Famq") # Без иконки, если bot не передан

    return [embed]


async def update_all_views(bot, data=None):
    """Обновляет сообщения админки и публичного канала."""
    embeds = generate_admin_embeds(data)
    
    # Админ-канал
    admin_chan = bot.get_channel(EVENTS_ADMIN_CHANNEL_ID)
    if admin_chan:
        target_msg = None
        try:
            async for msg in admin_chan.history(limit=10):
                if msg.author == bot.user and msg.components:
                    try:
                        if msg.components[0].children and msg.components[0].children[0].custom_id == "start_reg_btn":
                            target_msg = msg
                            break
                    except (IndexError, AttributeError): pass
        except Exception:
            pass
        
        if target_msg:
            try:
                await target_msg.edit(embeds=embeds, view=MainAdminView())
            except Exception:
                pass
        else:
            try:
                await admin_chan.send(embeds=embeds, view=MainAdminView())
            except Exception:
                pass

    # Публичный канал
    if data and data.get("message_id"):
        try:
            chan = bot.get_channel(data["channel_id"])
            if chan:
                msg = await chan.fetch_message(data["message_id"])
                await msg.edit(embeds=embeds, view=EventUserView(data["id"]))
        except Exception:
            pass

# --- МОДАЛЬНЫЕ ОКНА ---

class EventCreateModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Название мероприятия", custom_id="name", placeholder="Капт", required=True),
            TextInput(label="Организатор", custom_id="organizer", placeholder="Alexis", required=True),
            TextInput(label="Время", custom_id="time", placeholder="19:00", required=True),
            TextInput(label="Слоты (число)", custom_id="slots", placeholder="20", value="20", required=True),
            TextInput(label="Ссылка на скриншот (необяз.)", custom_id="image", required=False),
        ]
        super().__init__(title="Настройка мероприятия", components=components)

    async def callback(self, interaction: Interaction):
        try: slots = int(interaction.text_values["slots"])
        except: return await interaction.response.send_message("Слоты должны быть числом.", ephemeral=True)
        
        close_all_active_events()
        event_id = str(uuid.uuid4())[:8]
        struct = {"main": [], "reserve": []}
        
        new_event = {
            "id": event_id,
            "name": interaction.text_values["name"],
            "organizer": interaction.text_values["organizer"],
            "event_time": interaction.text_values["time"],
            "description": interaction.text_values["name"], 
            "image_url": interaction.text_values["image"],
            "max_slots": slots,
            "status": "active",
            "participants": struct,
            "channel_id": EVENTS_CHANNEL_ID
        }
        
        pub_chan = interaction.guild.get_channel(EVENTS_CHANNEL_ID)
        if not pub_chan: return await interaction.response.send_message("Нет публичного канала.", ephemeral=True)
        
        embeds = generate_admin_embeds(new_event)
        pub_msg = await pub_chan.send(embeds=embeds, view=EventUserView(event_id))
        new_event["message_id"] = pub_msg.id
        
        save_event(new_event)
        await update_all_views(interaction.bot, new_event)
        await log_admin_action(interaction.bot, "Старт регистрации", f"Ивент: **{new_event['name']}**", interaction.user)
        await interaction.response.send_message("Регистрация запущена!", ephemeral=True)

class SmartManageModal(Modal):
    def __init__(self, mode, event_id, menu_msg=None):
        self.mode = mode
        self.event_id = event_id
        self.menu_msg = menu_msg 
        
        ph, title, label = "", "Управление", "Данные"
        
        if mode == "reserve_to_main":
            title, label, ph = "Из Резерва → В Основу", "Номера из РЕЗЕРВА", "1 2 5"
        elif mode == "main_to_reserve":
            title, label, ph = "Из Основы → В Резерв", "Номера из ОСНОВЫ", "1 5"
        elif mode == "whitelist_add":
            title, label, ph = "Добавить в White List", "ID (через пробел)", "123456789 987654321"
        elif mode == "whitelist_remove":
            title, label, ph = "Удалить из White List", "ID (через пробел)", "123456789"
        elif mode == "manual_reserve_add":
            title, label, ph = "Внести в РЕЗЕРВ (ID)", "ID или теги", " 123456789"
        elif mode == "kick_user":
            title, label, ph = "Удаление участника", "Номер (1) или (р1)", "5"
            
        components = [TextInput(label=label, custom_id="input", placeholder=ph)]
        super().__init__(title=title, components=components)

    async def callback(self, interaction: Interaction):
        if self.menu_msg:
            try: await self.menu_msg.edit(view=OtherOptionsView(self.event_id))
            except: pass
        
        data = get_event_by_id(self.event_id)
        if not data: return
        struct = get_participants_struct(data)
        inp = interaction.text_values["input"]

        # === WL ADD ===
        if self.mode == "whitelist_add":
            ids = extract_ids(inp)
            add_to_global_whitelist(ids)
            await log_admin_action(interaction.bot, "Добавлено в WL", f"ID: {ids}", interaction.user)
            await interaction.response.send_message(f"Добавлено в Global WL: **{len(ids)} чел.**", ephemeral=True)
            return

        # === WL REMOVE ===
        if self.mode == "whitelist_remove":
            ids = extract_ids(inp)
            remove_from_global_whitelist(ids)
            await log_admin_action(interaction.bot, "Удалено из WL", f"ID: {ids}", interaction.user)
            await interaction.response.send_message(f"Удалено из Global WL: **{len(ids)} чел.**", ephemeral=True)
            return

        # === MANUAL RESERVE ===
        if self.mode == "manual_reserve_add":
            ids = extract_ids(inp)
            added = 0
            for uid in ids:
                if not any(p["user_id"] == uid for p in struct["main"] + struct["reserve"]):
                    struct["reserve"].append({"user_id": uid, "join_time": time.time()})
                    added += 1
            data["participants"] = struct
            save_event(data)
            await update_all_views(interaction.bot, data)
            await log_admin_action(interaction.bot, "Ручной ввод (Резерв)", f"Добавлено: **{added}**", interaction.user)
            await interaction.response.send_message(f"Добавлено в резерв: **{added} чел.**", ephemeral=True)
            return

        # === KICK ===
        if self.mode == "kick_user":
            txt = inp.strip().lower()
            is_res = True if (txt.startswith('r') or txt.startswith('р')) else False
            try: idx = int(re.sub(r"\D", "", txt)) - 1
            except: return await interaction.response.send_message("Некорректный номер.", ephemeral=True)
            
            lst = struct["reserve"] if is_res else struct["main"]
            if 0 <= idx < len(lst):
                removed = lst.pop(idx)
                data["participants"] = struct
                save_event(data)
                await update_all_views(interaction.bot, data)
                await log_admin_action(interaction.bot, "Кик участника", f"User: <@{removed['user_id']}>", interaction.user)
                await interaction.response.send_message(f"Кикнут <@{removed['user_id']}>.", ephemeral=True)
            else:
                await interaction.response.send_message("Номер вне диапазона.", ephemeral=True)
            return

        # === МАССОВЫЕ ПЕРЕНОСЫ ===
        try: indices = sorted(list(set([int(x) for x in inp.replace(",", " ").split() if x.isdigit()])))
        except: return await interaction.response.send_message("Ошибка ввода чисел.", ephemeral=True)
        if not indices: return await interaction.response.send_message("Пустой ввод.", ephemeral=True)

        if self.mode == "reserve_to_main":
            moved = []
            valid = [i-1 for i in indices if 0 < i <= len(struct["reserve"])]
            for i in sorted(valid, reverse=True): 
                moved.append(struct["reserve"].pop(i))
            moved.reverse()
            struct["main"].extend(moved)
            struct = push_to_reserve_if_full(struct, data["max_slots"])
            data["participants"] = struct
            save_event(data)
            await update_all_views(interaction.bot, data)
            await log_admin_action(interaction.bot, "Перенос Резерв→Основа", f"Кол-во: **{len(moved)}**", interaction.user)
            await interaction.response.send_message(f"Перемещено: **{len(moved)} чел.**", ephemeral=True)

        elif self.mode == "main_to_reserve":
            moved = []
            valid = [i-1 for i in indices if 0 < i <= len(struct["main"])]
            for i in sorted(valid, reverse=True): 
                moved.append(struct["main"].pop(i))
            moved.reverse()
            for u in reversed(moved): 
                struct["reserve"].insert(0, u)
            data["participants"] = struct
            save_event(data)
            await update_all_views(interaction.bot, data)
            await log_admin_action(interaction.bot, "Перенос Основа→Резерв", f"Кол-во: **{len(moved)}**", interaction.user)
            await interaction.response.send_message(f"Перемещено: **{len(moved)} чел.**", ephemeral=True)

class EditEventModal(Modal):
    def __init__(self, data, menu_msg=None):
        self.event_id = data["id"]
        self.menu_msg = menu_msg
        components = [
            TextInput(label="Название", custom_id="name", value=data["name"], required=True),
            TextInput(label="Время", custom_id="time", value=data["event_time"], required=True),
            TextInput(label="Примечание (Орг)", custom_id="desc", value=data["description"], required=True),
            TextInput(label="URL Картинки", custom_id="image", value=data.get("image_url", ""), required=False),
        ]
        super().__init__(title="Редактировать ивент", components=components)

    async def callback(self, interaction: Interaction):
        if self.menu_msg:
            try: await self.menu_msg.edit(view=OtherOptionsView(self.event_id))
            except: pass
        data = get_event_by_id(self.event_id)
        if not data: return
        data["name"] = interaction.text_values["name"]
        data["event_time"] = interaction.text_values["time"]
        data["description"] = interaction.text_values["desc"]
        data["image_url"] = interaction.text_values["image"]
        save_event(data)
        await update_all_views(interaction.bot, data)
        await log_admin_action(interaction.bot, "Редактирование", "Параметры ивента обновлены", interaction.user)
        await interaction.response.send_message("Ивент обновлен.", ephemeral=True)

# --- VIEWS ---

class OtherOptionsView(View):
    def __init__(self, event_id):
        super().__init__(timeout=None)
        self.event_id = event_id
        
        options = [
            disnake.SelectOption(label="White List", description="Управление списком приоритета", emoji=EMOJI_STAR, value="whitelist"),
            disnake.SelectOption(label="WL → Основа", description="Массовый перенос всех из WL в основу", emoji=EMOJI_INBOX, value="wl_mass_add"),
            disnake.SelectOption(label="Внести в резерв", description="Ручной ввод ID участников", emoji=EMOJI_PLUS_CIRCLE, value="add_reserve"),
            disnake.SelectOption(label="Редактировать Embed", description="Изменить название, время, описание, картинку", emoji=EMOJI_SETTINGS, value="edit"),
            disnake.SelectOption(label="Пауза", description="Остановить регистрацию (временно)", emoji=EMOJI_PAUSE, value="pause"),
            disnake.SelectOption(label="Старт", description="Возобновить регистрацию", emoji=EMOJI_RESUME, value="resume"),
            disnake.SelectOption(label="Кик", description="Удалить участника по номеру", emoji=EMOJI_DOOR, value="kick"),
            disnake.SelectOption(label="Запрос откатов", description="Пингануть участников для отправки отката", emoji=EMOJI_CAMERA, value="vods"),
        ]
        self.add_item(Select(placeholder="Меню управления", options=options, custom_id="other_select"))

    @disnake.ui.button(label="Закрыть", style=ButtonStyle.secondary, emoji=EMOJI_CROSS, row=1)
    async def close_menu(self, button, interaction):
        await interaction.message.delete()

    async def interaction_check(self, interaction: Interaction):
        if interaction.data.get("component_type") == 2: return True 
        
        val = interaction.data['values'][0]
        data = get_event_by_id(self.event_id)
        if not data: return await interaction.response.send_message("Ивент не найден.", ephemeral=True)
        
        # === WHITE LIST ===
        if val == "whitelist":
            embed = Embed(title="<:freeiconstar7408613:1472654730902765678> White List Управление", color=AUX_COLOR)
            wl = get_global_whitelist()
            desc_list = " ".join([f"<@{uid}>" for uid in wl]) if wl else "*Пусто*"
            embed.description = f"**Текущий список:**\n{desc_list}\n\n*White List — участники с приоритетом попадают в основу вне очереди.*"
            
            view = View()
            
            btn_add = Button(label="Добавить ID", style=ButtonStyle.success, emoji=EMOJI_PLUS_BTN)
            btn_add.callback = lambda i: i.response.send_modal(SmartManageModal("whitelist_add", self.event_id, interaction.message))
            
            btn_rem = Button(label="Удалить ID", style=ButtonStyle.danger, emoji=EMOJI_MINUS_BTN)
            btn_rem.callback = lambda i: i.response.send_modal(SmartManageModal("whitelist_remove", self.event_id, interaction.message))
            
            btn_show = Button(label="Показать WL", style=ButtonStyle.primary, emoji=EMOJI_EYE)
            async def show_cb(inter):
                wl_current = get_global_whitelist()
                txt = "\n".join([f"<@{uid}>" for uid in wl_current]) if wl_current else "*Пусто*"
                await inter.response.send_message(f"**<:freeiconrules5692161:1472654721117589606> Global White List:**\n{txt}", ephemeral=True)
            btn_show.callback = show_cb
            
            btn_clear = Button(label="Очистить весь WL", style=ButtonStyle.danger, emoji=EMOJI_BIN)
            async def clear_cb(inter):
                clear_global_whitelist()
                await log_admin_action(inter.bot, "Очистка WL", "Весь список удален", inter.user)
                await inter.response.send_message("Global White List очищен.", ephemeral=True)
            btn_clear.callback = clear_cb
            
            view.add_item(btn_add)
            view.add_item(btn_rem)
            view.add_item(btn_show)
            view.add_item(btn_clear)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # === WL MASS ADD ===
        elif val == "wl_mass_add":
            embed = Embed(title="<:freeiconfile3286303:1472678951599083603> Массовое добавление WL", color=AUX_COLOR)
            embed.description = (
                "**White List → Основной список**\n\n"
                "Все участники из Global WL будут автоматически добавлены в основу (если еще не записаны).\n"
                "При переполнении лишние уйдут в резерв."
            )
            
            view = View()
            btn_do = Button(label="Выполнить", style=ButtonStyle.primary, emoji=EMOJI_CHECK)
            
            async def mass_add_cb(inter):
                wl = get_global_whitelist()
                if not wl: return await inter.response.send_message("WL пуст.", ephemeral=True)
                
                struct = get_participants_struct(data)
                existing_ids = {p["user_id"] for p in struct["main"] + struct["reserve"]}
                added_users = []
                
                for uid in wl:
                    if uid not in existing_ids:
                        added_users.append({"user_id": uid, "join_time": time.time()})
                
                struct["main"] = added_users + struct["main"]
                struct = push_to_reserve_if_full(struct, data["max_slots"])
                
                data["participants"] = struct
                save_event(data)
                await update_all_views(inter.bot, data)
                await log_admin_action(inter.bot, "Массовый WL", f"Добавлено: **{len(added_users)}**", inter.user)
                await inter.response.send_message(f"WL → Основа: **{len(added_users)} чел.**", ephemeral=True)
            
            btn_do.callback = mass_add_cb
            view.add_item(btn_do)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # === ADD RESERVE ===
        elif val == "add_reserve":
            embed = Embed(title="<:freeiconplus1828819:1472681225935392858> Внести в резервный список", color=AUX_COLOR)
            embed.description = (
                "Укажите ID участников или теги, которых нужно внести в резерв вручную.\n"
                "Пример: `@User 123456789 987654321`"
            )
            view = View()
            btn = Button(label="Внести ID", style=ButtonStyle.success, emoji=EMOJI_PLUS_BTN)
            btn.callback = lambda i: i.response.send_modal(SmartManageModal("manual_reserve_add", self.event_id, interaction.message))
            view.add_item(btn)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        elif val == "edit":
            embed = Embed(
                title="<:freeicongear889744:1472678585277092084> Редактирование", 
                color=AUX_COLOR
            )
            embed.description = (
                "Изменить название, время, примечание, картинку.\n"
                "Откроется форма редактирования."
            )
            
            view = View(timeout=300)
            btn = Button(
                label="Редактировать", 
                style=ButtonStyle.secondary, 
                emoji="<:freeiconedit1040228:1472654696891158549>"
            )
            
            btn.callback = lambda i: asyncio.create_task(i.response.send_modal(EditEventModal(data, interaction.message)))
            
            view.add_item(btn)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


        # === PAUSE ===
        elif val == "pause":
            embed = Embed(title="<:freeiconstop394592:1472679253177925808> Пауза", color=AUX_COLOR)
            embed.description = "Регистрация будет приостановлена. Участники не смогут записываться."
            view = View()
            btn = Button(label="Остановить регистрацию", style=ButtonStyle.danger, emoji=EMOJI_PAUSE_BTN)
            async def do_pause(inter):
                data["status"] = "paused"
                save_event(data)
                await update_all_views(inter.bot, data)
                await log_admin_action(inter.bot, "Пауза", "Регистрация остановлена", inter.user)
                await inter.response.send_message("<:freeiconstop394592:1472679253177925808> Регистрация ПРИОСТАНОВЛЕНА.", ephemeral=True)
            btn.callback = do_pause
            view.add_item(btn)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # === RESUME ===
        elif val == "resume":
            embed = Embed(title="<:freeiconpowerbutton4943421:1472679504714666056> Возобновить", color=AUX_COLOR)
            embed.description = "Регистрация снова станет доступна."
            view = View()
            btn = Button(label="Возобновить регистрацию", style=ButtonStyle.success, emoji=EMOJI_PLAY)
            async def do_resume(inter):
                data["status"] = "active"
                save_event(data)
                await update_all_views(inter.bot, data)
                await log_admin_action(inter.bot, "Возобновление", "Регистрация открыта", inter.user)
                await inter.response.send_message("<:freeiconpowerbutton4943421:1472679504714666056> Регистрация ВОЗОБНОВЛЕНА.", ephemeral=True)
            btn.callback = do_resume
            view.add_item(btn)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # === KICK ===
        elif val == "kick":
            embed = Embed(title="<:freeiconbroom2954880:1472654679128145981> Кик участника", color=AUX_COLOR)
            embed.description = (
                "Укажите номер участника для удаления.\n"
                "**Примеры:**\n"
                "• `5` — удалить 5-го из основы\n"
                "• `р5` или `r5` — удалить 5-го из резерва"
            )
            view = View()
            btn = Button(label="Удалить участника", style=ButtonStyle.danger, emoji=EMOJI_DOOR_BTN)
            btn.callback = lambda i: i.response.send_modal(SmartManageModal("kick_user", self.event_id, interaction.message))
            view.add_item(btn)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        elif val == "vods":
            embed = Embed(title="<:freeiconyoutube1384060:1472661242941411458> Запрос откатов", color=AUX_COLOR)
            embed.description = (
                "Пингует всех участников основы с просьбой отправить откат.\n"
                "Сообщение будет отправлено в канал ивента."
            )
            view = View()
            btn = Button(label="Отправить запрос", style=ButtonStyle.primary, emoji=EMOJI_CAMERA_BTN)
            
            async def do_vods(inter):
                struct = get_participants_struct(data)
                if not struct["main"]:
                    return await inter.response.send_message("В основе никого нет.", ephemeral=True)
                
                pings = " ".join([f"<@{p['user_id']}>" for p in struct["main"]])
                msg_content = f"<:freeiconyoutube1384060:1472661242941411458> **Запрос откатов!**\n\n{pings}\n\n Отправлять откаты сюда: <#{VOD_SUBMIT_CHANNEL_ID}>"
                
                target = inter.guild.get_channel(data["channel_id"])
                await target.send(msg_content)
                await log_admin_action(inter.bot, "Запрос откатов", "Пинг участников для запроса отката", inter.user)
                await inter.response.send_message("Запрос отправлен.", ephemeral=True)
            
            btn.callback = do_vods
            view.add_item(btn)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await interaction.message.edit(view=OtherOptionsView(self.event_id))
        return False

class EventUserView(View):
    def __init__(self, event_id):
        super().__init__(timeout=None)
        self.event_id = event_id

    @disnake.ui.button(label="Записаться", style=ButtonStyle.success, emoji=EMOJI_JOIN, custom_id="usr_join")
    async def join(self, button, interaction):
        data = get_event_by_id(self.event_id)
        if not data: return await interaction.response.send_message("Ивент не найден.", ephemeral=True)
        if data["status"] == "paused": return await interaction.response.send_message("<:freeiconstop394592:1472679253177925808> Регистрация приостановлена.", ephemeral=True)
        if data["status"] != "active": return await interaction.response.send_message("<:cross:1472654174788255996> Регистрация закрыта.", ephemeral=True)
        
        struct = get_participants_struct(data)
        uid = interaction.user.id
        wl = get_global_whitelist()
        
        has_priority = False
        if interaction.guild:
            role = interaction.guild.get_role(EVENTS_PRIORITY_ROLE_ID)
            if role and role in interaction.user.roles:
                has_priority = True
        
        all_users = struct["main"] + struct["reserve"]
        if any(p["user_id"] == uid for p in all_users):
            return await interaction.response.send_message("Вы уже записаны.", ephemeral=True)
        
        # Ключ назван join_time
        user_data = {"user_id": uid, "join_time": int(time.time())}
        msg = ""

        if uid in wl or has_priority:
            struct["main"].insert(0, user_data)
            msg = "Вы записаны в **ОСНОВУ** (Priority/WL)!"
            struct = push_to_reserve_if_full(struct, data["max_slots"])
        else:
            struct["reserve"].append(user_data)
            msg = "Вы добавлены в **РЕЗЕРВ**."
        
        data["participants"] = struct
        save_event(data)
        await update_all_views(interaction.bot, data)
        await log_user_action(interaction.bot, "Вход", f"Статус: {msg}", interaction.user, False)
        await interaction.response.send_message(msg, ephemeral=True)

    @disnake.ui.button(label="Покинуть список", style=ButtonStyle.danger, custom_id="usr_leave")
    async def leave(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        
        data = get_event_by_id(self.event_id)
        if not data: 
            return await interaction.followup.send("Ивент не найден.", ephemeral=True)
        
        struct = get_participants_struct(data)
        uid = interaction.user.id
        
        all_participants = struct["main"] + struct["reserve"]
        user_data = next((p for p in all_participants if p["user_id"] == uid), None)
        
        if not user_data:
            return await interaction.followup.send("Вас нет в списке участников.", ephemeral=True)
        
        # Исправлено: берем join_time вместо time
        join_timestamp = user_data.get("join_time", 0)
        current_time = int(time.time())
        wait_time = 60
        
        if current_time - join_timestamp < wait_time:
            remaining = wait_time - (current_time - join_timestamp)
            return await interaction.followup.send(
                f"Вы не можете покинуть список так быстро! Подождите еще {remaining} сек.", 
                ephemeral=True
            )

        struct["main"] = [p for p in struct["main"] if p["user_id"] != uid]
        struct["reserve"] = [p for p in struct["reserve"] if p["user_id"] != uid]
        
        if len(struct["main"]) < data["max_slots"] and struct["reserve"]:
            struct["main"].append(struct["reserve"].pop(0))
        
        data["participants"] = struct
        save_event(data)
        
        await update_all_views(interaction.bot, data)
        await log_user_action(interaction.bot, "Выход", "Покинул ивент", interaction.user, True)
        
        await interaction.followup.send("Вы вышли из списка.", ephemeral=True)


class MainAdminView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Начать регистрацию", style=ButtonStyle.secondary, emoji=EMOJI_DICE, row=0, custom_id="start_reg_btn")
    async def start_reg(self, button, interaction):
        await interaction.response.send_modal(EventCreateModal())

    @disnake.ui.button(label="Завершить и очистить", style=ButtonStyle.danger, emoji=EMOJI_TRASH, row=0, custom_id="close_evt_btn")
    async def close_evt(self, button, interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Нет активного мероприятия.", ephemeral=True)
        
        try:
            chan = interaction.guild.get_channel(data["channel_id"])
            msg = await chan.fetch_message(data["message_id"])
            await msg.delete() 
        except: pass
        
        await log_event_history(interaction.bot, data)
        await log_admin_action(interaction.bot, "Ивент завершен", f"Имя: **{data['name']}**", interaction.user)
        
        close_all_active_events()
        await update_all_views(interaction.bot, None)
        await interaction.response.send_message("Ивент завершен и удален.", ephemeral=True)

    @disnake.ui.button(label="Внести в основной список", style=ButtonStyle.secondary, emoji=EMOJI_PLUS, row=1, custom_id="add_main_btn")
    async def add_to_main(self, button, interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Сначала создайте ивент.", ephemeral=True)
        await interaction.response.send_modal(SmartManageModal("reserve_to_main", data["id"]))

    @disnake.ui.button(label="Перевести в резервный список", style=ButtonStyle.secondary, emoji=EMOJI_MINUS, row=1, custom_id="to_res_btn")
    async def move_to_res(self, button, interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Сначала создайте ивент.", ephemeral=True)
        await interaction.response.send_modal(SmartManageModal("main_to_reserve", data["id"]))

    @disnake.ui.button(label="Проверка голосового канала", style=ButtonStyle.secondary, emoji=EMOJI_MIC, row=2, custom_id="chk_voice_btn")
    async def check_voice(self, button, interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Нет активного ивента.", ephemeral=True)
        
        voice = interaction.guild.get_channel(EVENT_VOICE_CHANNEL_ID)
        if not voice: 
            return await interaction.response.send_message(f"Канал {EVENT_VOICE_CHANNEL_ID} не найден.", ephemeral=True)
        
        struct = get_participants_struct(data)
        voice_members = {m.id for m in voice.members}
        
        missing_ids = [p["user_id"] for p in struct["main"] if p["user_id"] not in voice_members]
        
        if missing_ids:
            missing_text = ""
            for uid in missing_ids:
                try:
                    idx = next(i for i, p in enumerate(struct["main"]) if p["user_id"] == uid) + 1
                    missing_text += f"{idx}) <@{uid}>\n"
                except: pass
            
            if len(missing_text) > 1900:
                missing_text = missing_text[:1900].rstrip(",\n") + "\n..."
            else:
                missing_text = missing_text.rstrip()
            
            await interaction.response.send_message(f"**Отсутствуют в войсе:**\n{missing_text}", ephemeral=True)
        else:
            await interaction.response.send_message("Все участники основы в войсе!", ephemeral=True)

    @disnake.ui.button(label="Тегнуть основной список", style=ButtonStyle.secondary, emoji=EMOJI_CHAT, row=2, custom_id="tag_main_btn")
    async def tag_main(self, button, interaction):
        data = get_current_event()
        if not data: return
        
        struct = get_participants_struct(data)
        if not struct["main"]: 
            return await interaction.response.send_message("Основа пуста.", ephemeral=True)
        
        msg = f"**Внимание, основной состав!** {' '.join([f'<@{p['user_id']}>' for p in struct['main']])}"
        event_channel = interaction.guild.get_channel(data["channel_id"])
        await event_channel.send(msg)
        await log_admin_action(interaction.bot, "Тег участников", "Тег основы в канале", interaction.user)
        await interaction.response.send_message("Тег отправлен.", ephemeral=True)

    @disnake.ui.button(label="Пингануть everyone", style=ButtonStyle.secondary, emoji=EMOJI_MEGAPHONE, row=3, custom_id="ping_ev_btn")
    async def ping_everyone(self, button, interaction):
        data = get_current_event()
        if not data: return
        
        embed = Embed(color=AUX_COLOR)
        channel_mention = f"<#{data['channel_id']}>"
        embed.description = (
            f"Регистрация откраты: {channel_mention}\n"
            f"Время: **{data['event_time']}**"
        )
        
        target = interaction.guild.get_channel(EVENTS_TAG_CHANNEL_ID)
        if not target:
            target = interaction.guild.get_channel(data["channel_id"])
        
        await target.send(content=f"@everyone **{data['name']}**", embed=embed)
        await log_admin_action(interaction.bot, "Пинг @everyone", "Анонс ивента", interaction.user)
        await interaction.response.send_message("Анонс отправлен.", ephemeral=True)

    @disnake.ui.button(label="Меню управления", style=ButtonStyle.primary, emoji=EMOJI_GEAR, row=3, custom_id="other_btn")
    async def other(self, button, interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Нет активного ивента.", ephemeral=True)
        
        embed = Embed(title="<:freeicongear889744:1472678585277092084> Меню управления", color=AUX_COLOR)
        desc = (
            "**<:freeiconstar7408613:1472654730902765678> White List** — управление WL ID и массовый перенос\n"
            "**<:freeiconplus1828819:1472681225935392858> Внести в резерв** — ручной ввод участников\n"
            "**<:freeiconedit1040228:1472654696891158549> Редактировать Embed** — изменить название, время, описание, картинку\n"
            "**<:freeiconstop394592:1472679253177925808> Пауза / <:freeiconpowerbutton4943421:1472679504714666056> Старт** — остановить/возобновить регистрацию\n"
            "**<:freeiconbroom2954880:1472654679128145981> Кик** — удалить участника\n"
            "**<:freeiconyoutube1384060:1472661242941411458> Запрос откатов** — пинг участников для запроса отката\n"
        )
        embed.description = desc
        await interaction.response.send_message(embed=embed, view=OtherOptionsView(data["id"]), ephemeral=False)

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_events_db()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        try:
            self.bot.add_view(MainAdminView())
            current = get_current_event()
            if current:
                self.bot.add_view(EventUserView(current["id"]))
            
            chan = self.bot.get_channel(EVENTS_ADMIN_CHANNEL_ID)
            if chan:
                panel_msg = None
                async for msg in chan.history(limit=10):
                    if msg.author == self.bot.user and msg.components:
                         try:
                             if msg.components[0].children[0].custom_id == "start_reg_btn":
                                 panel_msg = msg
                                 break
                         except: pass
                
                embeds = generate_admin_embeds(current, bot=self.bot)
                if panel_msg:
                    await panel_msg.edit(embeds=embeds, view=MainAdminView())
                else:
                    await chan.send(embeds=embeds, view=MainAdminView())
        except Exception as e:
            print(f"[EVENTS] Error: {e}")

    @commands.command(name="event")
    @commands.has_permissions(administrator=True)
    async def event_panel(self, ctx):
        await ctx.message.delete()
        await ctx.send(embeds=generate_admin_embeds(None), view=MainAdminView())

def setup(bot):
    bot.add_cog(EventsCog(bot))
