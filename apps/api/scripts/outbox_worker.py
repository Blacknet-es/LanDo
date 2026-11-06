import logging
import time

from sqlmodel import Session

from src.infrastructure.db.session import engine
from src.infrastructure.webhooks.outbox import deliver_pending_events

logging.basicConfig(level=logging.INFO)


def main() -> None:
    while True:
        with Session(engine) as session:
            deliver_pending_events(session)
        time.sleep(2)


if __name__ == "__main__":
    main()
