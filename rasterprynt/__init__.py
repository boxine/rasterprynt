#!/usr/bin/env python
from __future__ import unicode_literals


import argparse
import collections
import contextlib
import logging
import socket
import struct
import time

try:
    from urllib.request import urlopen
except ImportError:  # Python 2
    from urllib2 import urlopen
try:
    from urllib.error import URLError
except ImportError:  # Python 2
    from urllib2 import URLError


__version__ = '1.0.5'

logger = logging.getLogger('rasterprynt')

# Size of a stripe (height in Brother-talk)
STRIPE_SIZE = {
    ('P950NW', '18mm'): 408,
    ('P950NW', '36mm'): 536,
    ('9800PCN', '18mm'): 312,
}
STRIPE_SIZE_DEFAULT = STRIPE_SIZE[('P950NW', '18mm')]
TAPE_SIZE_DEFAULT = '18mm'


TOP_MARGIN_DEFAULT = 8
BOTTOM_MARGIN_DEFAULT = 8

# Cache of IP address -> model name
CACHE_TIMEOUT = 3600  # 1 hour
PrinterCacheEntry = collections.namedtuple('PrinterCacheEntry', ['ip', 'timestamp', 'model'])
_PRINTER_BY_IP = {}


def detect_printer_model(ip):
    cached = _PRINTER_BY_IP.get(ip)
    if cached and cached.timestamp + CACHE_TIMEOUT < time.time():
        return cached.model

    try:
        res_model = _detect_printer_model_uncached(ip)
    except URLError as urle:
        logging.warning('Failed to detect printer at %s: %s' % (ip, urle))
        return 'error'
    if res_model:
        _PRINTER_BY_IP[ip] = PrinterCacheEntry(ip, time.time(), res_model)
    return res_model


def _detect_printer_model_uncached(ip):
    # We use /admin/default.html because this seems to be the only common URL for both supported printers so far
    test_url = 'http://%s/admin/default.html' % ip
    try:
        with contextlib.closing(urlopen(test_url)) as url_handle:
            html = url_handle.read()
    except URLError as urle:
        if hasattr(urle, 'code') and urle.code == 401:
            html = urle.read()
        else:
            raise

    if b'<TITLE>Brother PT-9800PCN</TITLE>' in html:
        return '9800PCN'
    if b'<title>Brother PT-P950NW</title>' in html:
        return 'P950NW'

    return None


# Compress a row of bytes according to Brother's TIFF standard.
# Yields byte that make up the compressed row.
# See page 34 & 36 at http://download.brother.com/welcome/docp000771/cv_pth500p700e500_eng_raster_110.pdf
def _compress_tiff(row):
    pos = 0
    uncompressed_start = pos
    while pos < len(row):
        count = 0
        while pos + count + 1 < len(row) and row[pos + count + 1] == row[pos + count]:
            count += 1

        if count > 0:
            # Flush uncompressed buffer
            if uncompressed_start < pos:
                yield struct.pack('!b', pos - uncompressed_start - 1) + row[uncompressed_start:pos]

            # Output the compressed tag
            yield struct.pack('!bB', -count, row[pos])
            pos += count + 1
            uncompressed_start = pos
        else:
            # Uncompressed buffer continues
            pos += 1

    # Flush remaining uncompressed buffer
    if uncompressed_start < pos:
        yield struct.pack('!b', pos - uncompressed_start - 1) + row[uncompressed_start:pos]


# Scan a line from the image and yield the bytes that make them
def _raw_row(img, img_bytes, stripe_count, x, y_offset):
    for stripe_idx in range(stripe_count):
        bits = 0
        for bit_index in range(8):
            y = stripe_idx * 8 + bit_index - y_offset
            if x < img.width and 0 <= y < img.height:
                color = img_bytes[(x, y)]
                if isinstance(color, int):  # grayscale
                    px = color
                else:  # RGB
                    px = sum(color) / 3
                bits |= (0 if px > 230 else 1) << (7 - bit_index)
        yield struct.pack('!B', bits)


def _get_bytes(img):
    if img.mode == 'P':
        img = img.convert('RGBA')

    if img.mode == 'RGBA':
        from PIL import Image
        # Thanks to https://stackoverflow.com/a/9459208/35070
        new_img = Image.new('RGB', img.size, (255, 255, 255))
        new_img.paste(img, mask=img.split()[3])
        img = new_img

    return img.load()


