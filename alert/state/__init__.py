import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def stdout(*args):
    arg_count = 0
    color = bcolors.HEADER
    for msg in args:
        if arg_count > 0:
            color = bcolors.OKCYAN
        print(f"{color}{msg}{bcolors.ENDC}", file=sys.stdout)
        arg_count += 1


def stderr(*args):
    for msg in args:
        print(f"{bcolors.FAIL}{msg}{bcolors.ENDC}", file=sys.stderr)