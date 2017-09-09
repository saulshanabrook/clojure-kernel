"""
Clojure nREPL client, capable of evaluating code in a nREPL server.
"""

from .bencode import BencodeProtocol




class NreplProtocol(BencodeProtocol):


    def message_recieved(self, message):

    async def run_operation(self, operation, parameter):
        



async def run_operation(host, port, operation, **parameters):
    reader, writer = await open_bencode_connection(host, port)
    writer.write_message({"op": operation, **parameters})
    try:
        while True:
            val = await reader.read_message()
            yield val
            if 'done' in val.get('status', []):
                break
    finally:
        writer.close()

async def merge_async_generator(gen):
    """
    Takes in an async generator that should yield dictionaries
    and iterates through it merging them all together.
    """
    combined = {}
    async for val in gen:
        combined.update(val)
    return combined

async def eval_code(host, port, code):
    """
    Connects to the nREPL server at `host`:`port` and runs the `code`.

    yields a list of of all the values returned until execution is finished.
    """
    # disable creating session for now because it doesn't seem like we need
    # one, even though the nREPL docs says you do.
    # clone_res = await merge_async_generator(run_operation(host, port, "clone"))
    # session = clone_res['new-session']
    # try:
    async for val in run_operation("eval", code=code): #, session=session
        yield val
    # finally:
    #     await merge_async_generator(run_operation("close", session=session))
