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

# --- ИМПОРТ ИЗ CONSTANTS ---
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from constants import EVENTS_CHANNEL_ID, EVENTS_ADMIN_CHANNEL_ID
    try: from constants import EVENT_VOICE_CHANNEL_ID 
    except: EVENT_VOICE_CHANNEL_ID = 1469489179766292755
    try: from constants import EVENTS_TAG_CHANNEL_ID 
    except: EVENTS_TAG_CHANNEL_ID = 1469491042679128164
except ImportError:
    EVENTS_CHANNEL_ID = 0
    EVENTS_ADMIN_CHANNEL_ID = 0
    EVENT_VOICE_CHANNEL_ID = 1469489179766292755
    EVENTS_TAG_CHANNEL_ID = 1469491042679128164

DB_PATH = Path("events.db")

# --- DB FUNCTIONS ---

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
    conn.commit()
    conn.close()

def get_current_event():
    init_events_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE status IN ("active", "draft") ORDER BY created_at DESC LIMIT 1')
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
    if isinstance(parts_data, str): parts_json = parts_data
    else: parts_json = json.dumps(parts_data)
    
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
    cursor.execute('UPDATE events SET status = "closed" WHERE status IN ("active", "draft")')
    conn.commit()
    conn.close()

def delete_event(event_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
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

# --- HELPERS ---

def extract_ids(text):
    ids = re.findall(r'<@!?(\d+)>|(\d{17,20})', text)
    result = []
    for match in ids:
        uid = match[0] if match[0] else match[1]
        if uid: result.append(int(uid))
    return list(set(result))

def generate_admin_embed(data=None):
    embed = Embed(color=0x2B2D31)
    
    if not data:
        desc = (
            "**Мероприятие проводит:** -\n"
            "**Мероприятие:** -\n"
            "**Регистрация:** не активна\n\n"
            "> Время: -\n"
            "> Примечание: -\n"
        )
        embed.description = desc
        embed.add_field(name="Зарегистрированные участники: 0", value="**Основной список: (0/0)**", inline=False)
        embed.add_field(name="⠀", value="Пусто", inline=True)
        embed.add_field(name="Резерв: 0", value="Пусто", inline=False)
        return embed

    struct = get_participants_struct(data)
    main_list = struct["main"]
    reserve_list = struct["reserve"]
    max_slots = data["max_slots"]
    
    status_text = "приостановлена" if data["status"] == "draft" else "доступна"
    
    desc_text = (
        f"**Мероприятие проводит:** {data['organizer']}\n"
        f"**Мероприятие:** {data['name']}\n"
        f"**Регистрация:** {status_text}\n\n"
        f"> Время: {data['event_time']}\n"
        f"> Примечание: {data['description']}\n"
    )
    embed.description = desc_text
    
    embed.add_field(
        name=f"Зарегистрированные участники: {len(main_list) + len(reserve_list)}", 
        value=f"**Основной список: ({len(main_list)}/{max_slots})**", 
        inline=False
    )
    
    split_at = 25
    col1 = ""
    col2 = ""
    for i, p_data in enumerate(main_list):
        num = i + 1
        uid = int(p_data["user_id"])
        line = f"{num}) <@{uid}>\n"
        if i < split_at: col1 += line
        else: col2 += line
    if not col1: col1 = "Пусто"
    
    embed.add_field(name="⠀", value=col1, inline=True)
    if col2: embed.add_field(name="⠀", value=col2, inline=True)
    
    if reserve_list:
        res_text = ""
        for i, p_data in enumerate(reserve_list):
            res_text += f"{i+1}) <@{p_data['user_id']}>\n"
        if len(res_text) > 1000: res_text = res_text[:1000] + "..."
        embed.add_field(name=f"Резерв: {len(reserve_list)}", value=res_text, inline=False)
    else:
        embed.add_field(name=f"Резерв: 0", value="Пусто", inline=False)
        
    if data.get("image_url"):
        embed.set_image(url=data["image_url"])
        
    embed.set_footer(text=f"ID: {data['id']}")
    return embed

async def update_all_views(bot, data=None):
    admin_chan = bot.get_channel(EVENTS_ADMIN_CHANNEL_ID)
    if admin_chan:
        target_msg = None
        async for msg in admin_chan.history(limit=10):
            if msg.author == bot.user and msg.components:
                 try:
                     if msg.components[0].children[0].custom_id == "start_reg_btn":
                         target_msg = msg
                         break
                 except: pass
        
        embed = generate_admin_embed(data)
        if target_msg:
            await target_msg.edit(embed=embed, view=MainAdminView())
        else:
            await admin_chan.send(embed=embed, view=MainAdminView())

    if data and data.get("message_id"):
        try:
            chan = bot.get_channel(data["channel_id"])
            if chan:
                msg = await chan.fetch_message(data["message_id"])
                await msg.edit(embed=generate_admin_embed(data), view=EventUserView(data["id"]))
        except: pass

# --- MODALS ---

class EventCreateModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Название мероприятия", custom_id="name", placeholder="ВЗХ ЭКЛИПС", required=True),
            TextInput(label="Кто проводит", custom_id="organizer", placeholder="jozzylord", required=True),
            TextInput(label="Время (текстом)", custom_id="time", placeholder="19:00", required=True),
            TextInput(label="Количество слотов (число)", custom_id="slots", placeholder="50", required=True),
            TextInput(label="Ссылка на скриншот (необяз.)", custom_id="image", required=False),
        ]
        super().__init__(title="Настройка мероприятия", components=components)

    async def callback(self, interaction: Interaction):
        try: slots = int(interaction.text_values["slots"])
        except: return await interaction.response.send_message("Слоты - число.", ephemeral=True)
            
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
            
        embed = generate_admin_embed(new_event)
        pub_msg = await pub_chan.send(embed=embed, view=EventUserView(event_id))
        new_event["message_id"] = pub_msg.id
        
        save_event(new_event)
        await update_all_views(interaction.bot, new_event)
        await interaction.response.send_message("✅ Регистрация запущена!", ephemeral=True)

