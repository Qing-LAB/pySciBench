import argparse
from . import __version__

def acquire(args):
    # TODO: implement real-time data acquisition
    print(f"Acquiring data from {args.device}...")


def visualize(args):
    # TODO: implement visualization startup
    print("Launching visualization dashboard...")


def script_add(args):
    # TODO: register a user script hook
    print(f"Registering script: {args.path}")


def main():
    parser = argparse.ArgumentParser(prog='psbench')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command')

    p_acq = sub.add_parser('acquire')
    p_acq.add_argument('--device', required=True, help='Path to instrument')
    p_acq.set_defaults(func=acquire)

    p_vis = sub.add_parser('visualize')
    p_vis.set_defaults(func=visualize)

    p_script = sub.add_parser('script')
    sp = p_script.add_subparsers(dest='action')
    p_add = sp.add_parser('add')
    p_add.add_argument('path', help='Path to user script')
    p_add.set_defaults(func=script_add)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

