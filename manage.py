import logging
import sys
from src.client import Client


def main():
    # define a Handler which writes INFO messages or higher to the sys.stderr
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s: %(levelname)s/%(name)s] %(message)s')

    if len(sys.argv) < 2:
        print("usage: manage.py run")
    if len(sys.argv) is not 2 and sys.argv[1] is not "run":
        print("[ERROR] Command cannot be parsed. Exiting...")
        return

    Client().run()


if __name__ == "__main__":
    main()
