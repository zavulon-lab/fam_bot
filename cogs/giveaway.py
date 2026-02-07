import disnake
from disnake.ext import commands, tasks
from disnake.ui import Modal, TextInput, View, Button
from disnake import Interaction, ButtonStyle, Color, Embed
from datetime import datetime, timezone
import random
import time
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List
import uuid
import asyncio

# Импорт конфига
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import (
    GIVEAWAY_USER_CHANNEL_ID,
    GIVEAWAY_ADMIN_CHANNEL_ID,
    GIVEAWAY_LOG_CHANNEL_ID,
    MAX_WINNERS
)

DB_PATH = Path("giveaway.db")

# --- DATABASE ---
def init_giveaway_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            id TEXT PRIMARY KEY,
            description TEXT,
            prize TEXT,
            sponsor TEXT,
            winner_count INTEGER,
            end_time TEXT,
            status TEXT,
            fixed_message_id INTEGER,
            participants TEXT,
            winners TEXT,
            preselected_winners TEXT,
            preselected_by INTEGER,
            preselected_at TEXT,
            finished_at TEXT,
            guild_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def load_giveaway_data() -> Optional[Dict]:
    init_giveaway_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, description, prize, sponsor, winner_count, end_time, status,
               fixed_message_id, participants, winners, preselected_winners,
               preselected_by, preselected_at, finished_at, guild_id
        FROM giveaways
        ORDER BY created_at DESC
        LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    def safe_load_list(val):
        if not val: return []
        try: return eval(val) 
        except: return []

    return {
        "id": row[0],
        "description": row[1],
        "prize": row[2],
        "sponsor": row[3],
        "winner_count": row[4],
        "end_time": row[5],
        "status": row[6],
        "fixed_message_id": row[7],
        "participants": safe_load_list(row[8]),
        "winners": safe_load_list(row[9]),
        "preselected_winners": safe_load_list(row[10]),
        "preselected_by": row[11],
        "preselected_at": row[12],
        "finished_at": row[13],
        "guild_id": row[14]
    }

