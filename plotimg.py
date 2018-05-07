#!/usr/bin/env python3

import argparse
import struct


MODE_ESCP = 0x00
MODE_RASTER = 0x01
MODE_PTOUCH = 0x02
COMPRESSION_RAW = 0
COMPRESSION_TIFF = 2


def hexstr(b):
    return ' '.join('%02x' % byte for byte in b)


def tiff_uncompress(data):
    """ Yields the bytes in compressed TIFF format """
    p = 0
    while p < len(data):
        num = struct.unpack('!b', data[p:p+1])[0]
        if num < 0:
            count = (- num) + 1
            repeat = data[p + 1:p + 2]
            yield repeat * count
            p += 2
        else:
            dlen = num + 1
            yield data[p + 1:p + 1 + dlen]
            p += 1 + dlen


def read_rows(bc):
    """ Read rows from the brother commands (as one bytes object) bc """
    p = 0

    # Skip zeroes at the start (if present)
    while bc[p] == 0:
        p += 1

    mode = 0x02  # P-Touch
    margin = 0
    compression_mode = None
    mirroring = False

    rows = []
    while p < len(bc):
        if mode == MODE_RASTER and bc[p] == ord('M'):  # Select compression mode
            compression_mode = bc[p + 1]
            assert compression_mode in (COMPRESSION_RAW, COMPRESSION_TIFF)
            p += 2
            continue
        elif mode == MODE_RASTER and bc[p] == ord('Z'):  # Zero raster graphics
            rows.append('empty')
            p += 1
            continue
        elif mode == MODE_RASTER and bc[p] == ord('G'):  # Seems to be the same as g?
            dlen = struct.unpack('<H', bc[p + 1:p + 3])[0]
            p += 3
            img_data = bc[p:p + dlen]
            p += dlen
            if compression_mode == COMPRESSION_TIFF:
                binrow = b''.join(tiff_uncompress(img_data))
            elif compression_mode == COMPRESSION_RAW:
                binrow = img_data
            else:
                raise ValueError('Invalid compression mode %r' % compression_mode)
            row = []
            for c in binrow:
                for bit in range(8):
                    v = (c >> (7 - bit)) & 0x01
                    col = (0, 0, 0) if v else (255, 255, 255)
                    row.append(col)
            rows.append(row)
            continue
        elif bc[p] == 0xff:  # Print command
            p += 1
            continue
        elif mode == MODE_RASTER and bc[p] == 0x1a:  # Print Command with feeding
            p += 1
            continue

        # ESC code
        if bc[p] != 0x1b:
            raise ValueError(
                'Invalid control character: Expected ESC; got 0x%02x at position 0x%x' % (bc[p], p))

        p += 1
        cmd = bc[p]

        if cmd == ord('@'):
            pass  # Initialize
        elif cmd == ord('i'):
            p += 1
            subcmd = bc[p]

            if subcmd == ord('a'):  # Switch command mode
                p += 1
                mode = bc[p]
                assert mode in (MODE_ESCP, MODE_RASTER, MODE_PTOUCH)
            elif subcmd == ord('U'):  # Serial bus configuration
                p += 1
                subsubcmd = bc[p]

                if subsubcmd == ord('B'):
                    p += 1  # Baud rate - we don't care
                elif mode == MODE_RASTER and subsubcmd == ord('J'):  # TODO ??
                    p += 14
                else:
                    raise NotImplementedError(
                        'Unsupported bus subsubcommand of iU in mode %s: %s / 0x%02x' %
                        (mode, chr(subsubcmd), subsubcmd))
            elif mode == MODE_RASTER and subcmd == ord('z'):
                print('Print information command: %s' % hexstr(bc[p+1:p+11]))
                p += 10
            elif mode == MODE_RASTER and subcmd == ord('A'):  # TODO ??
                print('Unknown command iA, args %s' % hexstr(bc[p+1:p+2]))
                p += 1
            elif mode == MODE_RASTER and subcmd == ord('k'):  # TODO ??
                print('Unknown command ik, args %s' % hexstr(bc[p+1:p+4]))
                p += 3
            elif mode == MODE_RASTER and subcmd == ord('K'):  # Advanced Mode settings
                p += 1  # we don't care
            elif mode == MODE_RASTER and subcmd == ord('d'):  # Margin
                margin = struct.unpack('<H', bc[p + 1:p + 3])[0]
                p += 2
            elif subcmd == ord('M'):  # Various Mode Settings
                p += 1
                rest_bits = bc[p] & 0x9f
                if rest_bits != 0:
                    raise NotImplementedError('Strange bits in Various Mode settings: 0x%02x' % bc[p])
                mirroring = (bc[p] & 0x4) != 0
            else:
                raise NotImplementedError(
                    'Unsupported subcommand i %s / 0x%02x in mode %s' %
                    (chr(subcmd), subcmd, mode))
        else:
            raise NotImplementedError('Unsupported command %s / 0x%02x' % (chr(cmd), cmd))

        p += 1

    print('margin: %r' % margin)

    assert len(rows) > 0
    rows = ['empty'] * margin + rows + ['empty'] * margin
    max_len = max(len(r) for r in rows if r != 'empty')
    rows = [[(0xff, 0xff, 0xff)] * max_len if r == 'empty' else r for r in rows]
    assert all(len(r) == max_len for r in rows)

    if not mirroring:
        for r in rows:
            r.reverse()

    return rows


def plotimg(rows):
    """ Returns the netbpm image as bytes """

    height = len(rows)
    width = len(rows[0])
    assert all(all(c in ((0, 0, 0), (255, 255, 255)) for c in row) for row in rows)

    return (
        b'P1\n' +
        ('%d %d\n' % (width, height)).encode('ascii') +
        b'\n'.join(b' '.join(b'1' if cell == (0, 0, 0) else b'0' for cell in row) for row in rows)
    )


def main():
    parser = argparse.ArgumentParser('Plot the image which is going to be printed')
    parser.add_argument(
        'input', metavar='INPUT_FILE',
        help='The .bin file of instructions to the Brother printer')
    parser.add_argument(
        'output', metavar='OUTPUT_FILE',
        help='An netbpm output file')
    args = parser.parse_args()

    with open(args.input, 'rb') as input_f:
        bc = input_f.read()

    rows = read_rows(bc)

    height = len(rows)
    width = len(rows[0])
    print('width: %s, height: %s' % (width, height))

    img_bytes = plotimg(rows)

    with open(args.output, 'wb') as output_f:
        output_f.write(img_bytes)


if __name__ == '__main__':
    main()
