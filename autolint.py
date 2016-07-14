import argparse
import collections
import fnmatch
import os
import pathlib
import subprocess
import sys

import pathspec
import yaml


class AutoLintError(Exception):
    """Autolint exception base class."""

    pass


class AutoLintIOError(AutoLintError):
    """Exception to be raised on file exceptions."""

    pass


class AutoLintConfError(Exception):
    """Exception to be raised on configuration file errors."""

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

        target_path = pathlib.Path(target).expanduser()
        if not target_path.is_dir():
            raise AutoLintIOError("Expecting a dir but got %s" % target)
        self.target = target_path

        if configuration is not None:
            configuration_path = pathlib.Path(configuration).expanduser()
            if not configuration_path.is_file():
                raise AutoLintIOError(("Expecting a file as configuration, but "
                                       "got %s" % configuration))
            self.configuration = configuration_path

        if ignore_file is not None:
            ignore_file_path = pathlib.Path(ignore_file).expanduser()
            if not ignore_file_path.is_file():
                raise AutoLintIOError(("Expecting a ignore file, but "
                                       "got %s" % ignore_file))
            self.ignore_file = ignore_file_path

        self.__load_configuration()

    def __load_configuration(self):
        """Load the configuration file into a python object."""
        with open(str(self.configuration), 'r') as f:
            self.configuration_dict = yaml.safe_load(f)

    def run_linter(self, pretty_print=True, print_all=False):
        """Load the configurations and run the linter."""

        all_files = self.__get_all_files()
        to_lint_files = self.__remove_ignored_files(all_files)
        results = self.__lint(self.__classify_files(to_lint_files))
        return_code = 0


        if print_all:
            for lang, v in results.items():
                print("%s" % lang)
                for linter, r in v.items():
                    print("\t%s" % linter)
                    for filename, result in r.items():
                        print('\t\t"%s"' % filename)
                        print("\t\t\tret:%s\n\t\t\tout:%s\n\t\t\terr:%s" % result)
                        if result[0] != 0:
                            return_code = 1

        elif pretty_print:
            total_files = 0
            failed_files = 0
            for lang, v in results.items():
                print("%s" % lang)
                lang_total_files = 0
                lang_failed_files = 0
                for linter, r in v.items():
                    linter_total_files = 0
                    linter_failed_files = 0
                    print("\t%s" % linter)
                    for filename, result in r.items():
                        linter_total_files += 1
                        if result[0] != 0:
                            linter_failed_files += 1
                            print("\t\t%s\n\t\t\t%s\n\t\t\t%s" % (filename,
                                                                  result[1].decode('utf-8').replace('\n', '\n\t\t\t'),
                                                                  result[2].decode('utf-8').replace('\n', '\n\t\t\t')))
                    if len(v) > 1:
                        print("\t%s: Checked %d files, %d with errors" % (linter, linter_total_files, linter_failed_files))
                    lang_total_files += linter_total_files
                    lang_failed_files += linter_failed_files
                if len(results) > 1:
                    print("%s: Checked %d files, %d with errors" % (lang, lang_total_files, lang_failed_files))
                total_files +=lang_total_files
                failed_files += lang_failed_files
            print("Checked %d files, %d with errors" % (total_files, failed_files))

        return return_code, results

    def __get_all_files(self):
        """Returns a list of all the files in the target directory."""

        ret_files = []
        for root, dirs, files in os.walk(str(self.target)):
            for filename in files:
                ret_files.append(os.path.join(root, filename))
        return ret_files

    def __remove_ignored_files(self, all_files):
        """Remove the files matching a pattern at the ignore file

        :param all_files, list of the files to be removed

        :return a subset of all_files, where all the files matched by an ignore
                pattern were removed
        """
        if self.ignore_file is None:
            return all_files

        with open(str(self.ignore_file), 'r') as f:
            spec = pathspec.PathSpec.from_lines('gitignore', f)

        return_files = set(all_files)
        for p in spec.patterns:
            if p.include is not None:
                result_files = p.match(all_files)
                if p.include:
                    return_files.difference_update(result_files)
                else:
                    return_files.update(result_files)
        return return_files

    def __classify_files(self, files):
        """Classify a list of files into languages.

        :param files, list of files to be classified.

        :return a dict with an entry per each language found in the directory,
                excluding ignore files specified. Each entry includes a list of
                files to be linted.
                ex. {'c':['src/main.c', 'src/include.h'], 'js':['src/main.js']}
        """

        ret = {}
        try:
            for lang, conf in self.configuration_dict['langs'].items():
                ret[lang] = set()
                for pattern in conf['include']:
                    ret[lang].update(
                        [f for f in files if fnmatch.fnmatch(f, pattern)])
                if not ret[lang]:
                    del ret[lang]

        except KeyError as e:
            raise AutoLintConfError(("Configuration file, key %s not found"
                                     % e.args[0]))

        return ret

    def __lint(self, files):
        """Receive the language and the files and run the linter on them.

        :param files, dictionary with languages as key and a iterable of files
                      as values.

        :return TODO
        """

        ret = {}
        lang = ''

        try:
            for lang, lang_files in files.items():
                ret[lang] = {}
                linters = self.configuration_dict['langs'][lang]['linters']
                for linter in linters:
                    linter_to_run = self.configuration_dict['linters'][linter]
                    cmd = []
                    cmd.append(linter_to_run['cmd'])
                    if 'flags' in linter_to_run:
                        for flag in linter_to_run['flags']:
                            cmd.append(flag)
                    ret[lang][linter] = self.__execute_linter_program(
                            cmd, lang_files)

        except KeyError as e:
            key = e.args[0]
            if key == 'linters':
                raise AutoLintConfError('Linter not specified for %s' % lang)
            raise AutoLintConfError('Missing "%s" at configuration' % key)

        return ret

    @classmethod
    def __execute_linter_program(self, cmd, files):
        """Execute and collect the results of the linter execution on the files.

        There is no timeout here, the method will wait till the execution of
        cmd returns.

        :param cmd, list of str as Popen receives to run a program. The path to
                    the file will be replaced in the list if the keyword
                    '%file_path%' appears, otherwise the path will be append to
                    the list.
        :param files, list of str with the path to the files to be linted.

        :return an ordered dict with one entry for each file in the files list,
                as value it will contain the exit code of the linter, the
                stdout and the stderr."""

        ret = collections.OrderedDict()
        need_replace = False
        for c in cmd:
            if '%file_path%' in c:
                need_replace = True
                break

        for f in files:
            if need_replace:
                command = [s.replace('%file_path%', f) for s in cmd]
            else:
                command = list(cmd)
                command.append(f)

            p = subprocess.Popen(command, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            ret[f] = (p.returncode, stdout, stderr)

        return ret


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
                              "provided, target/..autolint.yml will be used. "
                              "If not found default will be used, if provided "
                              "and not found, an error will be raised."),
                        default=None,
                        type=str)
    parser.add_argument("-i", "--ignore",
                        help=("path to the autolint ignore file, if not "
                              "provided, target/.lintignore will be used if"
                              "present."),
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
    target = args.target
    if args.no_ignore:
        ignore_file = None
    else:
        if args.ignore is None:
            ignore_file = os.path.join(target, ".lintignore")
            if not os.path.isfile(ignore_file):
                ignore_file = None
        else:
            ignore_file = args.ignore

    if args.configuration is not None:
        configuration = args.configuration
    else:
        configuration = os.path.join(target, ".autolint.yml")
        if not os.path.isfile(configuration):
            configuration = None

    AutoLint(target, configuration, ignore_file).run_linter()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
