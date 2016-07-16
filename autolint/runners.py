import collections
import subprocess


class Runner(object):
    """Base object to run linters."""
    _runners = collections.defaultdict(lambda: ByFileRunner)

    def __init__(self):
        """Runner constructor"""

        pass

    @classmethod
    def new_runner(cls, name):
        """Return an instance of a Runner specified by name

        :param name: name of a registered runner.

        :return: an instance of the specified runner, the default one if not
                 found.
        """

        return cls._runners[name]()

    def run(self, *args, **kwargs):
        """Run the linter."""

        raise NotImplementedError(
            "%s.%s must override run()." % (self.__class__.__module__,
                                            self.__class__.__name__))


class ByFileRunner(Runner):

    def __init__(self):
        super(ByFileRunner, self).__init__()

    def _execute(self, cmd, files, cb=None):
        """Execute and collect the results of the linter execution on the files.

        There is no timeout here, the method will wait till the execution of
        cmd returns.

        :param cmd, list of str as Popen receives to run a program. The path to
                    the file will be replaced in the list if the keyword
                    '%file_path%' appears, otherwise the path will be append to
                    the list.
        :param files, list of str with the path to the files to be linted.
        :param cb: If not None, will call the callback for each tuple
                   (returncode, stdout, stderr).

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
            result = (p.returncode, stdout, stderr)
            if cb is not None:
                cb(*result)
            ret[f] = result

        return ret

    def run(self, linter_configuration, files, cb):
        """Run the linter specified at linter_configuration.

        :param linter_configuration: dict, Linter configuration, parsed from
                                     autolint configuration file.
        :param files: iterable of files to be linted at this run.
        :param cb: callable to be called after every run of the linter, passed
                   to self._execute.

        :return see self.execute return.
        """

        cmd = [linter_configuration['cmd']]
        if 'flags' in linter_configuration:
            for flag in linter_configuration['flags']:
                cmd.append(flag)
        return self._execute(cmd, files, cb)
