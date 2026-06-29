#!/usr/bin/env python3
"""
Spark AI Creator — standalone Telegram bot (white KP).

Run:
  cp .env.example .env   # set BOT_TOKEN in .env
  python bot.py

Optional env:
  STARS_PER_USD=50   — how many Telegram Stars equal $1 on balance
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("spark")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
STARS_PER_USD = int(os.environ.get("STARS_PER_USD", "50"))

# ── KP texts ────────────────────────────────────────────────────────────────

RULES_TEXT = (
    "Spark AI Creator — топовый бот с нейросетями для создания, улучшения "
    "и редактирования изображений и видео — всё что нужно в одном месте!\n\n"
    "🚀 Нажми Старт и другие боты больше не понадобятся!"
)

WELCOME_TEXT = (
    "<b>👋 Добро пожаловать!</b> Спасибо что заглянул!\n\n"
    "<b>Наш бот — это агрегатор нейросетей, который создан для тех, кто хочет "
    "использовать лучшие нейросети в одном месте и не хочет оплачивать "
    "ежемесячные подписки.</b>\n\n"
    "<b>Здесь вы можете создавать, улучшать и редактировать изображения или видео</b> — "
    "всё что нужно в одном месте! 🚀\n\n"
    "Вы можете пополнить внутренний счёт бота на любую сумму, активировать и "
    "использовать нужный инструмент, и после получения результата оплата будет "
    "списана со счёта. У бота нет бесплатного функционала, поэтому мы можем "
    "предложить самые низкие цены.\n\n"
    "<b>Выберите функцию ниже 👇</b>"
)

PHOTO_MENU_TEXT = (
    "🌄 <b>Выберите тип нейросетей для работы с фотографиями и изображениями:</b>\n\n"
    "🎨 <b>Создание</b> — для создания изображений на основе задания или задания "
    "и предоставленных изображений.\n\n"
    "📷 <b>Улучшение</b> — для улучшения и восстановления качества изображений.\n\n"
    "🖌️ <b>Изменение</b> — нейросети для изменения изображений (нейрофотошоп, "
    "ретушь, удаление/замена фона и объектов, изменение стиля, дизайн интерьера и т.д.)"
)

PHOTO_CREATE_TEXT = (
    "<b>Выберите генератор изображений с которым хотите работать.</b>\n\n"
    "❓ <b>Если вы не знаете какой выбрать:</b>\n\n"
    "<b>4o Image</b> — способен отлично генерировать изображения с русским текстом, "
    "принимает не только текстовые описания, но может принять до 5 изображений "
    "и на основе них создавать изображения по вашим заданиям. Работает в формате "
    "диалога с ботом.\n"
    "<b>Midjourney</b> — хороший вариант по соотношению цена/качество, создающий "
    "сразу 4 изображения с возможностью выбора и получения одного в улучшенном качестве.\n"
    "<b>Flux1.1Pro Ultra</b> — лучшее качество при высоком разрешении.\n"
    "<b>Recraft V3</b> — входит в тройку лидеров по тестам.\n\n"
    "⚠️ Внимание! Почти все генераторы используют автоматическую модерацию "
    "контента. Если ваше задание или изображение содержит неприемлемый контент "
    "(насилие, жестокость, нагота, эротика, материалы под авторским правом, "
    "логотипы брендов, известных персонажей или людей, дискриминационный контент, "
    "наркотики, оружие, политические деятели и символика), генератор вернёт чёрное "
    "изображение, а оплата будет списана без возможности возврата."
)

PHOTO_CREATE_ACTIVE = (
    "<b>Генератор изображений активирован. Можете отправлять задания на создание "
    "изображений.</b>\n\n"
    "Задания могут содержать любые параметры, которые есть у этого генератора "
    "изображений (например формат изображения)."
)

PHOTO_ENHANCE_MENU = (
    "<b>Выберите инструмент для улучшения фото или изображения, который вам нужен, "
    "и после его активации все отправляемые фото будут обработаны этим инструментом.</b>"
)

PHOTO_ENHANCE_ACTIVE = (
    "<b>Выбранный способ работы с фотографиями активирован.</b> Теперь вы можете загружать "
    "фотографии в форматах jpeg, jpg, png, heic и размером не более 20 мб."
)

PHOTO_MODIFY_MENU = (
    "<b>Выберите способ изменения фотографий и изображений, который вам нужен, "
    "и после его активации все отправляемые изображения будут обработаны этим способом.</b>"
)

PHOTO_MODIFY_ACTIVE = (
    "<b>Выбранный способ работы с фотографиями активирован.</b> Теперь вы можете загружать "
    "фотографии в форматах jpeg, jpg, png, heic и размером не более 20 мб."
)

VIDEO_MENU_TEXT = (
    "🎬<b> Выберите тип нейросети, с которой хотите работать.</b> Мы предлагаем все "
    "топовые генераторы видео и инструменты, которые делятся на несколько категорий:\n\n"
    "🖼️ <b>Видео из изображений</b> — создают видео из фотографий (или картинок) + "
    "описания того, что вы хотите видеть на видео.\n\n"
    "📝 <b>Видео из текста</b> — создают видео только из текстового описания.\n\n"
    "📹 <b>Улучшить качество</b> — улучшают качество видео до заданного разрешения и FPS."
)

VIDEO_IMG2VID_MENU = (
    "🎬 <b>Выберите генератор видео нажав на одну из кнопок в меню ниже.</b>\n\n"
    "🖼️ Видео из изображений — этот тип генераторов создаёт видео из "
    "фотографий и картинок. Вам необходимо отправить фотографию или картинку как "
    "файл и в подписи к этому файлу указать, что вы хотите, чтобы происходило на "
    "видео. Примеры: девушка улыбается и машет рукой, мужчина и женщина обнимаются "
    "и целуются, футболист забивает мяч в ворота."
)

VIDEO_IMG2VID_ACTIVE = (
    "<b>Режим создания видео активирован.</b> Для создания видео загрузите изображение "
    "размером до 20 мегабайт (как файл, без сжатия) и в описании укажите, что "
    "должно происходить в видео. Например: люди слегка улыбаются и машут рукой."
)

VIDEO_TXT2VID_MENU = (
    "🎬 <b>Выберите генератор видео, с которым хотите работать.</b>\n\n"
    "📝 Видео из текста (Text-to-Video) — этот тип генераторов создаёт "
    "видео из текстового описания. Вам нужно описать в текстовом сообщении, "
    "какое именно видео вы хотите и что должно происходить на нём."
)

VIDEO_TXT2VID_ACTIVE = (
    "<b>Режим создания видео из текста активирован.</b> Для создания видео вам нужно "
    "отправить сообщение с текстом, в котором будет подробно описано какое видео "
    "вы хотите получить."
)

VIDEO_UPSCALE_MENU = (
    "🎬 <b>Выберите инструмент для улучшения видео, с которым хотите работать.</b>"
)

VIDEO_UPSCALE_ACTIVE = (
    "<b>Режим улучшения видео активирован.</b> Загрузите видео, у которого вы хотите "
    "улучшить качество."
)

PAY_PROMPT = "На сколько $ хотите пополнить баланс, используя Telegram Stars?"

TASK_ACCEPTED = (
    "✅ Задание принято в обработку.\n"
    "Списано: <b>${price}</b>\n"
    "Баланс: <b>${balance}</b>"
)

# ── Tools & prices (USD) ────────────────────────────────────────────────────

PHOTO_CREATE_TOOLS: list[tuple[str, str, Decimal]] = [
    ("gpt_image_2", "GPT Image 2", Decimal("0.02")),
    ("gpt_image_15", "GPT Image 1.5", Decimal("0.05")),
    ("nano_banana", "Nano Banana", Decimal("0.02")),
    ("nano_banana_pro_4k", "Nano Banana Pro 4K", Decimal("0.07")),
    ("nano_banana_pro_2k", "Nano Banana Pro 2K", Decimal("0.02")),
    ("wan_27_pro", "Wan 2.7 Pro", Decimal("0.02")),
    ("seedream_45", "Seedream 4.5", Decimal("0.05")),
    ("flux_20", "FLUX 2.0", Decimal("0.05")),
]

PHOTO_ENHANCE_TOOLS: list[tuple[str, str, Decimal]] = [
    ("enhance_full", "Улучшение всего фото", Decimal("0.02")),
    ("enhance_face", "Улучшение лица 🔥", Decimal("0.02")),
    ("enhance_resolution", "Улучшение разрешения", Decimal("0.02")),
    ("retouch_face", "Ретушь лица", Decimal("0.02")),
]

PHOTO_MODIFY_TOOLS: list[tuple[str, str, Decimal]] = [
    ("neuro_photo", "Нейрофотошоп", Decimal("0.02")),
    ("neuro_photo_pro", "Нейрофотошоп Pro", Decimal("0.10")),
    ("change_style", "Изменить стиль фото", Decimal("0.05")),
    ("aspect_ratio", "Соотношение сторон", Decimal("0.08")),
    ("remove_objects", "Удаление объектов", Decimal("0.03")),
    ("remove_bg", "Убрать фон", Decimal("0.03")),
]

VIDEO_GENERATORS: list[tuple[str, str, Decimal]] = [
    ("runway_hd", "Runway HD", Decimal("0.15")),
    ("hailuo", "Hailuo", Decimal("0.25")),
    ("grok_hd", "Grok HD", Decimal("0.25")),
    ("wan_25_hd", "Wan 2.5 HD", Decimal("0.35")),
    ("kling", "Kling", Decimal("0.25")),
    ("gemini_omni", "Gemini Omni", Decimal("0.40")),
]

PAY_PACKAGES_USD: tuple[int, ...] = (2, 5, 10, 25, 50)

TOOL_BY_ID: dict[str, tuple[str, Decimal]] = {}
for _id, _title, _price in (
    PHOTO_CREATE_TOOLS + PHOTO_ENHANCE_TOOLS + PHOTO_MODIFY_TOOLS + VIDEO_GENERATORS
):
    TOOL_BY_ID[_id] = (_title, _price)


# ── In-memory user state (resets on bot restart) ─────────────────────────────

@dataclass
class UserState:
    accepted_rules: bool = False
    balance_usd: Decimal = field(default_factory=lambda: Decimal("0.00"))
    active_tool_id: str | None = None
    active_mode: str | None = None


_users: dict[int, UserState] = {}


def _user(user_id: int) -> UserState:
    if user_id not in _users:
        _users[user_id] = UserState()
    return _users[user_id]


def _get_user(user_id: int) -> tuple[bool, Decimal, str | None, str | None]:
    u = _user(user_id)
    return u.accepted_rules, u.balance_usd, u.active_tool_id, u.active_mode


def set_accepted_rules(user_id: int) -> None:
    _user(user_id).accepted_rules = True


def set_active_tool(user_id: int, tool_id: str, mode: str) -> None:
    u = _user(user_id)
    u.active_tool_id = tool_id
    u.active_mode = mode


def clear_active_tool(user_id: int) -> None:
    u = _users.get(user_id)
    if u is not None:
        u.active_tool_id = None
        u.active_mode = None


def add_balance(user_id: int, usd: Decimal) -> Decimal:
    u = _user(user_id)
    u.balance_usd = (u.balance_usd + usd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return u.balance_usd


def try_charge(user_id: int, price: Decimal) -> tuple[bool, Decimal]:
    u = _user(user_id)
    if u.balance_usd < price:
        return False, u.balance_usd
    u.balance_usd = (u.balance_usd - price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return True, u.balance_usd


def format_balance(user_id: int) -> str:
    _, balance, _, _ = _get_user(user_id)
    return f"{balance:.2f}"


def low_balance_text(user_id: int) -> str:
    return (
        f"<b>На вашем счете:</b> {format_balance(user_id)}\n"
        "Пополните баланс для использования бота.\n"
        "Для пополнения нажмите > /pay"
    )


def usd_to_stars(usd: int) -> int:
    return usd * STARS_PER_USD


async def send_topup_invoice(bot: Bot, user_id: int, usd: int) -> None:
    stars = usd_to_stars(usd)
    await bot.send_invoice(
        chat_id=user_id,
        title=f"Пополнение баланса ${usd}",
        description=f"Зачисление ${usd:.2f} на внутренний счёт Spark AI Creator",
        payload=f"topup:{user_id}:{usd}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"${usd}", amount=stars)],
    )


# ── Keyboards ───────────────────────────────────────────────────────────────

def kb_rules() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Подтверждаю", callback_data="rules:accept")]]
    )


def kb_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Фото и изображения", callback_data="nav:photo")],
            [InlineKeyboardButton(text="🎬 Создание видео", callback_data="nav:video")],
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="nav:pay")],
        ]
    )


def kb_back(callback: str) -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]]


def kb_photo_root() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Создание", callback_data="photo:create")],
            [InlineKeyboardButton(text="📷 Улучшение", callback_data="photo:enhance")],
            [InlineKeyboardButton(text="🖌️ Изменение", callback_data="photo:modify")],
            *kb_back("nav:main"),
        ]
    )


def _kb_tools(tools: list[tuple[str, str, Decimal]], prefix: str, back_cb: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{title} — ${price}", callback_data=f"{prefix}:{tool_id}")]
        for tool_id, title, price in tools
    ]
    rows.extend(kb_back(back_cb))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_video_root() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼️ Видео из изображений", callback_data="video:img2vid")],
            [InlineKeyboardButton(text="📝 Видео из текста", callback_data="video:txt2vid")],
            [InlineKeyboardButton(text="📹 Улучшить качество", callback_data="video:upscale")],
            *kb_back("nav:main"),
        ]
    )


def kb_pay() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"${usd}", callback_data=f"pay:{usd}")]
        for usd in PAY_PACKAGES_USD
    ]
    rows.extend(kb_back("nav:main"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── FSM (optional screen tracking) ──────────────────────────────────────────

class SparkStates(StatesGroup):
    waiting_task = State()


router = Router()


async def show_main_menu(target: Message, *, edit: bool = False) -> None:
    text = WELCOME_TEXT + f"\n\n💰 Баланс: <b>${format_balance(target.from_user.id)}</b>"
    markup = kb_main_menu()
    if edit and target.from_user:
        await target.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)


# ── Handlers ────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    accepted, _, _, _ = _get_user(message.from_user.id)
    if not accepted:
        await message.answer(RULES_TEXT, reply_markup=kb_rules())
        return
    await show_main_menu(message)


@router.callback_query(F.data == "rules:accept")
async def on_rules_accept(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    set_accepted_rules(callback.from_user.id)
    await state.clear()
    try:
        await callback.message.edit_text("✅ Спасибо! Добро пожаловать.")
    except Exception:
        pass
    await show_main_menu(callback.message)


@router.callback_query(F.data == "nav:main")
async def nav_main(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    clear_active_tool(callback.from_user.id)
    text = WELCOME_TEXT + f"\n\n💰 Баланс: <b>${format_balance(callback.from_user.id)}</b>"
    await callback.message.edit_text(text, reply_markup=kb_main_menu(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "nav:photo")
async def nav_photo(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    clear_active_tool(callback.from_user.id)
    await callback.message.edit_text(PHOTO_MENU_TEXT, reply_markup=kb_photo_root(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "nav:video")
async def nav_video(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    clear_active_tool(callback.from_user.id)
    await callback.message.edit_text(VIDEO_MENU_TEXT, reply_markup=kb_video_root(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "nav:pay")
async def nav_pay(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(PAY_PROMPT, reply_markup=kb_pay())


@router.message(Command("pay"))
async def cmd_pay(message: Message) -> None:
    await message.answer(PAY_PROMPT, reply_markup=kb_pay())


@router.callback_query(F.data == "photo:create")
async def photo_create_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        PHOTO_CREATE_TEXT,
        reply_markup=_kb_tools(PHOTO_CREATE_TOOLS, "tool:photo_create", "nav:photo"),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "photo:enhance")
async def photo_enhance_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        PHOTO_ENHANCE_MENU,
        reply_markup=_kb_tools(PHOTO_ENHANCE_TOOLS, "tool:photo_enhance", "nav:photo"),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "photo:modify")
async def photo_modify_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        PHOTO_MODIFY_MENU,
        reply_markup=_kb_tools(PHOTO_MODIFY_TOOLS, "tool:photo_modify", "nav:photo"),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "video:img2vid")
async def video_img2vid_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        VIDEO_IMG2VID_MENU,
        reply_markup=_kb_tools(VIDEO_GENERATORS, "tool:video_img2vid", "nav:video"),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "video:txt2vid")
async def video_txt2vid_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        VIDEO_TXT2VID_MENU,
        reply_markup=_kb_tools(VIDEO_GENERATORS, "tool:video_txt2vid", "nav:video"),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "video:upscale")
async def video_upscale_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        VIDEO_UPSCALE_MENU,
        reply_markup=_kb_tools(VIDEO_GENERATORS, "tool:video_upscale", "nav:video"),
        parse_mode=ParseMode.HTML,
    )


ACTIVE_TEXT_BY_PREFIX = {
    "tool:photo_create": PHOTO_CREATE_ACTIVE,
    "tool:photo_enhance": PHOTO_ENHANCE_ACTIVE,
    "tool:photo_modify": PHOTO_MODIFY_ACTIVE,
    "tool:video_img2vid": VIDEO_IMG2VID_ACTIVE,
    "tool:video_txt2vid": VIDEO_TXT2VID_ACTIVE,
    "tool:video_upscale": VIDEO_UPSCALE_ACTIVE,
}

BACK_BY_PREFIX = {
    "tool:photo_create": "photo:create",
    "tool:photo_enhance": "photo:enhance",
    "tool:photo_modify": "photo:modify",
    "tool:video_img2vid": "video:img2vid",
    "tool:video_txt2vid": "video:txt2vid",
    "tool:video_upscale": "video:upscale",
}


@router.callback_query(F.data.startswith("tool:"))
async def activate_tool(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) != 3:
        return
    prefix = f"{parts[0]}:{parts[1]}"
    tool_id = parts[2]
    if tool_id not in TOOL_BY_ID:
        return

    title, price = TOOL_BY_ID[tool_id]
    set_active_tool(callback.from_user.id, tool_id, prefix)
    await state.set_state(SparkStates.waiting_task)

    active_text = ACTIVE_TEXT_BY_PREFIX.get(prefix, "Инструмент активирован.")
    text = (
        f"<b>{title}</b> — ${price}\n\n"
        f"{active_text}\n\n"
        f"💰 Баланс: <b>${format_balance(callback.from_user.id)}</b>"
    )
    back_cb = BACK_BY_PREFIX.get(prefix, "nav:main")
    markup = InlineKeyboardMarkup(inline_keyboard=kb_back(back_cb))
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("pay:"))
async def pay_package(callback: CallbackQuery, bot: Bot) -> None:
    usd = int(callback.data.split(":")[1])
    if usd not in PAY_PACKAGES_USD:
        await callback.answer("Неверная сумма", show_alert=True)
        return
    await callback.answer()
    await send_topup_invoice(bot, callback.from_user.id, usd)


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_payment(message: Message) -> None:
    payload = message.successful_payment.invoice_payload or ""
    parts = payload.split(":")
    if len(parts) >= 3 and parts[0] == "topup":
        usd = Decimal(parts[2])
    else:
        stars = message.successful_payment.total_amount
        usd = (Decimal(stars) / Decimal(STARS_PER_USD)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    new_balance = add_balance(message.from_user.id, usd)
    await message.answer(
        f"✅ Баланс пополнен на <b>${usd:.2f}</b>\n"
        f"Текущий баланс: <b>${new_balance:.2f}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_main_menu(),
    )


def _is_task_message(message: Message) -> bool:
    if message.text and not message.text.startswith("/"):
        return True
    if message.photo or message.document or message.video:
        return True
    return False


@router.message(SparkStates.waiting_task, _is_task_message)
async def on_task(message: Message, state: FSMContext) -> None:
    _, _, tool_id, _ = _get_user(message.from_user.id)
    if not tool_id or tool_id not in TOOL_BY_ID:
        await state.clear()
        await message.answer("Сначала выберите инструмент в меню.", reply_markup=kb_main_menu())
        return

    title, price = TOOL_BY_ID[tool_id]
    ok, balance = try_charge(message.from_user.id, price)
    if not ok:
        await message.answer(
            low_balance_text(message.from_user.id),
            reply_markup=kb_pay(),
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer(
        TASK_ACCEPTED.format(price=f"{price:.2f}", balance=f"{balance:.2f}"),
        parse_mode=ParseMode.HTML,
    )
    # Demo: one task per activation — re-select tool for next job
    clear_active_tool(message.from_user.id)
    await state.clear()


@router.message(_is_task_message)
async def on_task_without_tool(message: Message) -> None:
    """KP: any task without active tool / zero balance → balance prompt."""
    accepted, balance, tool_id, _ = _get_user(message.from_user.id)
    if not accepted:
        await message.answer(RULES_TEXT, reply_markup=kb_rules())
        return
    if tool_id:
        return  # handled by waiting_task state
    if balance <= 0:
        await message.answer(
            low_balance_text(message.from_user.id),
            reply_markup=kb_pay(),
            parse_mode=ParseMode.HTML,
        )
        return
    await message.answer("Выберите функцию в меню 👇", reply_markup=kb_main_menu())


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Set BOT_TOKEN env variable")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logger.info("Spark AI Creator bot starting (STARS_PER_USD=%s)", STARS_PER_USD)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
