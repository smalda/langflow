# @pytest.mark.asyncio
# async def test_dance_education_bot_initialization():
#     # Given
#     bot = DanceEducationBot()

#     # When
#     bot.setup()

#     # Then
#     assert bot.application is not None
#     assert bot.api_client is not None

# @pytest.mark.asyncio
# async def test_bot_handler_registration():
#     # Given
#     bot = DanceEducationBot()
#     bot.setup()

#     # Then
#     handlers = bot.application.handlers[0]
#     assert any(isinstance(h, CommandHandler) for h in handlers)
#     assert any(isinstance(h, ConversationHandler) for h in handlers)