def save_giveaway_data(data: Dict):
    init_giveaway_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    participants_str = str(data.get("participants", []))
    winners_str = str(data.get("winners", []))
    preselected_winners_str = str(data.get("preselected_winners", []))

    cursor.execute('''
        INSERT OR REPLACE INTO giveaways
        (id, description, prize, sponsor, winner_count, end_time, status,
         fixed_message_id, participants, winners, preselected_winners,
         preselected_by, preselected_at, finished_at, guild_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("id"),
        data.get("description"),
        data.get("prize"),
        data.get("sponsor"),
        data.get("winner_count", 1),
        data.get("end_time"),
        data.get("status", "active"),
        data.get("fixed_message_id"),
        participants_str,
        winners_str,
        preselected_winners_str,
        data.get("preselected_by"),
        data.get("preselected_at"),
        data.get("finished_at"),
        data.get("guild_id")
    ))
    conn.commit()
    conn.close()

# --- MODALS & VIEWS ---

class GiveawayPreviewView(View):
    def __init__(self, data: Dict):
        super().__init__(timeout=600)
        self.data = data

    @disnake.ui.button(label="Опубликовать", style=ButtonStyle.success, emoji="✅")
    async def confirm(self, button: Button, interaction: Interaction):
        if not self.data.get("id"):
            self.data["id"] = str(uuid.uuid4())[:8]

        save_giveaway_data(self.data)
        
        channel = interaction.guild.get_channel(GIVEAWAY_USER_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Ошибка: Канал розыгрышей не найден в конфиге.", ephemeral=True)
            return

        embed = Embed(
            title="🎉 НОВЫЙ РОЗЫГРЫШ!",
            description=self.data["description"],
            color=Color.gold()
        )
        embed.add_field(name="🎁 Приз", value=self.data["prize"], inline=True)
        embed.add_field(name="👤 Спонсор", value=self.data["sponsor"], inline=True)
        embed.add_field(name="👑 Победителей", value=str(self.data["winner_count"]), inline=True)
        
        try:
            dt = datetime.strptime(self.data["end_time"], "%Y-%m-%d %H:%M")
            ts = int(dt.timestamp())
            embed.add_field(name="⏳ Итоги", value=f"<t:{ts}:R>", inline=False)
        except:
            embed.add_field(name="⏳ Итоги", value=self.data["end_time"], inline=False)

        embed.add_field(name="👥 Участников", value="0", inline=False)
        embed.set_footer(text=f"ID: {self.data['id']}")
        
        msg = await channel.send(embed=embed, view=GiveawayJoinView(self.data["id"]))
        
        self.data["fixed_message_id"] = msg.id
        save_giveaway_data(self.data)
        
        await interaction.response.edit_message(content=f"✅ Розыгрыш опубликован! [Ссылка]({msg.jump_url})", view=None, embed=None)

    @disnake.ui.button(label="Отмена", style=ButtonStyle.danger, emoji="❌")
    async def cancel(self, button: Button, interaction: Interaction):
        await interaction.response.edit_message(content="❌ Создание отменено.", view=None, embed=None)


class GiveawayEditModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Описание", custom_id="desc", style=disnake.TextInputStyle.paragraph, placeholder="Условия участия...", required=True),
            TextInput(label="Приз", custom_id="prize", placeholder="Например: 500 рублей", required=True),
            TextInput(label="Спонсор", custom_id="sponsor", placeholder="Ник спонсора", required=True),
            TextInput(label="Количество победителей", custom_id="winners", value="1", required=True),
            TextInput(label="Время окончания", custom_id="end_time", placeholder="YYYY-MM-DD HH:MM", required=True)
        ]
        super().__init__(title="Настройка розыгрыша", components=components)

    async def callback(self, interaction: Interaction):
        try:
            w_count = int(interaction.text_values["winners"])
            if w_count < 1 or w_count > MAX_WINNERS:
                raise ValueError
            end_dt = datetime.strptime(interaction.text_values["end_time"], "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(f"❌ Ошибка данных! Проверьте число победителей и формат даты.", ephemeral=True)
            return

        temp_data = {
            "id": str(uuid.uuid4())[:8],
            "description": interaction.text_values["desc"],
            "prize": interaction.text_values["prize"],
            "sponsor": interaction.text_values["sponsor"],
            "winner_count": w_count,
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
            "participants": [],
            "status": "active",
            "guild_id": interaction.guild.id
        }

        preview_embed = Embed(
            title="Предпросмотр розыгрыша",
            description=temp_data["description"],
            color=Color.from_rgb(54, 57, 63)
        )
        preview_embed.add_field(name="🎁 Приз", value=temp_data["prize"], inline=True)
        preview_embed.add_field(name="👤 Спонсор", value=temp_data["sponsor"], inline=True)
        preview_embed.add_field(name="⏳ Окончание", value=temp_data["end_time"], inline=False)
        
        await interaction.response.send_message(embed=preview_embed, view=GiveawayPreviewView(temp_data), ephemeral=True)


class WinnerSelectModal(Modal):
    def __init__(self):
        components = [
            TextInput(
                label="ID победителей",
                custom_id="winners",
                placeholder="123456789, 987654321...",
                style=disnake.TextInputStyle.paragraph,
                required=True
            )
        ]
        super().__init__(title="Выбор победителей", components=components)

    async def callback(self, interaction: Interaction):
        data = load_giveaway_data()
        if not data or data.get("status") != "active":
            await interaction.response.send_message("❌ Нет активного розыгрыша.", ephemeral=True)
            return

        try:
            input_text = interaction.text_values["winners"].replace(",", " ").split()
            winner_ids = [int(x) for x in input_text]
        except ValueError:
            await interaction.response.send_message("❌ Ошибка: Введите корректные числовые ID.", ephemeral=True)
            return

        target_count = data.get("winner_count", 1)
        if len(winner_ids) != target_count:
            await interaction.response.send_message(
                f"⚠️ Нужно указать ровно **{target_count}** ID (вы указали {len(winner_ids)}).", 
                ephemeral=True
            )
            return

        guild = interaction.guild
        mentions = []
        for uid in winner_ids:
            u = guild.get_member(uid)
            mentions.append(u.mention if u else f"ID {uid}")

        log_chan = guild.get_channel(GIVEAWAY_LOG_CHANNEL_ID)
        if log_chan:
            emb = Embed(
                title="Ручной выбор победителей",
                description=f"Администратор {interaction.user.mention} выбрал победителей:\n" + ", ".join(mentions),
                color=Color.orange()
            )
            await log_chan.send(embed=emb)

        data["preselected_winners"] = winner_ids
        data["preselected_by"] = interaction.user.id
        data["preselected_at"] = datetime.now(timezone.utc).isoformat()
        save_giveaway_data(data)
        
        await interaction.response.send_message("✅ Победители зафиксированы.", ephemeral=True)


class GiveawayJoinView(View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @disnake.ui.button(label="Участвовать", style=ButtonStyle.success, emoji="🎉", custom_id="btn_join_giveaway")
    async def join(self, button: Button, interaction: Interaction):
        data = load_giveaway_data()
        
        if not data or str(data.get("id")) != str(self.giveaway_id) or data.get("status") != "active":
            await interaction.response.send_message("❌ Этот розыгрыш уже завершен.", ephemeral=True)
            return

        uid = interaction.user.id
        participants = data.get("participants", [])
        
        if uid in participants:
            participants.remove(uid)
            msg = "📤 Вы больше не участвуете."
        else:
            participants.append(uid)
            msg = "✅ Вы участвуете в розыгрыше!"
        
        data["participants"] = participants
        save_giveaway_data(data)

        try:
            embed = interaction.message.embeds[0]
            for i, f in enumerate(embed.fields):
                if "Участников" in f.name:
                    embed.set_field_at(i, name=f.name, value=str(len(participants)), inline=False)
                    break
            await interaction.message.edit(embed=embed)
        except:
            pass
            
        await interaction.response.send_message(msg, ephemeral=True)


class GiveawayAdminPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Создать розыгрыш", style=ButtonStyle.primary, emoji="➕", custom_id="adm_gw_create")
    async def create(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(GiveawayEditModal())

    @disnake.ui.button(label="Завершить текущий", style=ButtonStyle.danger, emoji="⏹️", custom_id="adm_gw_stop")
    async def stop(self, button: Button, interaction: Interaction):
        data = load_giveaway_data()
        if not data or data["status"] != "active":
            await interaction.response.send_message("❌ Нет активных розыгрышей.", ephemeral=True)
            return
        
        cog = interaction.bot.get_cog("GiveawayCog")
        if cog:
            await cog.finish_giveaway(data, interaction.guild)
            await interaction.response.send_message("✅ Розыгрыш принудительно завершен.", ephemeral=True)

    @disnake.ui.button(label="Выбрать победителей", style=ButtonStyle.secondary, emoji="👑", custom_id="adm_gw_pick")
    async def pick(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(WinnerSelectModal())


class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_giveaway_db()
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        """Автоматическая отправка панели при запуске"""
        try:
            channel = self.bot.get_channel(GIVEAWAY_ADMIN_CHANNEL_ID)
            if channel:
                # Очищаем старые сообщения (чтобы панель была одна)
                try:
                    await channel.purge(limit=10)
                except Exception as e:
                    print(f"[GIVEAWAY] Ошибка очистки канала админки: {e}")

                embed = Embed(
                    title="🎁 Управление розыгрышами",
                    description=(
                        "Здесь вы можете создавать и завершать розыгрыши.\n"
                        "Все действия выполняются через кнопки ниже."
                    ),
                    color=Color.blurple()
                )
                # Отправляем новую панель
                await channel.send(embed=embed, view=GiveawayAdminPanel())
                print(f"[GIVEAWAY] Панель управления отправлена в канал {GIVEAWAY_ADMIN_CHANNEL_ID}")
            else:
                print(f"[GIVEAWAY] Ошибка: Канал {GIVEAWAY_ADMIN_CHANNEL_ID} не найден.")
        except Exception as e:
            print(f"[GIVEAWAY] Ошибка при отправке панели: {e}")

    @tasks.loop(minutes=1)
    async def check_giveaways(self):
        data = load_giveaway_data()
        if not data or data["status"] != "active": return
        
        try:
            end_dt = datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M")
            if datetime.now() >= end_dt:
                guild = self.bot.get_guild(data["guild_id"])
                if guild:
                    await self.finish_giveaway(data, guild)
        except Exception as e:
            print(f"[GIVEAWAY] Timer error: {e}")

    async def finish_giveaway(self, data, guild):
        participants = data.get("participants", [])
        count = data.get("winner_count", 1)
        preselected = data.get("preselected_winners", [])
        
        winners = []
        for uid in preselected:
            if uid not in winners: winners.append(uid)
        
        needed = count - len(winners)
        if needed > 0:
            pool = [p for p in participants if p not in winners]
            if len(pool) >= needed:
                winners.extend(random.sample(pool, needed))
            else:
                winners.extend(pool)

        data["status"] = "finished"
        data["winners"] = winners
        data["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_giveaway_data(data)

        try:
            chan = guild.get_channel(GIVEAWAY_USER_CHANNEL_ID)
            if chan and data.get("fixed_message_id"):
                msg = await chan.fetch_message(data["fixed_message_id"])
                embed = msg.embeds[0]
                embed.title = "🎉 РОЗЫГРЫШ ЗАВЕРШЕН"
                embed.color = Color.greyple()
                
                w_list = ", ".join([f"<@{uid}>" for uid in winners]) if winners else "Нет победителей"
                embed.add_field(name="🏆 Победители", value=w_list, inline=False)
                
                await msg.edit(embed=embed, view=None)
                if winners:
                    await chan.send(f"🎉 Поздравляем победителей: {w_list}!")
        except:
            pass

        log_chan = guild.get_channel(GIVEAWAY_LOG_CHANNEL_ID)
        if log_chan:
            emb = Embed(title="Итоги розыгрыша", color=Color.green(), timestamp=datetime.now())
            emb.add_field(name="Приз", value=data["prize"])
            emb.add_field(name="Победители", value=", ".join([str(u) for u in winners]))
            emb.add_field(name="Участников", value=str(len(participants)))
            await log_chan.send(embed=emb)

def setup(bot):
    bot.add_cog(GiveawayCog(bot))
