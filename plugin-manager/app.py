if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

import argparse
import logging

import uvicorn

from scripts.config import Services

ap = argparse.ArgumentParser()

if __name__ == "__main__":
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
    uvicorn.run("main:app", host=arguments["bind"], port=int(arguments["port"]), limit_max_requests=1048576000)
