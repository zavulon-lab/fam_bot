import os
import json
import sqlite3
import logging
from typing import Optional, Dict, List
from contextlib import contextmanager


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


DB_PATH = "bot_data.db"


@contextmanager
def get_db_connection():
    """Контекстный менеджер для работы с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при работе с БД: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Инициализация базы данных"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица для личных каналов пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS private_channels (
                user_id TEXT PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица для созданных каналов (для отката)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS created_channels (
                channel_id INTEGER PRIMARY KEY,
                creator_id INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица: Настройки формы заявок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_form_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_data TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица для отпусков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacations (
                user_id TEXT PRIMARY KEY,
                roles_data TEXT,
                start_date TEXT,
                end_date TEXT,
                reason TEXT
            )
        ''')
        
        # --- НОВАЯ ТАБЛИЦА ДЛЯ РОЗЫГРЫШЕЙ ---
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
                thumbnail_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # --- Миграция: добавляем недостающие колонки ---
        cursor.execute("PRAGMA table_info(giveaways)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        if "thumbnail_url" not in existing_cols:
            cursor.execute("ALTER TABLE giveaways ADD COLUMN thumbnail_url TEXT")
            logger.info("Добавлена колонка thumbnail_url в таблицу giveaways")
        
        logger.info("База данных инициализирована")


# ========== ЛИЧНЫЕ КАНАЛЫ ==========


def get_private_channel(user_id: str) -> Optional[int]:
    """Получить ID личного канала пользователя"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id FROM private_channels WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result['channel_id'] if result else None


def set_private_channel(user_id: str, channel_id: int):
    """Сохранить ID личного канала пользователя"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO private_channels (user_id, channel_id) VALUES (?, ?)",
            (user_id, channel_id)
        )
        logger.info(f"Личный канал {channel_id} установлен для пользователя {user_id}")


# ========== СОЗДАННЫЕ КАНАЛЫ (ОТКАТЫ) ==========


def add_created_channel(channel_id: int, creator_id: int, channel_name: str):
    """Добавить созданный канал в БД"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO created_channels (channel_id, creator_id, channel_name) VALUES (?, ?, ?)",
            (channel_id, creator_id, channel_name)
        )
        logger.info(f"Канал {channel_name} (ID: {channel_id}) добавлен в БД")


def delete_created_channel(channel_id: int):
    """Удалить канал из БД"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM created_channels WHERE channel_id = ?", (channel_id,))
        logger.info(f"Канал {channel_id} удалён из БД")


def channel_exists(channel_id: int) -> bool:
    """Проверить существование канала в БД"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM created_channels WHERE channel_id = ?", (channel_id,))
        return cursor.fetchone() is not None


# ========== ФОРМА ЗАЯВОК ==========


def save_application_form(form_fields: List[Dict]):
    """Сохранить конфигурацию формы заявки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        form_json = json.dumps(form_fields, ensure_ascii=False)
        
        cursor.execute("DELETE FROM application_form_config")
        cursor.execute(
            "INSERT INTO application_form_config (form_data, updated_at) VALUES (?, CURRENT_TIMESTAMP)",
            (form_json,)
        )
        logger.info(f"Конфигурация формы заявки сохранена: {len(form_fields)} полей")


def get_application_form() -> List[Dict]:
    """Получить конфигурацию формы заявки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT form_data FROM application_form_config ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            return json.loads(result['form_data'])
        else:
            return get_default_application_form()


def get_default_application_form() -> List[Dict]:
    """Получить дефолтную конфигурацию формы"""
    return [
        {
            "type": "text_input",
            "label": "Ник | Статик | Имя и возраст",
            "custom_id": "name_static_age",
            "style": "short",
            "required": True,
            "placeholder": "Введите ваш ник, статик и имя с возрастом",
            "min_length": None,
            "max_length": None,
            "options": []
        },
        {
            "type": "text_input",
            "label": "Прошлые семьи",
            "custom_id": "past_families",
            "style": "paragraph",
            "required": True,
            "placeholder": "Перечислите ваши прошлые семьи",
            "min_length": None,
            "max_length": None,
            "options": []
        },
        {
            "type": "text_input",
            "label": "Откаты с ГГ и мероприятий",
            "custom_id": "gt_rollbacks",
            "style": "paragraph",
            "required": True,
            "placeholder": "Отправьте ссылки на ваши откаты с ГГ или МП",
            "min_length": None,
            "max_length": None,
            "options": []
        },
        {
            "type": "text_input",
            "label": "Цель вступления",
            "custom_id": "goal",
            "style": "paragraph",
            "required": True,
            "placeholder": "Расскажите, зачем хотите вступить",
            "min_length": None,
            "max_length": None,
            "options": []
        },
        {
            "type": "text_input",
            "label": "Откуда узнал о нас",
            "custom_id": "how_found",
            "style": "short",
            "required": True,
            "placeholder": "Откуда вы о нас узнали?",
            "min_length": None,
            "max_length": None,
            "options": []
        }
    ]


