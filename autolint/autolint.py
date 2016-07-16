#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import collections
import fnmatch
import os
import pkg_resources
import subprocess
import sys

import pathspec
import yaml

#Python2 support
try:
    from autolint.runners import Runner
except ImportError:
    from .runners import Runner

__conf_file__ = ".autolint.yml"
__project__ = "autolint"


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

        target_path = os.path.expanduser(target)
        if not os.path.isdir(target_path):
            raise AutoLintIOError("Expecting a dir but got %s" % target)
        self.target = target_path

        if configuration is not None:
            configuration_path = os.path.expanduser(configuration)
            if not os.path.isfile(configuration_path):
                raise AutoLintIOError(("Expecting a file as configuration, but"
                                       " got %s" % configuration))
            self.configuration = configuration_path

        if self.configuration is None:
            self.configuration = self.get_default_conf_path()

        if ignore_file is not None:
            ignore_file_path = os.path.expanduser(ignore_file)
            if not os.path.isfile(ignore_file_path):
                raise AutoLintIOError(("Expecting a ignore file, but "
                                       "got %s" % ignore_file))
            self.ignore_file = ignore_file_path

        self.__load_configuration()

    @staticmethod
    def get_default_conf_path():
        """Get the path to the configuration file installed with the module.

        :return the path to the configuration file installed."""
        filename = __conf_file__
        projectname = __project__
        return pkg_resources.resource_filename(projectname, filename)

    def __load_configuration(self):
        """Load the configuration file into a python object."""

        with open(self.configuration, 'r') as f:
            self.configuration_dict = yaml.safe_load(f)

    @staticmethod
    def print_helper(filename, stdout, stderr):
        """ Print nicely the parameters

        :param filename: str name of the file.
        :param stdout: bytes of stdout wrote by the linter.
        :param stderr: bytes of stderr wrote by the linter.
        """
        if stdout and stderr:
            print("\t\t%s\n\t\t\t%s\n\t\t\t%s" % (
                filename,
                stdout.decode('utf-8').replace('\n', '\n\t\t\t'),
                stderr.decode('utf-8').replace('\n', '\n\t\t\t')))
        elif stdout:
            print("\t\t%s\n\t\t\t%s" % (
                filename,
                stdout.decode('utf-8').replace('\n', '\n\t\t\t')))
        elif stderr:
            print("\t\t%s\n\t\t\t%s" % (
                filename,
                stderr.decode('utf-8').replace('\n', '\n\t\t\t')))

    def __pretty_print(self, results):
        """Print a hierarchy of the languages and linters ran.

        :param results, dict with the results of an execution of __lint.

        :return amount of files with return code != 0

        """

        total_files = 0
        failed_files = 0
        for lang, d1 in results.items():
            print("%s" % lang)
            lang_total_files = 0
            lang_failed_files = 0
            for linter, d2 in d1.items():
                linter_total_files = 0
                linter_failed_files = 0
                print("\t%s" % linter)
                for filename, result in d2.items():
                    linter_total_files += 1
                    if result[0] != 0:
                        linter_failed_files += 1
                        self.print_helper(filename, result[1], result[2])
                    else:
                        print("\t\t%s" % filename)
                if len(d1) > 1:
                    print(("\t%s: Checked %d files; %d with errors") % (
                            linter, linter_total_files, linter_failed_files))
                lang_total_files += linter_total_files
                lang_failed_files += linter_failed_files
            if len(results) > 1:
                print(("%s: Checked %d files; %d with errors") % (
                        lang, lang_total_files, lang_failed_files))
            total_files += lang_total_files
            failed_files += lang_failed_files
        print("Checked %d files, %d with errors" % (total_files,
                                                    failed_files))
        return failed_files

    def print_all_fx(self, _unused, stdout, stderr):
        """Print the stdout and stderr bytes. Both decoded using utf-8

        :param _unused, not used, just to comply runner format.
        :param stdout, bytes to be printed out to the stdout.
        :param stderr, bytes to be printed out to the stderr.
        """

        sys.stdout.write(stdout.decode('utf-8'))
        sys.stderr.write(stderr.decode('utf-8'))

    def run_linter(self, pretty_print=False, print_all=True):
        """Load the configurations and run the linter.

        :param pretty_print If true prints a hierarchy of languages,
                            linters and files describing the execution. It
                            also summarize the failed files and total files.

        :param print_all If true prints the stdout and stderr for each
                         execution of the linter. It keeps the order each
                         output was printed by the linter.

        :return A tuple of two elemts, the first is 1 if there is at leat one
                linter execution returned a return_code != 0 and 0 otherwise.
                The second element es the complete result dict as returned by
                __lint.
        """

        all_files = self.__get_all_files()
        to_lint_files = self.__remove_ignored_files(all_files)
        classified_files = self.__classify_files(to_lint_files)
        results = self.__lint(classified_files,
                              self.print_all_fx if print_all else None)
        return_code = 0

        if print_all:
            for lang, v in results.items():
                for linter, r in v.items():
                    for filename, result in r.items():
                        if result[0] != 0:
                            return_code = 1

        elif pretty_print:
            return_code = 1 if self.__pretty_print(results) > 0 else 0

        else:
            for v in results.itervalues():
                for r in v.itervalues():
                    for result in r.itervalues():
                        if result[0] != 0:
                            return 1, results

        return return_code, results

    def __get_all_files(self):
        """Get all the files in the target directory.

        :return  A list of str with the path of each file under the target
                 directory.
        """

        ret_files = []
        for root, dirs, files in os.walk(self.target):
            for filename in files:
                ret_files.append(os.path.join(root, filename))
        return ret_files

    def __remove_ignored_files(self, all_files):
        """Remove the files matching a pattern at the ignore file

        :param all_files, list of the files to be filtered

        :return a set instance containing a subset of all_files, where all the
                files matched by an ignore pattern were removed.
        """

        if self.ignore_file is None:
            return all_files

        with open(self.ignore_file, 'r') as f:
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

        The classification is against the patterns included in the
        configuration file per language. Unix filename pattern matching will
        be applied to the path of the file.

        :param files, an iterable of files to be classified.

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

    def __lint(self, files, cb):
        """Receive the language and the files and run the linter on them.

        :param files, dictionary with languages as key and a iterable of files
                      as values.
        :param cb Function to be passed to runner.run as parameter.

        :return A group of dicts and ordered dicts with the results of the
                executions ran. The hierarchy is as follows:
                {<language_name>:
                    {<linter_name>:
                        {<file_name>:(return_code, stdout_bytes, stderr_bytes)}
                    }
                }
        """

        ret = {}
        lang = ''

        try:
            for lang, lang_files in files.items():
                ret[lang] = {}
                linters = self.configuration_dict['langs'][lang]['linters']
                for linter in linters:
                    linter_conf = self.configuration_dict['linters'][linter]
                    if 'runner' in linter_conf:
                        runner = Runner.new_runner(linter_conf['runner'])
                    else:
                        runner = Runner.new_runner(linter)
                    ret[lang][linter] = runner.run(linter_conf, lang_files, cb)

        except KeyError as e:
            key = e.args[0]
            if key == 'linters':
                raise AutoLintConfError('Linter not specified for %s' % lang)
            raise AutoLintConfError('Missing "%s" at configuration' % key)

        return ret


