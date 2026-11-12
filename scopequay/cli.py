import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "serve":
        from .server import main as serve

        return serve(args[1:])
    from tharun.cli import main as research

    return research(args)
