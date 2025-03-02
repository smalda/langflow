import os
import subprocess
import sys


def run_services():
    # Start FastAPI
    api_process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Start RabbitMQ consumer
    consumer_process = subprocess.Popen(
        ["python", "app/run_consumer.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Start Telegram bot
    bot_process = subprocess.Popen(
        ["python", "-m", "bot.main"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        api_process.wait()
        consumer_process.wait()
        bot_process.wait()
    except KeyboardInterrupt:
        api_process.terminate()
        consumer_process.terminate()
        bot_process.terminate()

        api_process.wait()
        consumer_process.wait()
        bot_process.wait()


if __name__ == "__main__":
    run_services()