def get_parser():
    """Creates the parser for the command line

    :return: It returns an argparse.ArgumentParser ready to parse argv
    """

    parser = argparse.ArgumentParser(description="AutoLinter")
    printg = parser.add_mutually_exclusive_group()
    parser.add_argument("-c", "--configuration",
                        help=("path to the autolint configuration, if not "
                              "provided, target/.autolint.yml will be used. "
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
    parser.add_argument("--get-default-conf",
                        help=("Print the path to the default configuration "
                              "file and return."),
                        dest='get_default_conf',
                        action='store_true')
    parser.set_defaults(get_default_conf=False)
    parser.add_argument("--no-ignore",
                        help=("do not use a ignore file, this flag makes "
                              "--ignore flag to be discarded."),
                        dest='no_ignore',
                        action='store_true')
    parser.set_defaults(no_ignore=False)
    printg.add_argument("--no-print",
                        help=("Do not print anything, flag can not be used "
                              "with --pretty-print."),
                        dest='no_print',
                        action='store_true')
    printg.set_defaults(no_print=False)
    printg.add_argument("--pretty-print",
                        help=("print the output of the linters within a"
                              "hierarchy of the languages and linters ran."),
                        dest='pretty_print',
                        action='store_true')
    printg.set_defaults(pretty_print=False)
    parser.add_argument("target",
                        help="directory path to be linted",
                        nargs="?",
                        default=os.getcwd(),
                        type=str)
    return parser


def main():
    args = get_parser().parse_args()
    target = args.target
    if args.get_default_conf:
        with open(AutoLint.get_default_conf_path(), 'r') as f:
            print(f.read())
        return
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

    auto_lint = AutoLint(target, configuration, ignore_file)
    print_all = not(args.no_print or args.pretty_print)
    return auto_lint.run_linter(args.pretty_print, print_all)[0]

if __name__ == "__main__":
    sys.exit(main())
