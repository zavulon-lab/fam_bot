import disnake
import time
from disnake.ext import commands
from datetime import datetime, timezone

# Импортируем конфиг
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import (
    LOG_MESSAGES_CHANNEL_ID,
    LOG_VOICE_CHANNEL_ID,
    LOG_ROLES_CHANNEL_ID,
    LOG_NICKNAMES_CHANNEL_ID,
    LOG_MODERATION_CHANNEL_ID
)

class UserLogsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_log(self, channel_id: int, embed: disnake.Embed):
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if channel and isinstance(channel, disnake.TextChannel):
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"[USER_LOGS] Ошибка отправки в канал {channel_id}: {e}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        if message.author.bot: return
        
        embed = disnake.Embed(
            description=f"<:freeicondelete3625005:1472679616589205604> **Сообщение удалено**",
            color=disnake.Color.red()
        )
        info_value = (
            f"Участник: {message.author.mention}\n"
            f"<:freeiconteam2763403:1472654736489451581> login: {message.author.name}\n"
            f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {message.author.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        
        channel_value = (
            f"<:link:1472654744316018843> Канал: {message.channel.mention}\n"
            f"<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
        )
        embed.add_field(name="Детали", value=channel_value, inline=True)
        embed.add_field(name="Содержимое", value=message.content or "Контент отсутствует (возможно файл)", inline=False)
        
        if message.attachments:
            embed.add_field(name="Вложения", value="\n".join(a.url for a in message.attachments), inline=False)
            
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {message.author.id}")
        
        await self.send_log(LOG_MESSAGES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if before.author.bot or before.content == after.content: return
        
        embed = disnake.Embed(
            description=f"<:freeiconedit1040228:1472654696891158549> **Сообщение изменено**",
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        info_value = (
            f"Участник: {before.author.mention}\n"
            f"<:freeiconteam2763403:1472654736489451581> login: {before.author.name}\n"
            f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {before.author.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        
        channel_value = (
            f"<:link:1472654744316018843> Канал: {before.channel.mention}\n"
            f"<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
        )
        embed.add_field(name="Детали", value=channel_value, inline=True)
        
        embed.add_field(name="Было", value=(before.content[:1000] + "...") if len(before.content) > 1000 else (before.content or "Пусто"), inline=False)
        embed.add_field(name="Стало", value=(after.content[:1000] + "...") if len(after.content) > 1000 else (after.content or "Пусто"), inline=False)
        
        embed.set_thumbnail(url=before.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {before.author.id}")
        
        await self.send_log(LOG_MESSAGES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if before.channel == after.channel: return
        
        embed = disnake.Embed()
        info_value = (
            f"Участник: {member.mention}\n"
            f"<:freeiconteam2763403:1472654736489451581> login: {member.name}\n"
            f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {member.id}"
        )
        
        if before.channel is None:
            embed.description = f"<:1_:1472942174977917105> **Подключение к голосовому каналу**"
            embed.color = disnake.Color.green()
            channel_info = f"Канал: {after.channel.name}\n<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
            
        elif after.channel is None:
            embed.description = f"<:2_:1472654669674184716> **Отключение от голосового канала**"
            embed.color = disnake.Color.red()
            channel_info = f"Канал: {before.channel.name}\n<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
            
        else:
            embed.description = f"<:freeiconexchange1372789:1472654701643436113> **Перемещение между каналами**"
            embed.color = disnake.Color.from_rgb(54, 57, 63)
            channel_info = f"{before.channel.name} → {after.channel.name}\n<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"

        embed.add_field(name="Информация", value=info_value, inline=True)
        embed.add_field(name="Детали", value=channel_info, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_log(LOG_VOICE_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        # Никнейм
        if before.display_name != after.display_name:
            embed = disnake.Embed(
                description=f"<:freeiconadd2013845:1472654674976051200> **Изменение никнейма**",
                color=disnake.Color.from_rgb(54, 57, 63)
            )
            info_value = (
                f"Участник: {after.mention}\n"
                f"<:freeiconteam2763403:1472654736489451581> login: {after.name}\n"
                f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {after.id}"
            )
            embed.add_field(name="Информация", value=info_value, inline=True)
            change_value = (
                f"**Было:** {before.display_name}\n"
                f"**Стало:** {after.display_name}\n"
                f"<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
            )
            embed.add_field(name="Изменения", value=change_value, inline=True)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"User ID: {after.id}")
            
            await self.send_log(LOG_NICKNAMES_CHANNEL_ID, embed)

        # Роли
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            
            if added or removed:
                embed = disnake.Embed(
                    description=f"<:freeiconshield473701:1472654728801423635> **Обновление ролей**",
                    color=disnake.Color.from_rgb(54, 57, 63)
                )
                info_value = (
                    f"Участник: {after.mention}\n"
                    f"<:freeiconteam2763403:1472654736489451581> login: {after.name}\n"
                    f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {after.id}"
                )
                embed.add_field(name="Информация", value=info_value, inline=True)
                
                moderator_value = "Не найден"
                # Пытаемся найти модератора через аудит
                async for entry in after.guild.audit_logs(limit=5, action=disnake.AuditLogAction.member_role_update):
                    if entry.target.id == after.id and (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                        moderator_value = f"{entry.user.mention}"
                        break
                        
                embed.add_field(name="Модератор", value=moderator_value, inline=True)
                embed.add_field(name="Время", value=f"<t:{int(time.time())}:R>", inline=True)
                
                if added:
                    embed.add_field(name="<:freeiconplus1828819:1472681225935392858> Выданы", value=", ".join(r.mention for r in added), inline=False)
                if removed:
                    embed.add_field(name="<:freeiconminus10263924:1472681399512334409> Сняты", value=", ".join(r.mention for r in removed), inline=False)
                
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.send_log(LOG_ROLES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        now = datetime.now(timezone.utc)
        diff = now - member.created_at
        years = diff.days // 365
        days = diff.days % 365
        age_str = f"**{years} лет, {days} дней**" if years > 0 else f"**{days} дней**"
        
        embed = disnake.Embed(
            description=f"<:1_:1472942174977917105> {member.mention} присоединился в Discord сервер",
            color=disnake.Color.green()
        )
        info_value = (
            f"Участник: {member.mention}\n"
            f"<:freeiconteam2763403:1472654736489451581> login: {member.name}\n"
            f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {member.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        embed.add_field(
            name="Возраст аккаунта",
            value=f"<:freeiconclock12476999:1472654689815232834> {age_str}",
            inline=True
        )
        embed.set_footer(text=f"Количество участников: {member.guild.member_count}")
        
        await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        now = datetime.now(timezone.utc)
        diff = now - member.created_at
        years = diff.days // 365
        days = diff.days % 365
        age_str = f"**{years} лет, {days} дней**" if years > 0 else f"**{days} дней**"
        
        # Проверяем аудит на кик
        kicked = False
        async for entry in member.guild.audit_logs(limit=5, action=disnake.AuditLogAction.kick):
            if entry.target.id == member.id and (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 5:
                embed = disnake.Embed(
                    description=f"<:cross:1472654174788255996> **Исключение пользователя (Кик)**",
                    color=disnake.Color.red()
                )
                info_value = (
                    f"Участник: {member.mention}\n"
                    f"<:freeiconteam2763403:1472654736489451581> login: {member.name}\n"
                    f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {member.id}"
                )
                embed.add_field(name="Информация", value=info_value, inline=True)
                moderator_value = (
                    f"Модератор: {entry.user.mention}\n"
                    f"<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
                )
                embed.add_field(name="Детали", value=moderator_value, inline=True)
                embed.set_footer(text=f"User ID: {member.id}")
                
                await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)
                kicked = True
                break
        
        if not kicked:
            embed = disnake.Embed(
                description=f"<:2_:1472654669674184716> {member.mention} вышел с Discord сервера",
                color=disnake.Color.red()
            )
            info_value = (
                f"Участник: {member.mention}\n"
                f"<:freeiconteam2763403:1472654736489451581> login: {member.name}\n"
                f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {member.id}"
            )
            embed.add_field(name="Информация", value=info_value, inline=True)
            embed.add_field(
                name="Возраст аккаунта",
                value=f"<:freeiconclock12476999:1472654689815232834> {age_str}",
                inline=True
            )
            embed.set_footer(text=f"Количество участников: {member.guild.member_count}")
            
            await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: disnake.Role):
        embed = disnake.Embed(
            description=f"<:freeiconplus1828819:1472681225935392858> **Создана роль**",
            color=disnake.Color.green()
        )
        info_value = (
            f"**Название:** {role.name}\n"
            f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {role.id}\n"
            f"<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
        )
        embed.add_field(name="Информация", value=info_value, inline=False)
        perms = role.permissions
        embed.add_field(
            name="<:freeiconshield473701:1472654728801423635> Полномочия",
            value=(
                f"Администратор: {'✅' if perms.administrator else '❌'}\n"
                f"Управление сервером: {'✅' if perms.manage_guild else '❌'}\n"
                f"Управление ролями: {'✅' if perms.manage_roles else '❌'}"
            ),
            inline=False
        )
        await self.send_log(LOG_ROLES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        embed = disnake.Embed(
            description=f"<:freeiconminus10263924:1472681399512334409> **Удалена роль**",
            color=disnake.Color.red()
        )
        info_value = (
            f"**Название:** {role.name}\n"
            f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {role.id}\n"
            f"<:freeiconclock12476999:1472654689815232834> Время: <t:{int(time.time())}:R>"
        )
        embed.add_field(name="Информация", value=info_value, inline=False)
        embed.set_footer(text=f"Role ID: {role.id}")
        await self.send_log(LOG_ROLES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, user: disnake.User):
        embed = disnake.Embed(
            description=f"<:ban:1472654052763500584> **Блокировка пользователя**",
            color=disnake.Color.dark_red()
        )
        info_value = (
            f"Участник: {user.mention}\n"
            f"<:freeiconteam2763403:1472654736489451581> login: {user.name}\n"
            f"<:freeiconbusinesscard10584954:1472654680403349719> ID: {user.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        embed.add_field(name="Время", value=f"<:freeiconclock12476999:1472654689815232834> <t:{int(time.time())}:R>", inline=True)
        
        # Пытаемся найти причину и модератора
        async for entry in guild.audit_logs(limit=5, action=disnake.AuditLogAction.ban):
            if entry.target.id == user.id:
                 embed.add_field(name="Модератор", value=entry.user.mention, inline=True)
                 embed.add_field(name="Причина", value=entry.reason or "Не указана", inline=False)
                 break
                 
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)

def setup(bot: commands.Bot):
    bot.add_cog(UserLogsCog(bot))
