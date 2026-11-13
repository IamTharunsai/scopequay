import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"--help", "-h"}:
        print(
            "ScopeQuay — local agent-action experiments and review\n\n"
            "  serve          Open the local experiment workbench\n"
            "  review         Assess action-context JSON; execute no tool\n"
            "  install-skill  Copy the advisory skill to an explicit target\n"
            "  generate / validate / annotate / agreement\n"
            "  calibrate / cost-calibrate / run / agent-run / models\n"
            "  report / verify-log\n\nUse <command> --help for options. Cloud inference is disabled."
        )
        return
    if args and args[0] == "review":
        from .review_cli import review

        return review(args[1:])
    if args and args[0] == "install-skill":
        from .review_cli import install_skill

        return install_skill(args[1:])
    if args and args[0] == "serve":
        from .server import main as serve

        return serve(args[1:])
    from tharun.cli import main as research

    return research(args)