# ========== ОТПУСКА ==========


def save_vacation_data(user_id, roles_list, start_date, end_date, reason):
    """Сохранить данные об отпуске и ролях"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        roles_json = json.dumps(roles_list)
        cursor.execute('''
            INSERT OR REPLACE INTO vacations (user_id, roles_data, start_date, end_date, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, roles_json, start_date, end_date, reason))
        logger.info(f"Отпуск для {user_id} сохранен.")


def get_vacation_data(user_id):
    """Получить сохраненные роли пользователя в отпуске"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT roles_data FROM vacations WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
    if result:
        return json.loads(result['roles_data'])
    return None


def delete_vacation_data(user_id):
    """Удалить данные об отпуске (пользователь вернулся)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM vacations WHERE user_id = ?', (user_id,))
        logger.info(f"Отпуск для {user_id} удален из БД.")


# ========== РОЗЫГРЫШИ ==========


def load_giveaway_data() -> Optional[Dict]:
    """Получить последний активный розыгрыш"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, description, prize, sponsor, winner_count, end_time, status,
                   fixed_message_id, participants, winners, preselected_winners,
                   preselected_by, preselected_at, finished_at, guild_id, thumbnail_url
            FROM giveaways
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        row = cursor.fetchone()


    if not row:
        return None


    def safe_load_list(val):
        if not val: return []
        try: return eval(val) 
        except: return []


    return {
        "id": row['id'],
        "description": row['description'],
        "prize": row['prize'],
        "sponsor": row['sponsor'],
        "winner_count": row['winner_count'],
        "end_time": row['end_time'],
        "status": row['status'],
        "fixed_message_id": row['fixed_message_id'],
        "participants": safe_load_list(row['participants']),
        "winners": safe_load_list(row['winners']),
        "preselected_winners": safe_load_list(row['preselected_winners']),
        "preselected_by": row['preselected_by'],
        "preselected_at": row['preselected_at'],
        "finished_at": row['finished_at'],
        "guild_id": row['guild_id'],
        "thumbnail_url": row['thumbnail_url']
    }


def save_giveaway_data(data: Dict):
    """Сохранить или обновить данные розыгрыша"""
    with get_db_connection() as conn:
        cursor = conn.cursor()


        participants_str = str(data.get("participants", []))
        winners_str = str(data.get("winners", []))
        preselected_winners_str = str(data.get("preselected_winners", []))


        cursor.execute('''
            INSERT OR REPLACE INTO giveaways
            (id, description, prize, sponsor, winner_count, end_time, status,
             fixed_message_id, participants, winners, preselected_winners,
             preselected_by, preselected_at, finished_at, guild_id, thumbnail_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get("guild_id"),
            data.get("thumbnail_url")
        ))
        logger.info(f"Розыгрыш {data.get('id')} сохранён")


# ========== СТАТУС ЗАЯВОК ==========


STATUS_FILE = "applications_status.json"


def get_applications_status():
    """Возвращает True, если набор открыт, False если закрыт."""
    if not os.path.exists(STATUS_FILE):
        set_applications_status(True)
        return True
        
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("enabled", True)
    except Exception as e:
        print(f"[Database Error] Не удалось прочитать статус заявок: {e}")
        return True


def set_applications_status(enabled: bool):
    """Сохраняет статус набора (True/False)."""
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"enabled": enabled}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[Database Error] Не удалось сохранить статус заявок: {e}")


# Инициализация БД при импорте модуля
init_db()