def render(images, ip=None,
           top_margin=TOP_MARGIN_DEFAULT, bottom_margin=BOTTOM_MARGIN_DEFAULT,
           printer_model=None, tape_size=TAPE_SIZE_DEFAULT):
    # Yields bytes that can be printed on a Brother P950NW(new printer) or Brother 9800PCN(old printer).
    # The protocol here is reverse-engineered from what the Windows driver for brother printers sends.
    # Many commands are documented at
    #  http://download.brother.com/welcome/docp000771/cv_pth500p700e500_eng_raster_110.pdf
    # The ESC/P command reference at
    #  http://support.brother.com/g/b/manuallist.aspx?c=us&lang=en&prod=p950nweus&flang=English&type3=384&type2=81
    # can also help.
    # Our old code and brother sends 200 0-bytes here (maybe to synchronize the serial bus? No need for that via TCP)

    # We support TIFF, but it seems to introduce artifacts on some printers, so disable it.
    USE_TIFF = False

    yield b'\x00' * 200

    if printer_model is None:
        printer_model = detect_printer_model(ip) if ip else None
    assert printer_model in ('P950NW', '9800PCN')

    # These are the only supported sizes so far
    assert tape_size in ('18mm', '36mm')

    # number of dots in a stripe (depends on printer + tape size)
    stripe_size = STRIPE_SIZE.get((printer_model, tape_size), STRIPE_SIZE_DEFAULT)
    assert stripe_size % 8 == 0
    stripe_count = stripe_size // 8

    yield b'\x1b@'  # Init
    yield b'\x1bia\x01'  # Raster mode
    yield b'\x1biM\x00'  # Various Mode settings: no auto cut
    yield b'\x1bid\x00\x00'  # Margin = 0

    first = True
    for img in images:
        if first:
            first = False
        else:
            yield b'\x0c'

        img_bytes = _get_bytes(img)

        cut_correction = 0  # Correction factor for cuts: Cuts come this much after we send the signal to cut
        if printer_model == 'P950NW':
            # The "raster number" seems to be the width, or length of the stripe
            raster_number = img.width + top_margin + bottom_margin

            yield (
                b'\x1biz'  # Print information command
                b'\xc0' +  # PI_RECOVER | PI_QUALITY
                b'\x00' +  # Media type: not set
                b'\x00' +  # Media width, e.g. 18 = 18mm. We're setting it to 0 (unspecified)
                b'\x00' +  # Media length: not set
                struct.pack('<I', raster_number) +  # "Raster number"
                (b'\x00' if first else b'\x01') +  # Starting page?
                b'\x00')   # This byte is always 0 (reserved)
        elif printer_model == '9800PCN':
            # ?? Some kind of initialization.
            # In our old code, \x01 was labelled "type"
            # \x12 is the media width in mm (i.e. 18mm)
            yield b'\x1bic\x8e\x01\x12\x00\x00'

            # Specify feed amount (correction for overly early cutting)
            yield b'\x1bid' + struct.pack('!B', 0) + b'\x00'
            cut_correction = 8
        else:
            assert False, 'Unsupported printer %s' % printer_model

        if top_margin < cut_correction:
            raise ValueError(
                'top margin %d is smaller than cut correction %d of %s' %
                (top_margin, cut_correction, printer_model))

        if USE_TIFF:
            yield b'M\x02'  # Select compression mode: TIFF
        else:
            yield b'M\x00'  # Select compression mode: Simple

        # Draw margin.
        # For compatibility with different printers, we send empty lines instead of specifying a margin.
        yield b'Z' * (top_margin - cut_correction)

        for x in range(img.width):
            offset = (stripe_size - img.height)

            row = b''.join(_raw_row(img, img_bytes, stripe_count, x, offset))
            assert len(row) == stripe_count
            if USE_TIFF:
                row = b''.join(_compress_tiff(row))

            yield b'G' + struct.pack('<H', len(row))
            yield row

        # Draw bottom margin.
        # For compatibility with different printers, we send empty lines instead of specifying a margin.
        yield b'Z' * (bottom_margin + cut_correction)

    yield b'\x1a'  # Print


def cat(images, ip=None,
        top_margin=TOP_MARGIN_DEFAULT, bottom_margin=BOTTOM_MARGIN_DEFAULT,
        tape_size=TAPE_SIZE_DEFAULT):
    return b''.join(
        render(images, ip=ip, top_margin=top_margin, bottom_margin=bottom_margin, tape_size=tape_size))


def send(data, ip):
    sock = socket.create_connection((ip, 9100))
    sock.sendall(data)
    sock.close()


def prynt(images, ip,
          top_margin=TOP_MARGIN_DEFAULT, bottom_margin=BOTTOM_MARGIN_DEFAULT,
          tape_size=TAPE_SIZE_DEFAULT):
    data = cat(images, ip, top_margin, bottom_margin, tape_size=tape_size)
    send(data, ip)


def main():
    import PIL.Image

    parser = argparse.ArgumentParser('Print images to a Brother P-Touch printer')
    parser.add_argument(
        'ip', metavar='IP', help='IP address (or domain name) of the printer')
    parser.add_argument(
        'image_files', metavar='IMAGE', nargs='*'
    )
    parser.add_argument(
        '--to-file', metavar='FILENAME',
        help='Write the sent binary data to a file instead of printing it')
    parser.add_argument(
        '--detect-device', action='store_true',
        help='Detect which printer is running at the specified IP address')
    parser.add_argument(
        '--top-margin', default=TOP_MARGIN_DEFAULT, metavar='INT', type=int,
        help='Margin before every image, in pixels (default: %(default)s)')
    parser.add_argument(
        '--bottom-margin', default=BOTTOM_MARGIN_DEFAULT, metavar='INT', type=int,
        help='Margin after every image, in pixels (default: %(default)s)')
    parser.add_argument(
        '--tape-size', default=TAPE_SIZE_DEFAULT, metavar='SIZE',
        help='Description of tape size (limited support, default: %(default)s)')
    args = parser.parse_args()

    if args.detect_device:
        if args.image_files:
            parser.error('Images given with --detect-device')
            return

        print(detect_printer_model(args.ip))
        return

    images = [
        PIL.Image.open(img_file) for img_file in args.image_files
    ]
    if not images:
        parser.error('No images given')
        return

    if args.to_file:
        data = cat(
            images, args.ip,
            top_margin=args.top_margin, bottom_margin=args.bottom_margin,
            tape_size=args.tape_size)

        with open(args.to_file, 'wb') as outf:
            outf.write(data)
        return

    prynt(
        images, args.ip,
        top_margin=args.top_margin, bottom_margin=args.bottom_margin,
        tape_size=args.tape_size)


if __name__ == '__main__':
    main()
