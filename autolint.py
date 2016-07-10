
import argparse
import pathlib
import yaml
import os
import sys

class AutoLintIOError(Exception):
    """Exception to be raised on file exceptions."""
    pass

class AutoLint(object):
    """Class to run linters on code"""

    def __init__(self, target, configuration=None, ignore_file=None):
        """Set the configuration for the object to run the linters.

        :target: str, path to the directory to lint.
        :configuration: str, path to the configuration file to be used to run
                        autolint, if None default configuration will be used.
        :ignore_file: str, path to the ignore file to be used, this file must
                      follow the gitignore syntax and the files matching one of
                      its patterns are going to be skiped during the linter
                      process.
        """

        self.configuration = None
        self.ignore_file = None

        target_path = pathlib.Path.expanduser(target)
        if not target_path.is_dir():
            raise AutoLintIOError("Expecting a dir but got %s" % target)
        self.target = target_path

        if configuration is not None:
            configuration_path = pathlib.Path.expanduser(configuration)
            if not configuration_path.is_file():
                raise AutoLintIOError(("Expecting a file as configuration, but "
                                       "got %s" % configuration))
            self.configuration = configuration_path

        if ignore_file is not None:
            ignore_file_path = pathlib.Path.expanduser(ignore_file)
            if not ignore_file_path.is_file():
                raise AutoLintIOError(("Expecting a ignore file, but "
                                       "got %s" % ignore_file))
            self.ignore_file = ignore_file_path

    def _get_file_list(self):
        pass


def get_parser():
    """Creates the parser for the command line

    :return: It returns an argparse.ArgumentParser ready to parse argv
    """

    CONF_FILE = ".autolint"
    parser = argparse.ArgumentParser(description="AutoLinter")
    parser.add_argument("target",
                        help="directory path to be linted",
                        nargs="?",
                        default=os.getcwd(),
                        type=str)
    parser.add_argument("-c", "--configuration",
                        help=("path to the autolint configuration, if not "
                              "provided, target/.autolint will be used. "
                              "If not found default will be used, if provided "
                              "and not found, an error will be raised."),
                        default=None,
                        type=str)
    parser.add_argument("-i", "--ignore",
                        help=("path to the autolint ignore file, if not "
                              "provided, target/.lintignore will be used."),
                        default=None,
                        type=str)
    parser.add_argument("--no-ignore",
                        help=("do not use a ignore file, this flag makes "
                              "--ignore flag to be discarded."),
                        dest='no_ignore',
                        action='store_true')
    parser.set_defaults(no_ignore=False)
    return parser

def main(argv=None):
    args = get_parser().parse_args()


if __name__ == "__main__":
    sys.exit(main(sys.argv))

