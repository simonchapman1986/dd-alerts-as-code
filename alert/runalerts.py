import argparse
import pathlib
from os import getenv
from typing import Literal
from argparse import Namespace, ArgumentParser
from state.manager import MonitorStateManager

if __name__ == "__main__":
    DEFAULT_PROJECT_NAME: Literal['test'] = "test"

    parser: ArgumentParser = argparse.ArgumentParser(prog="Alert State Manager")
    parser.add_argument("--dir", nargs="?", default=".", type=pathlib.Path)
    parser.add_argument("--project", default=getenv("PROJECT_NAME", DEFAULT_PROJECT_NAME), type=str)
    args: Namespace = parser.parse_args()
    mng: MonitorStateManager = MonitorStateManager(dir=args.dir, project_name=args.project)
    mng.run()