class SmartManageModal(Modal):
    def __init__(self, mode, event_id):
        self.mode = mode
        self.event_id = event_id
        if mode == "reserve_to_main":
            title = "Из Резерва -> В Основу"
            label = "Номера из РЕЗЕРВА (1 2 5)"
        elif mode == "main_to_reserve":
            title = "Из Основы -> В Резерв"
            label = "Номера из ОСНОВЫ (1 5)"
        else:
            title = "Управление"
            label = "Данные"
        components = [TextInput(label=label, custom_id="input", placeholder="1 2 3")]
        super().__init__(title=title, components=components)

    async def callback(self, interaction: Interaction):
        data = get_event_by_id(self.event_id)
        if not data: return
        struct = get_participants_struct(data)
        
        raw_input = interaction.text_values["input"].replace(",", " ")
        try: indices = sorted(list(set([int(x) for x in raw_input.split() if x.isdigit()])))
        except: return await interaction.response.send_message("❌ Введите только цифры.", ephemeral=True)

        if not indices: return await interaction.response.send_message("❌ Нет цифр.", ephemeral=True)

        count = 0
        if self.mode == "reserve_to_main":
            users_to_move = []
            for idx in indices:
                real_idx = idx - 1
                if 0 <= real_idx < len(struct["reserve"]): users_to_move.append(struct["reserve"][real_idx])
            ids_to_remove = [u["user_id"] for u in users_to_move]
            struct["reserve"] = [p for p in struct["reserve"] if p["user_id"] not in ids_to_remove]
            for u in users_to_move:
                u["join_time"] = time.time()
                struct["main"].append(u)
                count += 1
                
        elif self.mode == "main_to_reserve":
            users_to_move = []
            for idx in indices:
                real_idx = idx - 1
                if 0 <= real_idx < len(struct["main"]): users_to_move.append(struct["main"][real_idx])
            ids_to_remove = [u["user_id"] for u in users_to_move]
            struct["main"] = [p for p in struct["main"] if p["user_id"] not in ids_to_remove]
            for u in users_to_move:
                u["join_time"] = time.time()
                struct["reserve"].append(u)
                count += 1

        data["participants"] = struct
        save_event(data)
        await update_all_views(interaction.bot, data)
        await interaction.response.send_message(f"✅ Перемещено участников: {count}", ephemeral=True)

# --- VIEWS ---

class OtherOptionsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        options = [
            disnake.SelectOption(label="Формирования приоритетных 20 слотов main состава", emoji="⭐", value="prio"),
            disnake.SelectOption(label="Поместить в резерв другого участника вместо него", emoji="➕", value="swap"),
            disnake.SelectOption(label="Изменить информацию в Embed", emoji="⚙️", value="edit"),
            disnake.SelectOption(label="Временно приостановить добавление в список", emoji="🚫", value="pause"),
            disnake.SelectOption(label="Снять паузу с регистрации", emoji="🔄", value="resume"),
            disnake.SelectOption(label="Убрать человека из регистрации", emoji="🚪", value="kick"),
            disnake.SelectOption(label="Заменить невидимый символ на картинку", emoji="🖼️", value="img"),
            disnake.SelectOption(label="Активность участников (резерв/основа)", emoji="📊", value="stats"),
            disnake.SelectOption(label="Запрос откатов, пинг списка основы", emoji="🎥", value="vods"),
        ]
        
        self.add_item(Select(placeholder="Прочие функции бота", options=options, custom_id="other_select"))

    async def interaction_check(self, interaction: Interaction):
        await interaction.response.send_message(f"Вы выбрали: {interaction.data['values'][0]} (В разработке)", ephemeral=True)
        return False


class EventUserView(View):
    def __init__(self, event_id):
        super().__init__(timeout=None)
        self.event_id = event_id

    @disnake.ui.button(label="Записаться", style=ButtonStyle.success, emoji="➕", custom_id="usr_join")
    async def join(self, button: Button, interaction: Interaction):
        data = get_event_by_id(self.event_id)
        if not data or data["status"] != "active": return await interaction.response.send_message("Закрыто.", ephemeral=True)
            
        struct = get_participants_struct(data)
        uid = interaction.user.id
        
        if any(p["user_id"] == uid for p in struct["main"]) or any(p["user_id"] == uid for p in struct["reserve"]):
            return await interaction.response.send_message("⚠️ Вы уже записаны.", ephemeral=True)
            
        struct["reserve"].append({"user_id": uid, "join_time": time.time()})
        data["participants"] = struct
        save_event(data)
        await update_all_views(interaction.bot, data)
        await interaction.response.send_message("✅ Вы в резерве.", ephemeral=True)

    @disnake.ui.button(label="Покинуть список", style=ButtonStyle.danger, emoji="➖", custom_id="usr_leave")
    async def leave(self, button: Button, interaction: Interaction):
        data = get_event_by_id(self.event_id)
        if not data: return
        struct = get_participants_struct(data)
        uid = interaction.user.id
        struct["main"] = [p for p in struct["main"] if p["user_id"] != uid]
        struct["reserve"] = [p for p in struct["reserve"] if p["user_id"] != uid]
        data["participants"] = struct
        save_event(data)
        await update_all_views(interaction.bot, data)
        await interaction.response.send_message("🗑️ Вы вышли.", ephemeral=True)


