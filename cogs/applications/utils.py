"""Вспомогательные функции для модуля заявок"""
import disnake
import re
from disnake import Embed, CategoryChannel, HTTPException
from datetime import datetime
from constants import CATEGORY_ID, PRIVATE_THREAD_ROLE_ID
from database import set_private_channel, get_private_channel


def generate_custom_id(label: str) -> str:
    """Автоматически генерирует ID из названия поля"""
    clean_label = re.sub(r'[^a-zA-Zа-яА-Я0-9\s]', '', label)
    custom_id = clean_label.lower().replace(' ', '_')
    
    if not custom_id:
        custom_id = f"field_{int(datetime.now().timestamp())}"
    
    return custom_id[:40]


def migrate_old_form_data(form_config: list) -> list:
    """Добавляет поле 'type' к старым записям без него"""
    migrated = []
    for field in form_config:
        if "type" not in field:
            if "options" in field and len(field.get("options", [])) > 0:
                field["type"] = "select_menu"
            else:
                field["type"] = "text_input"
                if "options" not in field:
                    field["options"] = []
        migrated.append(field)
    return migrated


def extract_user_id_from_embed(embed: Embed) -> int | None:
    """Извлекает ID пользователя из эмбеда заявки"""
    # 1. Сначала ищем в поле "Информация об аккаунте" или похожих
    for field in embed.fields:
        if "ID" in field.value or "Информация" in field.name:
            # Ищем последовательность из 17-20 цифр
            match = re.search(r'`(\d{17,20})`', field.value)
            if match:
                return int(match.group(1))
            # Если без кавычек
            match = re.search(r'ID:.*?(\d{17,20})', field.value)
            if match:
                return int(match.group(1))

    # 2. Если не нашли, ищем просто по всему тексту эмбеда (резервный вариант)
    # Собираем весь текст
    full_text = (embed.description or "") + " "
    for f in embed.fields:
        full_text += f.value + " "
    
    # Ищем ID пользователя (обычно это user.id)
    # Это может быть рискованно, если в тексте есть другие длинные числа, но для заявки пойдет
    matches = re.findall(r'`?(\d{17,20})`?', full_text)
    if matches:
        return int(matches[0])
        
    return None



async def create_personal_file(guild, member, curator):
    """Создает личное дело (канал) для участника с правами для куратора"""
    try:
        category = guild.get_channel(CATEGORY_ID)
        if not category or not isinstance(category, CategoryChannel):
            print(f"[PersonalFile] Категория {CATEGORY_ID} не найдена")
            return None

        # Логика с лимитом 50 каналов
        if len(category.channels) >= 50:
            category_name_base = category.name
            new_category = None
            category_index = 1

            for cat in guild.categories:
                if cat.name.startswith(category_name_base) and len(cat.channels) < 50:
                    new_category = cat
                    break

            if not new_category:
                while True:
                    new_category_name = f"{category_name_base} {category_index}" if category_index > 1 else category_name_base
                    try:
                        new_category = await guild.create_category(
                            name=new_category_name, reason="Достигнут лимит каналов в категории (50)"
                        )
                        for target, permission_overwrite in category.overwrites.items():
                            await new_category.set_permissions(target, overwrite=permission_overwrite)
                        break
                    except HTTPException as http_err:
                        if http_err.code == 50035 and "Maximum number" in str(http_err):
                            category_index += 1
                            continue
                        elif http_err.code == 50035 and "Guild has reached" in str(http_err):
                            print("[PersonalFile] Сервер достиг лимита каналов!")
                            return None
                        raise
            
            category = new_category

        # Проверяем, есть ли уже канал в БД
        existing_channel_id = get_private_channel(str(member.id))
        if existing_channel_id:
            existing_channel = guild.get_channel(existing_channel_id)
            if existing_channel:
                return existing_channel

        # Создаем канал
        channel_name = member.display_name.lower().replace(" ", "-")
        
        personal_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            reason=f"Создание личного дела для {member.display_name}"
        )

        # Настраиваем права
        await personal_channel.set_permissions(guild.default_role, view_channel=False)
        await personal_channel.set_permissions(member, view_channel=True, send_messages=True)
        await personal_channel.set_permissions(curator, view_channel=True, send_messages=True)
        
        role = guild.get_role(PRIVATE_THREAD_ROLE_ID)
        if role:
            await personal_channel.set_permissions(role, view_channel=True)

        # Сохраняем в БД
        set_private_channel(str(member.id), personal_channel.id)
        
        # Приветственное сообщение
        embed = Embed(
            title="<:freeiconopenfolder12075402:1472674638239633590> Личный портфель",
            description=(
                f"**Владелец:** {member.mention}\n"
                f"**Куратор:** {curator.mention}\n"
                f"**Дата создания:** {datetime.now().strftime('%d.%m.%Y')}"
            ),
            color=disnake.Color.from_rgb(54, 57, 63)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await personal_channel.send(f"{member.mention}", embed=embed)

        return personal_channel

    except Exception as e:
        print(f"[PersonalFile] Ошибка при создании: {e}")
        import traceback
        traceback.print_exc()
        return None
