from IPython.kernel.zmq.kernelbase import Kernel
from oct2py import octave

import signal
from subprocess import check_output
import re

__version__ = '0.1'

version_pat = re.compile(r'version (\d+(\.\d+)+)')


class OctaveKernel(Kernel):
    implementation = 'octave_kernel'
    implementation_version = __version__
    language = 'octave'
    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = None
    @property
    def banner(self):
        if self._banner is None:
            self._banner = check_output(['octave', '--version']).decode('utf-8')
        return self._banner

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        # Signal handlers are inherited by forked processes, and we can't easily
        # reset it from the subprocess. Since kernelapp ignores SIGINT except in
        # message handlers, we need to temporarily reset the SIGINT handler here
        # so that octave and its children are interruptible.
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            self.octavewrapper = octave
        finally:
            signal.signal(signal.SIGINT, sig)

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        if code.strip() == 'exit':
            # TODO: exit gracefully here

        interrupted = False
        try:
            output = self.octavewrapper._eval([code.rstrip()])
        except KeyboardInterrupt:
            self.octavewrapper._session.proc.send_signal(signal.SIGINT)
            interrupted = True
            # TODO: handle the output
            output = 'Interrupted'
            #self.bashwrapper._expect_prompt()
            #output = self.bashwrapper.child.before

        if not silent:
            stream_content = {'name': 'stdout', 'data': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}

        try:
            # TODO: handle an exit code
            exitcode = 0
            #exitcode = int(self.run_command('echo $?').rstrip())
        except Exception:
            exitcode = 1

        if exitcode:
            return {'status': 'error', 'execution_count': self.execution_count,
                    'ename': '', 'evalue': str(exitcode), 'traceback': []}
        else:
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

if __name__ == '__main__':
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=OctaveKernel)
