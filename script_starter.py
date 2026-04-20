import os
from subprocess import run
from time import sleep

from dotenv import load_dotenv

load_dotenv()

BOT_SCRIPT_PATH = os.getenv("BOT_SCRIPT_PATH", "./ThreatIntelBot.py")
CLEANUP_SCRIPT_PATH = os.getenv("CLEANUP_SCRIPT_PATH", "./cleanup_db.py")
RESTART_TIMER_SECONDS = int(os.getenv("RESTART_TIMER_SECONDS", "5"))


def start_script() -> None:
    while True:
        try:
            cleanup_result = run(["python3", CLEANUP_SCRIPT_PATH], check=False)
            if cleanup_result.returncode != 0:
                print(f"Cleanup script exited with code {cleanup_result.returncode}. Continuing...")
            run(["python3", BOT_SCRIPT_PATH], check=True)
            return
        except Exception as exc:
            print(f"Bot crashed ({exc}). Restarting in {RESTART_TIMER_SECONDS} seconds...")
            sleep(RESTART_TIMER_SECONDS)


if __name__ == "__main__":
    start_script()
