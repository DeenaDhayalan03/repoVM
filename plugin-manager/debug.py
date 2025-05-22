if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    from main import app

    app.root_path = None  # type: ignore

import argparse
import gc
import logging

import uvicorn

from scripts.config import Services

gc.collect()

ap = argparse.ArgumentParser()

if __name__ == "__main__":
    logging.warning(
        """
    The app is starting in debug mode!

    This can result in instability and exposure to vulnerability.

    If you are seeing this message in production, you have probably screwed up your start up script.

    Run app.py or start app using uvicorn directly.
    """
    )
    ap.add_argument(
        "--port",
        "-p",
        required=False,
        default=Services.PORT,
        help="Port to start the application.",
    )
    ap.add_argument(
        "--bind",
        "-b",
        required=False,
        default=Services.HOST,
        help="IF to start the application.",
    )
    arguments = vars(ap.parse_args())

    logging.info(f"App Starting at {arguments['bind']}:{arguments['port']}")
    uvicorn.run("main:app", host=arguments["bind"], port=int(arguments["port"]))
