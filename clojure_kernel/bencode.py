import codecs
from typing import Tuple
import bencode
import curio

async def write_to_stream(stream: curio.io.StreamBase, input_: curio.Queue):
    try:
        async for val in input_:
            await stream.write(val)
    except curio.CancelledError:
        await stream.close()

async def read_from_stream(stream: curio.io.StreamBase, output: curio.Queue):
    while True:
        val = await stream.read()
        await output.put(val)

async def open_connection_queues(host, port):
    soc = await curio.open_connection(host, port)
    input_, output = curio.Queue(), curio.Queue()
    stream = soc.as_stream()
    await curio.spawn(write_to_stream, stream, input_, daemon=True)
    await curio.spawn(read_from_stream, stream, output, daemon=True)
    return input_, output

async def map_existing_queue(func, queue, transformed_queue):
    """
    Grabs values from queue, applies f to them, puts them on
    transformed_queue.
    """
    async for val in queue:
        await transformed_queue.put(func(val))

async def map_queue(func, queue, input_):
    """
    Returns a new queue.

    If input_ is true, takes values off of the new queue returned,
    applies f to them and puts them on the passed in queue.abs
    If false, the reverse is performed.
    """
    new_queue = curio.Queue()
    if input_:
        from_queue = new_queue
        to_queue = queue
    else:
        from_queue = queue
        to_queue = new_queue
    await curio.spawn(map_existing_queue, func, from_queue, to_queue, daemon=True)
    return new_queue

async def bencode_decode(string_queue):
    bencode_queue = curio.Queue()
    async def bencode_decode_async():
        buffer = ''
        offset = 1
        async for string in string_queue:
            if not string:
                continue
            buffer += string
            # We start from the begining of the buffer and try parsing each sub
            # string until we reach the end.
            while offset <= len(buffer):
                selected = buffer[:offset]
                try:
                    message = bencode.decode(selected)
                except bencode.BencodeDecodeError:
                    offset += 1
                # When we have parsed something, take it off of the buffer, decode it,
                # and put it on the output queue
                else:
                    buffer = buffer[offset:]
                    offset = 1
                    await bencode_queue.put(message)
    await curio.spawn(bencode_decode_async, daemon=True)
    return bencode_queue

async def connect_bencode(host: str, port: int) -> Tuple[curio.Queue, curio.Queue]:
    """
    Returns an input queue and output queue to send and recieve objects
    """
    input_bytes, output_bytes = await open_connection_queues(host, port)

    input_string = await map_queue(lambda s: s.encode(), input_bytes, input_=True)

    decoder = codecs.getincrementaldecoder('utf8')()
    output_string = await map_queue(decoder.decode, output_bytes, input_=False)

    input_bencode = await map_queue(bencode.encode, input_string, input_=True)
    output_bencode = await bencode_decode(output_string)
    return input_bencode, output_bencode
