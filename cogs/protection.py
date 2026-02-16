import time
import disnake
from datetime import datetime, timezone, timedelta
from disnake.ext import commands
from disnake.ui import View, Button, Select, Modal, TextInput
from disnake import Interaction, ButtonStyle, SelectOption, AuditLogEntry, Color, Embed
import sqlite3
from pathlib import Path
import asyncio
import json

# Импортируем конфиг из корня проекта
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import PROTECTION_ADMIN_CHANNEL_ID, PROTECTION_LOG_CHANNEL_ID, SUPPORT_ROLE_ID

DB_PATH = Path("protection.db")

# --- DATABASE FUNCTIONS ---
def init_protection_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS protection_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            user_id INTEGER PRIMARY KEY,
            total_warns INTEGER DEFAULT 0,
            actions_progress TEXT
        )
    ''')
    conn.commit()
    conn.close()

def load_config():
    init_protection_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM protection_config WHERE key = ?', ('config',))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    
    default = {
        "events": {
            "channel_delete": "ban",
            "channel_create": "ban",
            "webhook_create": "ban",
            "webhook_send": "kick",
            "ban_member": "kick",
            "kick_member": "kick",
            "everyone_ping": "kick",
            "here_ping": "kick"
        },
        "whitelist": [],
        "panel_message_id": None
    }
    save_config(default)
    return default

def save_config(config):
    init_protection_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO protection_config (key, value) VALUES (?, ?)',
        ('config', json.dumps(config, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

def load_violations():
    init_protection_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, total_warns, actions_progress FROM violations')
    rows = cursor.fetchall()
    conn.close()
    
    violations = {}
    for user_id, total_warns, actions_progress_str in rows:
        violations[str(user_id)] = {
            "total_warns": total_warns,
            "actions_progress": json.loads(actions_progress_str) if actions_progress_str else {}
        }
    return violations

def save_violations(data):
    init_protection_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM violations')
    for user_id_str, violation_data in data.items():
        user_id = int(user_id_str)
        total_warns = violation_data.get("total_warns", 0)
        actions_progress = json.dumps(violation_data.get("actions_progress", {}))
        cursor.execute(
            'INSERT INTO violations (user_id, total_warns, actions_progress) VALUES (?, ?, ?)',
            (user_id, total_warns, actions_progress)
        )
    conn.commit()
    conn.close()

def load_whitelist():
    init_protection_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM whitelist')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_to_whitelist(user_id):
    init_protection_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_from_whitelist(user_id):
    init_protection_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM whitelist WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# --- CONSTANTS & UI ---

EVENT_EMOJIS = {
    "channel_delete": "<:freeicondelete3625005:1472679616589205604>",
    "channel_create": "<:freeiconplus1828819:1472681225935392858>",
    "webhook_create": "<:link:1472654744316018843>",
    "webhook_send": "<:freeiconsending1149588:1472654727257788559>",
    "ban_member": "<:ban:1472654052763500584>",
    "kick_member": "<:freeiconblooddrop893529:1472654677735637145>",
    "everyone_ping": "<:emoji:1472654055343001833>",
    "here_ping": "<:freeiconnotification1827370:1472654716537409537>"
}

ACTION_NAMES = {
    "ban": "Бан",
    "kick": "Кик",
    "warn": "Варн",
    "tempban": "Врем. бан",
    "none": "Без действий",
    "delete": "Удалять"
}

ACTION_EMOJIS = {
    "ban": "<:ban:1472654052763500584>",
    "kick": "<:freeiconblooddrop893529:1472654677735637145>",
    "warn": "<:freeiconalert8452627:1472654676351778816>",
    "tempban": "<:freeiconclock12476999:1472654689815232834>",
    "none": "<:tik:1472654073814581268>",
    "delete": "<:freeicondelete3625005:1472679616589205604>"
}

config = load_config()

EVENTS = {
    "channel_delete": "Удаление канала",
    "channel_create": "Создание канала",
    "webhook_create": "Создание вебхука",
    "webhook_send": "Отправка от вебхука",
    "ban_member": "Бан участника",
    "kick_member": "Кик участника",
    "everyone_ping": "Пинг @everyone",
    "here_ping": "Пинг @here"
}

class ActionSelect(View):
    def __init__(self, event_key):
        super().__init__(timeout=300)
        self.event_key = event_key

        select = Select(
            placeholder="Выберите действие",
            options=[
                SelectOption(label="Бан", value="ban", emoji="<:ban:1472654052763500584>"),
                SelectOption(label="Кик", value="kick", emoji="<:freeiconblooddrop893529:1472654677735637145>"),
                SelectOption(label="Предупреждение", value="warn", emoji="<:freeiconalert8452627:1472654676351778816>"),
                SelectOption(label="Временный бан", value="tempban", emoji="<:freeiconclock12476999:1472654689815232834>"),
                SelectOption(label="Без действий", value="none", emoji="<:tik:1472654073814581268>")
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: disnake.Interaction):
        action = interaction.data["values"][0]
        
        if action == "none":
            config["events"][self.event_key] = {"action": "none", "limit": 1}
            save_config(config)
            
            event_name = EVENTS.get(self.event_key, self.event_key)
            embed = disnake.Embed(
                title="Защита отключена",
                description=f"Для события **`{event_name}`** теперь не применяются никакие санкции.",
                color=disnake.Color.from_rgb(54, 57, 63)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await update_protection_panel(interaction.guild)
        
        else:
            await interaction.response.send_modal(ActionConfigModal(self.event_key, action))

class WhitelistModal(Modal):
    def __init__(self):
        components = [TextInput(label="ID пользователя", custom_id="user_id", placeholder="Введите ID", required=True)]
        super().__init__(title="Добавить в вайтлист", components=components)

    async def callback(self, interaction: Interaction):
        try:
            uid = int(interaction.text_values["user_id"].strip())
        except ValueError:
            await interaction.response.send_message("Неверный ID.", ephemeral=True)
            return

        whitelist = load_whitelist()
        if uid in whitelist:
            await interaction.response.send_message("Уже в вайтлисте.", ephemeral=True)
            return

        add_to_whitelist(uid)
        
        config["whitelist"] = load_whitelist()
        save_config(config)
        
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else "Неизвестно"
        await interaction.response.send_message(f" {name} (`{uid}`) добавлен в вайтлист.", ephemeral=True)
        await update_protection_panel(interaction.guild)

class RemoveWhitelistModal(Modal):
    def __init__(self):
        components = [TextInput(label="ID пользователя", custom_id="user_id", placeholder="Введите ID для удаления", required=True)]
        super().__init__(title="Удалить из вайтлиста", components=components)

    async def callback(self, interaction: Interaction):
        try:
            uid = int(interaction.text_values["user_id"].strip())
        except ValueError:
            await interaction.response.send_message(" Неверный ID. Введите только цифры.", ephemeral=True)
            return

        whitelist = load_whitelist()
        if uid not in whitelist:
            await interaction.response.send_message(" Этот ID не найден в вайтлисте.", ephemeral=True)
            return

        remove_from_whitelist(uid)
        
        config["whitelist"] = load_whitelist()
        save_config(config)
        
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else "Неизвестно"
        await interaction.response.send_message(f" Пользователь **{name}** (`{uid}`) удалён из вайтлиста.", ephemeral=True)
        await update_protection_panel(interaction.guild)

class ProtectionConfigView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.select(
        placeholder="Выберите событие для настройки",
        custom_id="protection_event_select",
        options=[
            disnake.SelectOption(label="Удаление канала", value="channel_delete", description="Массовое удаление текстовых каналов", emoji="<:freeicondelete3625005:1472679616589205604>"),
            disnake.SelectOption(label="Создание канала", value="channel_create", description="Массовое создание текстовых каналов ", emoji="<:freeiconplus1828819:1472681225935392858>"),
            disnake.SelectOption(label="Создание вебхука", value="webhook_create", description="Создание интеграции & Вебхука", emoji="<:link:1472654744316018843>"),
            disnake.SelectOption(label="Отправка от вебхука", value="webhook_send", description="Взаимодействие с URL вебхука", emoji="<:freeiconsending1149588:1472654727257788559>"),
            disnake.SelectOption(label="Бан участника", value="ban_member", description="Реакция на массовые блокировки участников", emoji="<:ban:1472654052763500584>"),
            disnake.SelectOption(label="Кик участника", value="kick_member", description="Защита от массовых исключений участников", emoji="<:freeiconblooddrop893529:1472654677735637145>"),
            disnake.SelectOption(label="Пинг @everyone", value="everyone_ping", description="Ограничение упоминаний роли @everyone", emoji="<:emoji:1472654055343001833>"),
            disnake.SelectOption(label="Пинг @here", value="here_ping", description="Ограничение упоминаний роли @here", emoji="<:freeiconnotification1827370:1472654716537409537>")
        ]
    )
    async def event_select(self, select: disnake.ui.Select, interaction: disnake.Interaction):
        if interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Только владелец сервера может настраивать защиту.", ephemeral=True)
            return
        
        event_key = select.values[0]
        view = ActionSelect(event_key)
        
        # 1. Отправляем меню настройки (эфемерно)
        await interaction.response.send_message(
            f"Настройка: **{EVENTS.get(event_key, event_key)}**", 
            view=view, 
            ephemeral=True
        )
        
        # 2. СБРОС СЕЛЕКТА НА ОСНОВНОМ СООБЩЕНИИ
        await interaction.message.edit(view=self)


    @disnake.ui.button(label="Вайтлист", style=ButtonStyle.grey, custom_id="protection_whitelist")
    async def whitelist_button(self, button: Button, interaction: Interaction):
        if interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Только владелец сервера может управлять вайтлистом.", ephemeral=True)
            return
        
        whitelist = load_whitelist()
        text = "Вайтлист пуст." if not whitelist else "\n".join(f"• <@{uid}> (`{uid}`)" for uid in whitelist[:20])
        if len(whitelist) > 20:
            text += f"\n... и ещё {len(whitelist) - 20}"
        embed = disnake.Embed(title="Вайтлист защиты", description=text, color=disnake.Color.from_rgb(54, 57, 63))
        view = WhitelistView(interaction.guild.owner.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class WhitelistView(View):
    def __init__(self, owner_id):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    @disnake.ui.button(label="Добавить", style=ButtonStyle.green)
    async def add(self, button: Button, interaction: Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец сервера может это делать.", ephemeral=True)
            return
        await interaction.response.send_modal(WhitelistModal())
    
    @disnake.ui.button(label="Удалить пользователя", style=ButtonStyle.red)
    async def remove(self, button: Button, interaction: Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец сервера может это делать.", ephemeral=True)
            return
        await interaction.response.send_modal(RemoveWhitelistModal())

async def update_protection_panel(guild: disnake.Guild):
    channel = guild.get_channel(PROTECTION_ADMIN_CHANNEL_ID)
    if not channel:
        print("[ЗАЩИТА] Админский канал не найден!")
        return

    try:
        config_lines = []
        for event_key, data in config["events"].items():
            if isinstance(data, dict):
                action = data.get("action", "none")
                limit = data.get("limit", 1)
                duration = data.get("duration", 0)
            else:
                action = data
                limit = 1
                duration = 0

            event_name = EVENTS.get(event_key, event_key)
            action_name = ACTION_NAMES.get(action, action)
            event_emoji = EVENT_EMOJIS.get(event_key, "⚙️")
            action_emoji = ACTION_EMOJIS.get(action, "❓")
            
            time_info = f" ({duration}м)" if action == "tempban" else ""
            limit_text = f"  {action_emoji} `{action_name}{time_info}` `{limit}`" if action != "none" else f"  {action_emoji} `{action_name}`"
            line = f"{event_emoji} **{event_name}**{limit_text}"
            config_lines.append(line)

        config_text = "\n".join(config_lines)
        embed = disnake.Embed(color=disnake.Color.from_rgb(54, 57, 63))
        embed.description = "## Панель управления защитой"

        current_field_value = ""
        first_field = True
        for line in config_lines:
            if len(current_field_value) + len(line) + 1 > 1020:
                embed.add_field(
                    name="**```Конфигурация защиты```**" if first_field else "\u200b",
                    value=current_field_value,
                    inline=False
                )
                current_field_value = line + "\n"
                first_field = False
            else:
                current_field_value += line + "\n"

        if current_field_value:
            embed.add_field(
                name="**```Конфигурация защиты```**" if first_field else "\u200b",
                value=current_field_value,
                inline=False
            )

        terms_text = (
            "**Бан** — Блокировка и снятие ролей\n"
            "**Кик** — Исключение из сервера\n"
            "**Без действий** — Санкции отключены\n"
            "**Warn** — Уведомление, затем кик"
        )
        embed.add_field(name="\u200b", value=f"```Термины```\n>>> {terms_text}", inline=False)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text=f"{guild.name}", icon_url=guild.icon.url)
        else:
            embed.set_footer(text=f"{guild.name}")

        view = ProtectionConfigView()
        message_id = config.get("panel_message_id")
        panel_processed = False

        if message_id:
            try:
                old_message = await channel.fetch_message(message_id)
                await old_message.edit(embed=embed, view=view)
                panel_processed = True
                print(f"[ЗАЩИТА] Панель обновлена (ID: {message_id})")
            except (disnake.NotFound, disnake.HTTPException):
                print("[ЗАЩИТА] Старая панель не найдена (удалена), создаю новую...")
                panel_processed = False

        if not panel_processed:
            new_message = await channel.send(embed=embed, view=view)
            config["panel_message_id"] = new_message.id
            save_config(config)
            print(f"[ЗАЩИТА] Новая панель успешно отправлена. ID: {new_message.id}")

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА ПАНЕЛИ] {e}")

class ActionConfigModal(Modal):
    def __init__(self, event_key, action):
        components = [
            TextInput(
                label="Лимит срабатываний",
                custom_id="limit_input",
                placeholder="Через сколько действий наказать? (например: 3)",
                value="1", min_length=1, max_length=3
            )
        ]
        if action == "tempban":
            components.append(TextInput(
                label="Длительность (в минутах)",
                custom_id="time_input",
                placeholder="Например: 60 (1 час), максимум 40320 (28 дней)",
                value="60", min_length=1, max_length=6
            ))
            
        super().__init__(title=f"Настройка: {EVENTS.get(event_key)}", components=components)
        self.event_key = event_key
        self.action = action

    async def callback(self, interaction: Interaction):
        try:
            limit_val = int(interaction.text_values["limit_input"].strip())
            duration_val = 0
            if self.action == "tempban":
                duration_val = int(interaction.text_values["time_input"].strip())
                if duration_val > 40320: duration_val = 40320
            
            if limit_val < 1: raise ValueError
        except ValueError:
            return await interaction.response.send_message("Ошибка: Введите корректные числа.", ephemeral=True)

        config["events"][self.event_key] = {
            "action": self.action,
            "limit": limit_val,
            "duration": duration_val
        }
        save_config(config)

        time_text = f"\nВремя изоляции: `{duration_val}` мин." if self.action == "tempban" else ""
        embed = disnake.Embed(
            title="⚙️ Конфигурация обновлена",
            description=(
                f"Событие: **{EVENTS.get(self.event_key)}**\n"
                f"Наказание: `{ACTION_NAMES.get(self.action)}`\n"
                f"Лимит действий:  <:freeiconalert8452627:1472654676351778816> `{limit_val}`" + time_text
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await update_protection_panel(interaction.guild)

class ProtectionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.violations = {}     # Инициализируем пустым
        self.user_messages = {}
        # Не вызываем методы БД здесь!

    @commands.Cog.listener()
    async def on_ready(self):
        # Инициализируем БД и загружаем данные, когда бот уже запустился
        init_protection_db()
        self.violations = load_violations()
        await self.setup_protection_panel()
        print("[PROTECTION] База данных и панели загружены.")


    async def setup_protection_panel(self):
        await self.bot.wait_until_ready()
        self.bot.add_view(ProtectionConfigView())
        for guild in self.bot.guilds:
            await update_protection_panel(guild)
            print(f"[ЗАЩИТА] Панель инициализирована для сервера: {guild.name}")

    async def handle_action(self, entry: AuditLogEntry = None, message: disnake.Message = None):
        user = entry.user if entry else message.author
        guild = entry.guild if entry else message.guild

        whitelist = load_whitelist()
        if user.bot or user == guild.owner or user.id in whitelist:
            return

        action_type = None
        if entry:
            mapping = {
                disnake.AuditLogAction.channel_delete: "channel_delete",
                disnake.AuditLogAction.channel_create: "channel_create",
                disnake.AuditLogAction.webhook_create: "webhook_create",
                disnake.AuditLogAction.webhook_update: "webhook_send",
                disnake.AuditLogAction.ban: "ban_member",
                disnake.AuditLogAction.kick: "kick_member"
            }
            action_type = mapping.get(entry.action)
        elif message and (message.mention_everyone or "@here" in message.content):
            action_type = "everyone_ping" if "@everyone" in message.content else "here_ping"

        if not action_type:
            return

        setting_raw = config["events"].get(action_type, "none")
        if isinstance(setting_raw, dict):
            setting = setting_raw.get("action", "none")
            limit = int(setting_raw.get("limit", 1))
        else:
            setting = setting_raw
            limit = 1

        if setting == "none":
            return

        uid_str = str(user.id)
        if uid_str not in self.violations:
            self.violations[uid_str] = {"total_warns": 0, "actions_progress": {}}
        
        progress = self.violations[uid_str]["actions_progress"].get(action_type, 0) + 1
        self.violations[uid_str]["actions_progress"][action_type] = progress
        save_violations(self.violations)
       
        if progress < limit:
            return 
        
        self.violations[uid_str]["actions_progress"][action_type] = 0
        self.violations[uid_str]["total_warns"] += 1
        total_warns = self.violations[uid_str]["total_warns"]
        save_violations(self.violations)

        punishment = "без наказания"
        success = False    
        try:
            if setting == "ban":
                await guild.ban(user, reason=f"Защита: Лимит {limit} для {action_type}")
                punishment = "заблокирован"
                success = True
            
            elif setting == "kick":
                await guild.kick(user, reason=f"Защита: Лимит {limit} для {action_type}")
                punishment = "кикнут"
                success = True

            elif setting == "warn":
                if total_warns == 1:
                    embed_warn = disnake.Embed(
                        title="Предупреждение системы защиты",
                        description=f"Вы превысили лимит действия: **{EVENTS.get(action_type)}**.",
                        color=disnake.Color.orange()
                    )
                    embed_warn.add_field(name="Статус", value="**[1 / 2]**", inline=True)
                    embed_warn.set_footer(text="Любое следующее превышение лимитов приведет к кику.")
                    
                    try:
                        await user.send(embed=embed_warn)
                        punishment = "[1/2]"
                    except:
                        punishment = "[1/2] (ЛС закрыты)"
                    success = True

                elif total_warns >= 2:
                    try:
                        kick_notice = disnake.Embed(
                            title="Вы были исключены",
                            description=f"Кик с сервера **{guild.name}** за повторное нарушение правил.",
                            color=disnake.Color.red()
                        )
                        await user.send(embed=kick_notice)
                    except: pass

                    await guild.kick(user, reason=f"Защита: Суммарный лимит нарушений [2/2]")
                    punishment = "кикнут (стак нарушений)"
                    
                    self.violations[uid_str] = {"total_warns": 0, "actions_progress": {}}
                    save_violations(self.violations)
                    success = True
            
            elif setting == "tempban":
                duration_min = int(setting_raw.get("duration", 60))
                until = datetime.now(timezone.utc) + timedelta(minutes=duration_min)
                
                try:
                    await user.timeout(until=until, reason=f"Защита: Лимит {limit} для {action_type}")
                    punishment = f"изоляция на {duration_min} мин."
                    success = True
                except disnake.Forbidden:
                    await guild.ban(user, reason=f"Защита: Не удалось выдать таймаут, выдан бан. Лимит {limit}")
                    punishment = "забанен (ошибка прав таймаута)"
                    success = True
            
            if message and success:
                try: await message.delete()
                except: pass

        except disnake.Forbidden:
            print(f"[ОШИБКА] Недостаточно прав для наказания {user.id}")
        
        if success:
            log_channel = guild.get_channel(PROTECTION_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = disnake.Embed(title="Сработала защита", color=Color.red())
                log_embed.add_field(name="Нарушитель", value=f"{user.mention} (`{user.id}`)")
                log_embed.add_field(name="Событие", value=EVENTS.get(action_type, action_type))
                log_embed.add_field(name="Наказание", value=punishment)
                log_embed.timestamp = datetime.now(timezone.utc)
                await log_channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: AuditLogEntry):
        await self.handle_action(entry=entry)  
     
    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot:
            return
        
        whitelist = load_whitelist()
        if message.author.guild_permissions.administrator or any(role.id == SUPPORT_ROLE_ID for role in message.author.roles):
            await self.handle_action(message=message)
            return
        
        # Анти-реклама
        if "discord.gg/" in message.content or "discord.com/invite" in message.content:
            try:
                await message.delete()
            except:
                pass
            return
        
        # Защита от пингов (обработка)
        if "@everyone" in message.content or "@here" in message.content:
            # Сразу передаем в handle_action, там идет проверка на вайтлист и лимиты
            await self.handle_action(message=message)
            # Принудительное удаление если не админ (дублируется в handle_action, но тут для гарантии)
            if not message.author.guild_permissions.administrator:
                 try: await message.delete()
                 except: pass
            return
        
        # Анти-спам (5 сообщений за 8 секунд)
        uid = message.author.id
        now = time.time()
        
        if uid not in self.user_messages:
            self.user_messages[uid] = []
        
        self.user_messages[uid] = [t for t in self.user_messages[uid] if now - t < 8]
        self.user_messages[uid].append(now)
        
        if len(self.user_messages[uid]) >= 5:
            try:
                until = datetime.now(timezone.utc) + timedelta(minutes=5)
                await message.author.timeout(until=until, reason="Пассивная защита: спам сообщениями")
                self.user_messages[uid] = []
                # Можно добавить лог
            except:
                pass
            return

def setup(bot):
    bot.add_cog(ProtectionCog(bot))
