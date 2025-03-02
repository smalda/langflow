import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.handlers.utils import create_selection_menu


def test_create_basic_menu():
    """Test creating a basic menu with just options"""
    options = [("option1", "Option 1"), ("option2", "Option 2")]

    markup = create_selection_menu(options)

    assert isinstance(markup, InlineKeyboardMarkup)
    keyboard = markup.inline_keyboard
    assert len(keyboard) == 3  # 1 row per option + home button
    assert all(isinstance(row[0], InlineKeyboardButton) for row in keyboard)
    assert keyboard[0][0].callback_data == "option1"
    assert keyboard[0][0].text == "Option 1"


def test_create_menu_with_done_button():
    """Test creating a menu with a done button"""
    options = [("option1", "Option 1")]

    markup = create_selection_menu(options, done_button=True)

    keyboard = markup.inline_keyboard
    assert len(keyboard) == 3  # options + done + home
    assert keyboard[1][0].callback_data == "done"
    assert "✅" in keyboard[1][0].text


def test_create_menu_without_home_button():
    """Test creating a menu without the home button"""
    options = [("option1", "Option 1")]

    markup = create_selection_menu(options, home_button=False)

    keyboard = markup.inline_keyboard
    assert len(keyboard) == 1  # just options
    assert all("Main Menu" not in button.text for row in keyboard for button in row)


def test_create_menu_with_custom_buttons():
    """Test creating a menu with custom buttons"""
    options = [("option1", "Option 1")]
    custom_buttons = [[InlineKeyboardButton("Custom", callback_data="custom")]]

    markup = create_selection_menu(options, custom_buttons=custom_buttons)

    keyboard = markup.inline_keyboard
    assert len(keyboard) == 3  # options + custom + home
    assert keyboard[1][0].callback_data == "custom"
    assert keyboard[1][0].text == "Custom"


def test_create_menu_with_multiple_items_per_row():
    """Test creating a menu with multiple items per row"""
    options = [
        ("option1", "Option 1"),
        ("option2", "Option 2"),
        ("option3", "Option 3"),
        ("option4", "Option 4"),
    ]

    markup = create_selection_menu(options, items_per_row=2)

    keyboard = markup.inline_keyboard
    assert len(keyboard[0]) == 2  # First row should have 2 items
    assert len(keyboard[1]) == 2  # Second row should have 2 items


def test_empty_options():
    """Test creating a menu with no options"""
    markup = create_selection_menu([])

    keyboard = markup.inline_keyboard
    assert len(keyboard) == 1  # Just home button
    assert "Main Menu" in keyboard[0][0].text


def test_all_features_combined():
    """Test creating a menu with all features enabled"""
    options = [("option1", "Option 1"), ("option2", "Option 2")]
    custom_buttons = [[InlineKeyboardButton("Custom", callback_data="custom")]]

    markup = create_selection_menu(
        options=options,
        done_button=True,
        home_button=True,
        items_per_row=2,
        custom_buttons=custom_buttons,
    )

    keyboard = markup.inline_keyboard
    assert len(keyboard) == 4  # options row + custom + done + home
    assert len(keyboard[0]) == 2  # Two items in first row
    assert keyboard[2][0].callback_data == "done"  # Done button
    assert "Main Menu" in keyboard[-1][0].text  # Home button


def test_invalid_items_per_row():
    """Test creating a menu with invalid items_per_row"""
    options = [("option1", "Option 1"), ("option2", "Option 2")]

    # Items per row should be at least 1
    markup = create_selection_menu(options, items_per_row=0)

    keyboard = markup.inline_keyboard
    # First row should contain both items as the implementation uses max(1, items_per_row)
    assert len(keyboard[0]) == 2  # Two items in first row
    assert keyboard[0][0].text == "Option 1"
    assert keyboard[0][1].text == "Option 2"