class MainAdminView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Начать регистрацию", style=ButtonStyle.secondary, emoji="🎰", row=0, custom_id="start_reg_btn")
    async def start_reg(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(EventCreateModal())

    @disnake.ui.button(label="Завершить и очистить", style=ButtonStyle.danger, emoji="🗑️", row=0, custom_id="close_evt_btn")
    async def close_evt(self, button: Button, interaction: Interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Нет активного мероприятия.", ephemeral=True)
        try:
            chan = interaction.guild.get_channel(data["channel_id"])
            msg = await chan.fetch_message(data["message_id"])
            await msg.delete() 
        except: pass
        close_all_active_events()
        await update_all_views(interaction.bot, None)
        await interaction.response.send_message("✅ Завершено.", ephemeral=True)

    @disnake.ui.button(label="Внести в основной список", style=ButtonStyle.secondary, emoji="➕", row=1, custom_id="add_main_btn")
    async def add_to_main(self, button: Button, interaction: Interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Сначала создайте ивент.", ephemeral=True)
        await interaction.response.send_modal(SmartManageModal("reserve_to_main", data["id"]))

    @disnake.ui.button(label="Перевести в резервный список", style=ButtonStyle.secondary, emoji="➖", row=1, custom_id="to_res_btn")
    async def move_to_res(self, button: Button, interaction: Interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Сначала создайте ивент.", ephemeral=True)
        await interaction.response.send_modal(SmartManageModal("main_to_reserve", data["id"]))

    @disnake.ui.button(label="Проверка участников в войсе", style=ButtonStyle.secondary, emoji="🚫", row=2, custom_id="chk_voice_btn")
    async def check_voice(self, button: Button, interaction: Interaction):
        data = get_current_event()
        if not data: return await interaction.response.send_message("Нет ивента.", ephemeral=True)
        
        voice = interaction.guild.get_channel(EVENT_VOICE_CHANNEL_ID)
        if not voice: return await interaction.response.send_message(f"❌ Канал {EVENT_VOICE_CHANNEL_ID} не найден.", ephemeral=True)
            
        struct = get_participants_struct(data)
        voice_members = {m.id for m in voice.members}
        
        missing_ids = [p["user_id"] for p in struct["main"] if p["user_id"] not in voice_members]
        
        missing_text = ""
        for uid in missing_ids:
            try:
                idx = next(i for i, p in enumerate(struct["main"]) if p["user_id"] == uid) + 1
                missing_text += f"{idx}) <@{uid}>, "
            except: pass
            
        if missing_text: missing_text = missing_text.rstrip(", ")
        else: missing_text = "Все на месте!"

        await interaction.response.send_message(f"Отсутствуют игроки, зарегистрированные в основной список: {missing_text}", ephemeral=True)

    @disnake.ui.button(label="Тегнуть основной список", style=ButtonStyle.secondary, emoji="💬", row=2, custom_id="tag_main_btn")
    async def tag_main(self, button: Button, interaction: Interaction):
        data = get_current_event()
        if not data: return
        struct = get_participants_struct(data)
        if not struct["main"]: return await interaction.response.send_message("Пусто.", ephemeral=True)
        
        # 1. Формируем сообщение с тегами
        msg = f"{' '.join([f'<@{p['user_id']}>' for p in struct['main']])}"
        
        # 2. Отправляем в КАНАЛ С ПЛЮСАМИ (там где юзеры жмут +)
        event_channel = interaction.guild.get_channel(data["channel_id"])
        await event_channel.send(msg)
        
        await interaction.response.send_message("✅ Список упомянут в канале мероприятия.", ephemeral=True)

    @disnake.ui.button(label="Пинг от бота с @everyone", style=ButtonStyle.secondary, emoji="📢", row=3, custom_id="ping_ev_btn")
    async def ping_everyone(self, button: Button, interaction: Interaction):
        data = get_current_event()
        if not data: return
        
        embed = Embed(color=0x2B2D31)
        # Ссылка на канал ивента
        channel_mention = f"<#{data['channel_id']}>"
        
        embed.description = (
            f"Регистрация открыта — {channel_mention}\n"
            f"Время: {data['event_time']}\n"
        )
        
        # Отправляем в канал тегов (или в канал ивента? Обычно в анонсы)
        # Пользователь сказал "сообщение регистрация открыта: ссылка на канал мероприятия".
        # Обычно такие пинги кидают в общий канал.
        # Пусть кидает в канал, указанный в EVENTS_TAG_CHANNEL_ID (если это канал анонсов).
        # Если нет, то кидаем в канал ивента.
        
        target = interaction.guild.get_channel(EVENTS_TAG_CHANNEL_ID)
        if not target: target = interaction.guild.get_channel(data["channel_id"])
            
        await target.send(
            content=f"@everyone {data['name']}",
            embed=embed
        )
        await interaction.response.send_message("✅ Пинг отправлен.", ephemeral=True)

    @disnake.ui.button(label="Прочие возможности бота", style=ButtonStyle.primary, emoji="⚙️", row=3, custom_id="other_btn")
    async def other(self, button: Button, interaction: Interaction):
        embed = Embed(title="⚙️ Прочие функции бота", color=0x2B2D31)
        desc = (
            "⭐ = Формирования приоритетных 20 слотов main состава\n"
            "➕ = Поместить в резерв другого участника вместо него\n"
            "⚙️ = Изменить информацию в Embed - МП, время, примечание\n"
            "🚫 = Временно приостановить добавление в список\n"
            "🔄 = Снять паузу с регистрации\n"
            "🚪 = Убрать человека из регистрации\n"
            "🖼️ = Заменить невидимый символ на картинку\n"
            "📊 = Активность участников (резерв/основа)\n"
            "🎥 = Запрос откатов, пинг списка основы"
        )
        embed.description = desc
        await interaction.response.send_message(embed=embed, view=OtherOptionsView(), ephemeral=True)

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
                
                embed = generate_admin_embed(current)
                if panel_msg:
                    await panel_msg.edit(embed=embed, view=MainAdminView())
                else:
                    await chan.send(embed=embed, view=MainAdminView())

        except Exception as e: print(f"[EVENTS] Error: {e}")

def setup(bot):
    bot.add_cog(EventsCog(bot))
