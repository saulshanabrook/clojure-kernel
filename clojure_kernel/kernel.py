import curio
import curio.subprocess
import curio.meta
import re
from ipykernel.kernelbase import Kernel


from . import __version__
from .bencode import connect_bencode

LEIN_COMMAND = ['lein', 'repl', ':headless', 'true']
LEIN_REGEX = re.compile(r"nREPL server started on port (\d+)")

async def lein_subprocess():
    """
    Starts a headless lein nrepl and returns two queueus.
    The first will just have the port on it when it is parsed from stdout
    and the second will have all lines of stdout
    """
    port_queue = curio.Queue()
    stdout_queue = curio.Queue()

    async def lein_subprocess_async():
        p = curio.subprocess.Popen(LEIN_COMMAND, stdout=curio.subprocess.PIPE, stderr=curio.subprocess.PIPE)
        await curio.spawn(process_queue_async, stdout_queue.put, p.stderr, daemon=True)
        async for line in p.stdout:
            line_str = line.decode('ascii')
            await stdout_queue.put(line_str)
            match = LEIN_REGEX.search(line_str)
            if match:
                await port_queue.put(int(match.group(1)))

    await curio.spawn(lein_subprocess_async, daemon=True)
    return port_queue, stdout_queue

async def process_queue(func, queue):
    async for val in queue:
        func(val)

async def process_queue_async(func, queue):
    async for val in queue:
        await func(val)


class NreplConnection(curio.meta.AsyncObject):
    async def __init__(self, host, port):
        self.bencode_input, bencode_output = await connect_bencode(host, port)

        self.value_queue = curio.Queue()
        self.out_queue = curio.Queue()
        self.error_queue = curio.Queue()
        self.exception_queue = curio.Queue()
        self.other_queue = curio.Queue()

        self._done_event = curio.Event()
        await self._reset_operation_state()
        await curio.spawn(process_queue_async, self.message_recieved, bencode_output, daemon=True)

    async def _reset_operation_state(self):
        await self._done_event.set()
        self._encountered_error = None

    async def message_recieved(self, message):
        if 'status' in message and 'done' in message['status']:
            await self._done_event.set()
        elif 'value' in message:
            await self.value_queue.put(message['value'])
        elif 'out' in message:
            await self.out_queue.put(message['out'])
        elif 'ex' in message:
            self._encountered_error = message['ex']
            await self.exception_queue.put(message['ex'])
        elif 'err' in message:
            await self.error_queue.put(message['err'])
        else:
            await self.other_queue.put(message)

    async def run_operation(self, operation, **parameters):
        assert self._done_event.is_set()
        self._done_event.clear()
        await self.bencode_input.put({"op": operation, **parameters})
        await self._done_event.wait()
        encountered_error = self._encountered_error
        await self._reset_operation_state()
        return encountered_error

    async def eval(self, code):
        return await self.run_operation("eval", code=code)

    async def cleanup(self):
        # don't use eval because we can't wait for response because process exits
        await self.bencode_input.put({"op": "eval", "code": "(System/exit 0)"})

class ClojureKernel(Kernel):
    implementation = 'Clojure'
    implementation_version = __version__
    language = 'Clojure'

    language_version = 'TODO: get from nrepl if possible'
    language_info = {
        'name': 'clojure',
        'mimetype': 'text/x-clojure',
        'file_extension': '.clj',
    }
    kernel_json = {
        "argv": ["clojure-kernel", "-f", "{connection_file}"],
        "display_name": "Clojure",
        "language": "clojure",
        "mimetype": "text/x-clojure",
        "name": "clojure",
    }
    banner = ''
    kernel = None

    def start_loop(self):
        self.kernel = curio.Kernel()
        self.kernel.run(self.start_loop_async())

    async def start_loop_async(self):
        self.on_out("$ " + ' '.join(LEIN_COMMAND)+ "\n")
        port_queue, stdout_queue = await lein_subprocess()
        await curio.spawn(process_queue, self.on_out, stdout_queue, daemon=True)
        port = await port_queue.get()

        self.nrepl_connection = await NreplConnection('localhost', port)
        await curio.spawn(process_queue, self.on_value, self.nrepl_connection.value_queue, daemon=True)
        await curio.spawn(process_queue, self.on_out, self.nrepl_connection.out_queue, daemon=True)
        await curio.spawn(process_queue, self.on_error, self.nrepl_connection.error_queue, daemon=True)
        await curio.spawn(process_queue, self.on_exception, self.nrepl_connection.exception_queue, daemon=True)
        await curio.spawn(process_queue, self.on_other, self.nrepl_connection.other_queue, daemon=True)

    def on_value(self, value):
        self.send_response(self.iopub_socket, 'execute_result', {
            'data': {'text/plain': value},
            'metadata': {},
            'execution_count': self.execution_count
        })

    def on_out(self, out):
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': out
        })

    def on_error(self, error):
        self.send_response(self.iopub_socket, 'error', {
            'ename': '',
            'evalue': '',
            'traceback': [error]
        })

    def on_exception(self, exception):
        self.send_response(self.iopub_socket, 'error', {
            'ename': exception,
            'evalue': '',
            'traceback': []
        })

    def on_other(self, message):
        self.on_out(str(message) + "\n")

    def do_shutdown(self, restart):
        self.kernel.run(self.nrepl_connection.cleanup, shutdown=True)
        if restart:
            self.start_loop()
        return super().do_shutdown(restart)


    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        if not self.kernel:
            self.start_loop()
        encountered_error = self.kernel.run(self.nrepl_connection.eval, code)
        if encountered_error:
            return {
                'status': 'error',
                'ename': '',
                'evalue': '',
                'traceback': [encountered_error]
            }
        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }
