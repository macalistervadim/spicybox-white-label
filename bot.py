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

WELCOME_TEXT = (
    "<b>👋 Welcome!</b> Thanks for stopping by!\n\n"
    "<b>Our bot is an AI aggregator built for people who want to use the best "
    "neural networks in one place without paying monthly subscriptions.</b>\n\n"
    "<b>Here you can create, enhance, and edit images or videos</b> — "
    "everything you need in one place! 🚀\n\n"
    "You can top up your in-bot balance for any amount, activate the tool you "
    "need, and payment will be deducted from your balance after you receive the "
    "result. The bot has no free features, so we can offer the lowest prices.\n\n"
    "<b>Choose a feature below 👇</b>"
)

PHOTO_MENU_TEXT = (
    "🌄 <b>Choose the type of neural networks for working with photos and images:</b>\n\n"
    "🎨 <b>Create</b> — generate images from a prompt or from a prompt plus "
    "reference images.\n\n"
    "📷 <b>Enhance</b> — improve and restore image quality.\n\n"
    "🖌️ <b>Edit</b> — AI tools for editing images (neuro-photoshop, retouching, "
    "background/object removal or replacement, style transfer, interior design, etc.)"
)

PHOTO_CREATE_TEXT = (
    "<b>Choose the image generator you want to work with.</b>\n\n"
    "❓ <b>Not sure which one to pick:</b>\n\n"
    "<b>4o Image</b> — great at generating images with text, accepts not only "
    "text prompts but up to 5 reference images and creates new images from your "
    "instructions. Works as a chat with the bot.\n"
    "<b>Midjourney</b> — a solid price/quality option that generates 4 images "
    "at once with the option to pick one and upscale it.\n"
    "<b>Flux1.1Pro Ultra</b> — best quality at high resolution.\n"
    "<b>Recraft V3</b> — ranks among the top performers in benchmarks.\n\n"
    "⚠️ Attention! Almost all generators use automatic content moderation. "
    "If your prompt or image contains unacceptable content (violence, cruelty, "
    "nudity, erotica, copyrighted material, brand logos, famous characters or "
    "people, discriminatory content, drugs, weapons, political figures or symbols), "
    "the generator will return a black image and the charge will not be refunded."
)

PHOTO_CREATE_ACTIVE = (
    "<b>Image generator activated. You can send prompts to create images.</b>\n\n"
    "Prompts may include any parameters supported by this generator "
    "(for example, image aspect ratio)."
)

PHOTO_ENHANCE_MENU = (
    "<b>Choose the photo or image enhancement tool you need. After activation, "
    "all photos you send will be processed with this tool.</b>"
)

PHOTO_ENHANCE_ACTIVE = (
    "<b>The selected photo workflow is active.</b> You can now upload photos "
    "in jpeg, jpg, png, or heic format up to 20 MB."
)

PHOTO_MODIFY_MENU = (
    "<b>Choose the photo and image editing method you need. After activation, "
    "all images you send will be processed with this method.</b>"
)

PHOTO_MODIFY_ACTIVE = (
    "<b>The selected photo workflow is active.</b> You can now upload photos "
    "in jpeg, jpg, png, or heic format up to 20 MB."
)

VIDEO_MENU_TEXT = (
    "🎬<b> Choose the type of neural network you want to work with.</b> We offer "
    "all top video generators and tools, grouped into several categories:\n\n"
    "🖼️ <b>Image to Video</b> — create video from photos (or images) plus a "
    "description of what should happen in the video.\n\n"
    "📝 <b>Text to Video</b> — create video from a text description only.\n\n"
    "📹 <b>Upscale Quality</b> — improve video quality to a target resolution and FPS."
)

VIDEO_IMG2VID_MENU = (
    "🎬 <b>Choose a video generator by tapping one of the buttons below.</b>\n\n"
    "🖼️ Image to Video — this type of generator creates video from photos and "
    "images. Send a photo or image as a file and describe in the caption what "
    "should happen in the video. Examples: a woman smiles and waves, a man and "
    "woman hug and kiss, a footballer scores a goal."
)

VIDEO_IMG2VID_ACTIVE = (
    "<b>Video creation mode is active.</b> To create a video, upload an image "
    "up to 20 MB (as a file, without compression) and describe in the caption "
    "what should happen in the video. For example: people smile slightly and wave."
)

VIDEO_TXT2VID_MENU = (
    "🎬 <b>Choose the video generator you want to work with.</b>\n\n"
    "📝 Text to Video — this type of generator creates video from a text "
    "description. Send a text message describing the video you want and what "
    "should happen in it."
)

VIDEO_TXT2VID_ACTIVE = (
    "<b>Text-to-video mode is active.</b> To create a video, send a text message "
    "with a detailed description of the video you want."
)

VIDEO_UPSCALE_MENU = (
    "🎬 <b>Choose the video upscaling tool you want to work with.</b>"
)

VIDEO_UPSCALE_ACTIVE = (
    "<b>Video upscaling mode is active.</b> Upload the video you want to improve."
)

PAY_PROMPT = "How much would you like to top up your balance using Telegram Stars?"

