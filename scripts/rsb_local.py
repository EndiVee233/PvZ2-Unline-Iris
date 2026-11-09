"""Read RSB v4 groups and replace their payloads without changing resource IDs."""

from io import BytesIO
import json
import struct
import zlib


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def align(data):
    return data + bytes(-len(data) % 4096)


class ResourceBundle:
    def __init__(self, data, read_index, write_index):
        if data[:8] != b'1bsr\x04\0\0\0':
            raise ValueError('Expected RSB v4')
        self.data = data
        self.write_index = write_index
        self.groups = {}
        self.files = {}
        count, start, stride = struct.unpack_from('<III', data, 40)
        pool_count, self.pool_start, self.pool_stride = struct.unpack_from('<III', data, 72)
        self.texture_count, self.texture_start, self.texture_stride = struct.unpack_from('<III', data, 84)
        if stride != 204 or pool_count != count or self.pool_stride != 152 or self.texture_stride < 16:
            raise ValueError('Unsupported RSB tables')
        for index in range(count):
            row = start + index * stride
            name = data[row:row + 128].split(b'\0', 1)[0].decode('ascii')
            offset, length = struct.unpack_from('<II', data, row + 128)
            block = memoryview(data)[offset:offset + length]
            if len(block) != length or bytes(block[:4]) != b'pgsr':
                raise ValueError(f'Invalid RSG {name}')
            entries = dict(read_index(block, u32(block, 76), u32(block, 72), 1))
            self.groups[name] = (index, row, block, entries)
            for entry in entries:
                self.files.setdefault(entry, []).append(name)

    @staticmethod
    def section(block, kind):
        offset, packed, raw = struct.unpack_from('<III', block, 40 if kind else 24)
        data = block[offset:offset + packed]
        result = zlib.decompress(data) if packed and u32(block, 16) & (1 if kind else 2) else bytes(data)
        if len(result) != raw:
            raise ValueError('Invalid RSG section length')
        return result

    def group_for(self, path):
        group, = self.files[path]
        return group

    def read(self, group, path):
        _, _, block, entries = self.groups[group]
        kind, offset, length, *_ = entries[path]
        data = self.section(block, kind)
        result = data[offset:offset + length]
        if len(result) != length:
            raise ValueError(f'Truncated entry {path}')
        return result

    def manifest(self, decoder):
        path, = (name for name in self.files if name.startswith('PROPERTIES\\RESOURCES') and name.endswith('.RTON'))
        raw = self.read(self.group_for(path), path)
        if raw[:4] != b'RTON':
            raise ValueError('Expected a plain resource manifest')
        stream = BytesIO(raw[4:])
        stream.name = path
        return json.loads(decoder(repairFiles=False).parse_root_object(stream))

    def texture_row(self, group, path):
        _, row, _, entries = self.groups[group]
        count, first = struct.unpack_from('<II', self.data, row + 196)
        kind, _, _, index, *_ = entries[path]
        if kind != 1 or index >= count or first + index >= self.texture_count:
            raise ValueError(f'Invalid texture slot {path}')
        return self.texture_start + (first + index) * self.texture_stride

    def texture(self, group, path):
        return struct.unpack_from('<4I', self.data, self.texture_row(group, path))

    def replace(self, replacements, rgba_paths):
        result = bytearray(self.data)
        for group, updates in replacements.items():
            index, row, block, entries = self.groups[group]
            sections = [bytearray(self.section(block, kind)) for kind in (0, 1)]
            new_entries = dict(entries)
            for path, raw in updates.items():
                kind, offset, length, *extra = entries[path]
                if len(raw) == length:
                    sections[kind][offset:offset + length] = raw
                else:
                    offset = len(sections[kind])
                    sections[kind].extend(align(raw))
                new_entries[path] = (kind, offset, len(raw), *extra)
                if (group, path) in rgba_paths:
                    width, height, _, _ = self.texture(group, path)
                    if len(raw) != width * height * 4:
                        raise ValueError(f'Invalid RGBA length for {path}')
                    struct.pack_into('<II', result, self.texture_row(group, path) + 8, width * 4, 0)
            head = bytearray(block[:u32(block, 24)])
            table = self.write_index(new_entries.items(), 1)
            start = u32(head, 76)
            if start + len(table) > len(head):
                raise ValueError(f'RSG table exceeds header for {group}')
            head[start:start + len(table)] = table
            struct.pack_into('<I', head, 72, len(table))
            plain, textures = (align(section) for section in sections)
            # Keep both RSG sections uncompressed. Mirror their offsets and sizes
            # into the outer RSB tables that allocate the runtime resource pools.
            struct.pack_into('<I', head, 16, u32(head, 16) & ~3)
            struct.pack_into('<II', head, 28, len(plain), len(plain))
            struct.pack_into('<III', head, 40, len(head) + len(plain), len(textures), len(textures))
            payload = head + plain + textures
            result.extend(bytes(-len(result) % 4096))
            struct.pack_into('<II', result, row + 128, len(result), len(payload))
            result[row + 140:row + 176] = head[16:36] + head[32:36] + head[40:52]
            pool = self.pool_start + index * self.pool_stride
            struct.pack_into('<II', result, pool + 128, len(head) + len(plain), len(textures))
            result.extend(payload)
        return result
