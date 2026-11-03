#!/usr/bin/env python3
"""Read class metadata and instruction-boundary references from standard DEX.

This is a reference extractor, not a Java decompiler. Only Python's standard
library is needed. Unknown/unused opcodes fail rather than produce guesses.
"""
import argparse
import struct
import zipfile


class Dex:
    def __init__(self, data):
        self.data = data
        if data[:4] != b'dex\n' or data[4:7] not in (b'035', b'037', b'038', b'039', b'040'):
            raise ValueError('Unsupported DEX header')
        self.strings = []
        for i in range(self.u32(56)):
            _, start = self.leb(self.u32(self.u32(60) + 4 * i))
            self.strings.append(data[start:data.index(b'\0', start)].decode('utf-8', errors='replace'))
        self.types = [self.strings[self.u32(self.u32(68) + 4 * i)] for i in range(self.u32(64))]
        self.protos = []
        for i in range(self.u32(72)):
            _, ret, params = self.unpack('III', self.u32(76) + 12 * i)
            args = [] if not params else [self.types[self.unpack('H', params + 4 + j * 2)[0]]
                                         for j in range(self.u32(params))]
            self.protos.append('(' + ''.join(args) + ')' + self.types[ret])
        self.fields = []
        for i in range(self.u32(80)):
            cls, typ, name = self.unpack('HHI', self.u32(84) + 8 * i)
            self.fields.append(self.types[cls] + '->' + self.strings[name] + ':' + self.types[typ])
        self.methods = []
        for i in range(self.u32(88)):
            cls, proto, name = self.unpack('HHI', self.u32(92) + 8 * i)
            self.methods.append(self.types[cls] + '->' + self.strings[name] + self.protos[proto])

    def unpack(self, fmt, offset):
        return struct.unpack_from('<' + fmt, self.data, offset)

    def u32(self, offset):
        return self.unpack('I', offset)[0]

    def leb(self, offset):
        value = shift = 0
        while shift < 35:
            byte = self.data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value, offset
            shift += 7
        raise ValueError('Invalid ULEB128')

    def class_def(self, target):
        for i in range(self.u32(96)):
            row = self.unpack('8I', self.u32(100) + 32 * i)
            if self.types[row[0]] == target:
                return row
        return None

    def print_class(self, target, method_filter):
        row = self.class_def(target)
        if row is None:
            return False
        print('CLASS', target)
        cursor = row[6]
        if not cursor:
            return True
        sizes = []
        for _ in range(4):
            size, cursor = self.leb(cursor)
            sizes.append(size)
        for group in range(4):
            index = 0
            for _ in range(sizes[group]):
                delta, cursor = self.leb(cursor)
                index += delta
                flags, cursor = self.leb(cursor)
                if group < 2:
                    print(' FIELD', self.fields[index], 'flags=' + hex(flags))
                    continue
                code, cursor = self.leb(cursor)
                if method_filter and method_filter not in self.methods[index]:
                    continue
                print(' METHOD', self.methods[index], 'flags=' + hex(flags), 'code=' + hex(code))
                if code:
                    count = self.u32(code + 12)
                    units = self.unpack(str(count) + 'H', code + 16)
                    self.print_references(units)
        return True

    def print_references(self, units):
        pc = 0
        while pc < len(units):
            op = units[pc] & 255
            width = instruction_width(units, pc)
            if pc + width > len(units):
                raise ValueError('Truncated instruction at ' + hex(pc * 2))
            prefix = '  ' + hex(pc * 2)
            if op in (0x1a, 0x1b):
                index = units[pc + 1] | ((units[pc + 2] << 16) if op == 0x1b else 0)
                print(prefix, 'const-string', repr(self.strings[index]))
            elif op in range(0x6e, 0x73) or op in range(0x74, 0x79):
                print(prefix, 'invoke', self.methods[units[pc + 1]])
            elif op in range(0x52, 0x6e):
                print(prefix, 'field-ref', self.fields[units[pc + 1]])
            elif op in (0x1c, 0x1f, 0x20, 0x22, 0x23, 0x24, 0x25):
                print(prefix, 'type-ref', self.types[units[pc + 1]])
            pc += width


def instruction_width(units, pc):
    word = units[pc]
    op = word & 255
    if op == 0 and word != 0:
        if word == 0x100:
            return 4 + 2 * units[pc + 1]
        if word == 0x200:
            return 2 + 4 * units[pc + 1]
        if word == 0x300:
            size = units[pc + 2] | (units[pc + 3] << 16)
            return 4 + (size * units[pc + 1] + 1) // 2
        raise ValueError('Unknown payload: ' + hex(word))
    if op in (0x18,):
        return 5
    if op in (0xfa, 0xfb):
        return 4
    if op in (0x03, 0x06, 0x09, 0x14, 0x17, 0x1b, 0x24, 0x25, 0x26, 0x2a, 0x2b, 0x2c, 0xfc, 0xfd) or op in range(0x6e, 0x73) or op in range(0x74, 0x79):
        return 3
    if op in (0x02, 0x05, 0x08, 0x13, 0x15, 0x16, 0x19, 0x1a, 0x1c, 0x1f, 0x20, 0x22, 0x23, 0x29, 0xfe, 0xff) or op in range(0x2d, 0x3e) or op in range(0x44, 0x6e) or op in range(0x90, 0xb0) or op in range(0xd0, 0xe3):
        return 2
    if op in (0x00, 0x01, 0x04, 0x07, 0x1d, 0x1e, 0x21, 0x27, 0x28) or op in range(0x0a, 0x13) or op in range(0x7b, 0x90) or op in range(0xb0, 0xd0):
        return 1
    raise ValueError('Unsupported/unused opcode: ' + hex(op) + ' at ' + hex(pc * 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', help='JAR/APK containing standard DEX files')
    parser.add_argument('--class-name', default='android.app.MuMuImeBlackList')
    parser.add_argument('--method', default='')
    args = parser.parse_args()
    target = 'L' + args.class_name.replace('.', '/') + ';'
    with zipfile.ZipFile(args.archive) as archive:
        for name in archive.namelist():
            if name.endswith('.dex') and Dex(archive.read(name)).print_class(target, args.method):
                print('DEX', name)
                return
    raise SystemExit('Class not found: ' + target)


if __name__ == '__main__':
    main()
