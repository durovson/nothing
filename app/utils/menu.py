from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message

MENU_IMAGE = Path(__file__).resolve().parent.parent / "assets" / "menu.png"


async def render_menu(
    message: Message,
    caption: str,
    keyboard: InlineKeyboardMarkup,
) -> Message:
    """Edit the current bot card, falling back to one replacement card."""
    if len(caption) > 1024:
        if message.from_user and message.from_user.is_bot:
            try:
                if message.photo or message.animation:
                    await message.delete()
                else:
                    await message.edit_text(caption, reply_markup=keyboard)
                    return message
            except TelegramBadRequest:
                pass
        return await message.answer(caption, reply_markup=keyboard)
    if message.from_user and message.from_user.is_bot:
        try:
            if message.photo or message.animation:
                await message.edit_caption(caption=caption, reply_markup=keyboard)
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
    return await message.answer_photo(
        photo=FSInputFile(MENU_IMAGE), caption=caption, reply_markup=keyboard
    )


async def remember_menu(state: FSMContext, message: Message) -> None:
    await state.update_data(menu_chat_id=message.chat.id, menu_message_id=message.message_id)


async def render_stored_menu(
    user_message: Message,
    state: FSMContext,
    caption: str,
    keyboard: InlineKeyboardMarkup,
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
        try:
            result = await user_message.bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=keyboard
            )
            return result if isinstance(result, Message) else None
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return None
    result = await user_message.answer_photo(
        photo=FSInputFile(MENU_IMAGE), caption=caption, reply_markup=keyboard
    )
    await remember_menu(state, result)
    return result