TASK_ACCEPTED = (
    "✅ Task accepted for processing.\n"
    "Charged: <b>${price}</b>\n"
    "Balance: <b>${balance}</b>"
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
    ("enhance_full", "Full Photo Enhance", Decimal("0.02")),
    ("enhance_face", "Face Enhance 🔥", Decimal("0.02")),
    ("enhance_resolution", "Resolution Enhance", Decimal("0.02")),
    ("retouch_face", "Face Retouch", Decimal("0.02")),
]

PHOTO_MODIFY_TOOLS: list[tuple[str, str, Decimal]] = [
    ("neuro_photo", "Neuro Photoshop", Decimal("0.02")),
    ("neuro_photo_pro", "Neuro Photoshop Pro", Decimal("0.10")),
    ("change_style", "Change Photo Style", Decimal("0.05")),
    ("aspect_ratio", "Aspect Ratio", Decimal("0.08")),
    ("remove_objects", "Remove Objects", Decimal("0.03")),
    ("remove_bg", "Remove Background", Decimal("0.03")),
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
    balance_usd: Decimal = field(default_factory=lambda: Decimal("0.00"))
    active_tool_id: str | None = None
    active_mode: str | None = None


_users: dict[int, UserState] = {}


def _user(user_id: int) -> UserState:
    if user_id not in _users:
        _users[user_id] = UserState()
    return _users[user_id]


def _get_user(user_id: int) -> tuple[Decimal, str | None, str | None]:
    u = _user(user_id)
    return u.balance_usd, u.active_tool_id, u.active_mode


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
    balance, _, _ = _get_user(user_id)
    return f"{balance:.2f}"


def low_balance_text(user_id: int) -> str:
    return (
        f"<b>Your balance:</b> {format_balance(user_id)}\n"
        "Top up your balance to use the bot.\n"
        "Tap /pay to top up"
    )


def usd_to_stars(usd: int) -> int:
    return usd * STARS_PER_USD


async def send_topup_invoice(bot: Bot, user_id: int, usd: int) -> None:
    stars = usd_to_stars(usd)
    await bot.send_invoice(
        chat_id=user_id,
        title=f"Balance top-up ${usd}",
        description=f"Credit ${usd:.2f} to your Spark AI Creator account",
        payload=f"topup:{user_id}:{usd}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"${usd}", amount=stars)],
    )


# ── Keyboards ───────────────────────────────────────────────────────────────

def kb_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Photos & Images", callback_data="nav:photo")],
            [InlineKeyboardButton(text="🎬 Video Creation", callback_data="nav:video")],
        ]
    )


def kb_back(callback: str) -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="◀️ Back", callback_data=callback)]]


def kb_photo_root() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Create", callback_data="photo:create")],
            [InlineKeyboardButton(text="📷 Enhance", callback_data="photo:enhance")],
            [InlineKeyboardButton(text="🖌️ Edit", callback_data="photo:modify")],
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
            [InlineKeyboardButton(text="🖼️ Image to Video", callback_data="video:img2vid")],
            [InlineKeyboardButton(text="📝 Text to Video", callback_data="video:txt2vid")],
            [InlineKeyboardButton(text="📹 Upscale Quality", callback_data="video:upscale")],
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
    markup = kb_main_menu()
    if edit and target.from_user:
        await target.edit_text(WELCOME_TEXT, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await target.answer(WELCOME_TEXT, reply_markup=markup, parse_mode=ParseMode.HTML)


# ── Handlers ────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu(message)


@router.callback_query(F.data == "nav:main")
async def nav_main(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    clear_active_tool(callback.from_user.id)
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=kb_main_menu(),
        parse_mode=ParseMode.HTML,
    )


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

    active_text = ACTIVE_TEXT_BY_PREFIX.get(prefix, "Tool activated.")
    text = (
        f"<b>{title}</b> — ${price}\n\n"
        f"{active_text}\n\n"
        f"💰 Balance: <b>${format_balance(callback.from_user.id)}</b>"
    )
    back_cb = BACK_BY_PREFIX.get(prefix, "nav:main")
    markup = InlineKeyboardMarkup(inline_keyboard=kb_back(back_cb))
    await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("pay:"))
async def pay_package(callback: CallbackQuery, bot: Bot) -> None:
    usd = int(callback.data.split(":")[1])
    if usd not in PAY_PACKAGES_USD:
        await callback.answer("Invalid amount", show_alert=True)
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
        f"✅ Balance topped up by <b>${usd:.2f}</b>\n"
        f"Current balance: <b>${new_balance:.2f}</b>",
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
    _, tool_id, _ = _get_user(message.from_user.id)
    if not tool_id or tool_id not in TOOL_BY_ID:
        await state.clear()
        await message.answer("Please select a tool from the menu first.", reply_markup=kb_main_menu())
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
    balance, tool_id, _ = _get_user(message.from_user.id)
    if tool_id:
        return  # handled by waiting_task state
    if balance <= 0:
        await message.answer(
            low_balance_text(message.from_user.id),
            reply_markup=kb_pay(),
            parse_mode=ParseMode.HTML,
        )
        return
    await message.answer("Choose a feature from the menu 👇", reply_markup=kb_main_menu())


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
