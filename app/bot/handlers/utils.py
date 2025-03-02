from typing import List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def create_selection_menu(
    options: List[Tuple[str, str]],  # List of (callback_data, display_text) tuples
    done_button: bool = False,
    home_button: bool = True,
    items_per_row: int = 1,
    custom_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard markup with the given options.

    Args:
        options: List of (callback_data, display_text) tuples
        done_button: Whether to add a "Done" button at the bottom
        home_button: Whether to add a "Back to Main Menu" button
        items_per_row: Number of items per row in the keyboard
        custom_buttons: Additional custom buttons to add before home/done buttons

    Returns:
        InlineKeyboardMarkup with the specified options
    """
    keyboard = []
    current_row = []

    # Add main options
    for callback_data, display_text in options:
        current_row.append(
            InlineKeyboardButton(display_text, callback_data=callback_data)
        )

        if len(current_row) == items_per_row:
            keyboard.append(current_row)
            current_row = []

    if current_row:  # Add any remaining buttons
        keyboard.append(current_row)

    # Add custom buttons if provided
    if custom_buttons:
        keyboard.extend(custom_buttons)

    # Add done button if requested
    if done_button:
        keyboard.append([InlineKeyboardButton("✅ Done", callback_data="done")])

    # Add home button if requested
    if home_button:
        keyboard.append(
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
        )

    return InlineKeyboardMarkup(keyboard)
