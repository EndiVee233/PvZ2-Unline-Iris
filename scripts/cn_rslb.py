"""Read the chunked LZMA RSLB wrapper used by the current CN APK."""
import lzma
import struct


def unpack_rslb(data):
    if data[:4] == b'1bsr':
        return data
    if data[:8] != b'RSLB\x01\0\0\0':
        raise ValueError('Unsupported CN resource wrapper')
    raw_size, packed_size, chunk_size, count = struct.unpack_from('<QQII', data, 8)
    if packed_size + 32 != len(data) or not chunk_size or count != (raw_size + chunk_size - 1) // chunk_size:
        raise ValueError('Invalid RSLB dimensions')
    result = bytearray()
    end = 32 + count * 36
    for index in range(count):
        row = 32 + index * 36
        position, size, offset, packed = struct.unpack_from('<QQQI', data, row)
        props = data[row + 28:row + 33]
        if (position != len(result) or size != min(chunk_size, raw_size - position)
                or offset != end or offset + packed > len(data) or packed < 5
                or data[offset:offset + 5] != props):
            raise ValueError('Invalid RSLB chunk')
        setting = props[0]
        if setting >= 9 * 5 * 5:
            raise ValueError('Invalid LZMA properties')
        filters = [{'id': lzma.FILTER_LZMA1, 'lc': setting % 9,
                    'lp': setting // 9 % 5, 'pb': setting // 45,
                    'dict_size': max(4096, int.from_bytes(props[1:], 'little'))}]
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        block = decoder.decompress(data[offset + 5:offset + packed], max_length=size)
        if len(block) != size:
            raise ValueError('Incomplete RSLB chunk')
        result.extend(block)
        end = offset + packed
    if end != len(data) or len(result) != raw_size or result[:8] != b'1bsr\x04\0\0\0':
        raise ValueError('Invalid decoded RSB')
    return bytes(result)
