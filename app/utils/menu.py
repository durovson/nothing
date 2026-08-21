from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    FSInputFile,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaPhoto,
    MaybeInaccessibleMessage,
    Message,
)

MENU_IMAGE = Path(__file__).resolve().parent.parent / "assets" / "menu.png"
MEDIA_DIR = MENU_IMAGE.parent / "media"
MEDIA_EXTENSIONS = (".gif", ".mp4", ".png", ".jpg", ".jpeg")


def media_path(screen: str) -> Path:
    """Resolve a replaceable repository media asset, falling back to menu.png."""
    for extension in MEDIA_EXTENSIONS:
        candidate = MEDIA_DIR / f"{screen}{extension}"
        if candidate.is_file():
            return candidate
    return MENU_IMAGE


def _input_media(path: Path, caption: str):
    source = FSInputFile(path)
    if path.suffix.lower() in {".gif", ".mp4"}:
        return InputMediaAnimation(media=source, caption=caption)
    return InputMediaPhoto(media=source, caption=caption)


async def render_menu(
    message: MaybeInaccessibleMessage,
    caption: str,
    keyboard: InlineKeyboardMarkup,
    screen: str = "main_menu",
) -> Message:
    """Edit the current bot card, falling back to one replacement card."""
    if len(caption) > 1024:
        if isinstance(message, Message) and message.from_user and message.from_user.is_bot:
            try:
                if message.photo or message.animation:
                    await message.delete()
                else:
                    await message.edit_text(caption, reply_markup=keyboard)
                    return message
            except TelegramBadRequest:
                pass
        return await message.answer(caption, reply_markup=keyboard)
    asset = media_path(screen)
    if isinstance(message, Message) and message.from_user and message.from_user.is_bot:
        try:
            if message.photo or message.animation:
                await message.edit_media(media=_input_media(asset, caption), reply_markup=keyboard)
            else:
                await message.edit_text(caption, reply_markup=keyboard)
            return message
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return message
            try:
                await message.delete()
            except TelegramBadRequest:
                pass
    if asset.suffix.lower() in {".gif", ".mp4"}:
        return await message.answer_animation(animation=FSInputFile(asset), caption=caption, reply_markup=keyboard)
    return await message.answer_photo(photo=FSInputFile(asset), caption=caption, reply_markup=keyboard)


async def render_home(
    message: MaybeInaccessibleMessage,
    caption: str,
    keyboard: InlineKeyboardMarkup,
) -> Message:
    """Home is always a fresh card, as required by the navigation contract."""
    if isinstance(message, Message) and message.from_user and message.from_user.is_bot:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
    return await render_menu(message, caption, keyboard, screen="main_menu")


async def remember_menu(state: FSMContext, message: Message) -> None:
    await state.update_data(menu_chat_id=message.chat.id, menu_message_id=message.message_id)


async def render_stored_menu(
    user_message: Message,
    state: FSMContext,
    caption: str,
    keyboard: InlineKeyboardMarkup,
    screen: str = "deal_join",
) -> Message | None:
    data = await state.get_data()
    chat_id = data.get("menu_chat_id")
    message_id = data.get("menu_message_id")
    try:
        await user_message.delete()
    except TelegramBadRequest:
        pass
    if len(caption) > 1024 and isinstance(chat_id, int) and isinstance(message_id, int):
        try:
            await user_message.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            pass
        result = await user_message.answer(caption, reply_markup=keyboard)
        await remember_menu(state, result)
        return result
    if isinstance(chat_id, int) and isinstance(message_id, int):
        asset = media_path(screen)
        try:
            result = await user_message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=_input_media(asset, caption),
                reply_markup=keyboard,
            )
            return result if isinstance(result, Message) else None
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return None
    asset = media_path(screen)
    if asset.suffix.lower() in {".gif", ".mp4"}:
        result = await user_message.answer_animation(animation=FSInputFile(asset), caption=caption, reply_markup=keyboard)
    else:
        result = await user_message.answer_photo(photo=FSInputFile(asset), caption=caption, reply_markup=keyboard)
    await remember_menu(state, result)
    return result
