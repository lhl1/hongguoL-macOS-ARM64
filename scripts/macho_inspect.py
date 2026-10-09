"""Small read-only Mach-O inventory for architecture, deployment target and linkage checks."""
import struct

def inspect(data):
    if len(data) < 8:
        return []
    magic = data[:4]
    if magic in [b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf']:
        n = struct.unpack_from('>I', data, 4)[0]
        result = []
        for i in range(n):
            if magic == b'\xca\xfe\xba\xbe':
                cpu, sub, offset, size, align = struct.unpack_from('>IIIII', data, 8 + i * 20)
            else:
                cpu, sub, offset, size, align, reserved = struct.unpack_from('>IIQQII', data, 8 + i * 32)
            result.extend(inspect(data[offset:offset+size]))
        return result
    if magic not in [b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xce']:
        return []
    endian = '<' if magic in [b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe'] else '>'
    cpu, subtype, filetype, count, size, flags = struct.unpack_from(endian + '6I', data, 4)
    offset = 32 if magic in [b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf'] else 28
    result = {'arch': {0x100000c:'arm64',0x1000007:'x64'}.get(cpu, hex(cpu)), 'minimumOS': '0.0.0', 'libraries': [], 'rpaths': [], 'codeSignature': False}
    def version(value):
        return '.'.join(str(v) for v in [value>>16,(value>>8)&255,value&255])
    for i in range(count):
        cmd, command_size = struct.unpack_from(endian + 'II', data, offset)
        assert command_size >= 8 and offset + command_size <= len(data)
        base = cmd & 0x7fffffff
        if base in [0xc,0x18,0x1f,0x23,0x20,0x1c]:
            name_offset = struct.unpack_from(endian + 'I', data, offset + 8)[0]
            value = data[offset+name_offset:offset+command_size].split(b'\0')[0].decode('utf8')
            result['rpaths' if base == 0x1c else 'libraries'].append(value)
        elif base == 0x32:
            result['minimumOS'] = version(struct.unpack_from(endian + 'I', data, offset + 12)[0])
        elif base == 0x24:
            result['minimumOS'] = version(struct.unpack_from(endian + 'I', data, offset + 8)[0])
        elif base == 0x1d:
            result['codeSignature'] = True
        offset += command_size
    return [result]
