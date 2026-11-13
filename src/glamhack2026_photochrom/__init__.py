import sys


def main() -> None:
    from . import build, paintings

    if "--paintings-only" not in sys.argv:
        build.run()
    paintings.run()
