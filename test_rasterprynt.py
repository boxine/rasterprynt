import unittest

import rasterprynt


class RasterpryntTest(unittest.TestCase):
    def test_compress_tiff(self):
        def _compress_tiff(b):
            return b''.join(rasterprynt._compress_tiff(b))

        self.assertEqual(_compress_tiff(b''), b'')
        self.assertEqual(_compress_tiff(b'a'), b'\x00a')
        self.assertEqual(_compress_tiff(b'aaa'), b'\xfea')
        self.assertEqual(_compress_tiff(b'aaaaaa'), b'\xfba')
        self.assertEqual(_compress_tiff(b'aaaaaabbb'), b'\xfba\xfeb')
        self.assertEqual(_compress_tiff(b'aaaaaaxybbb'), b'\xfba\x01xy\xfeb')
        self.assertEqual(_compress_tiff(b'abcdef'), b'\x05abcdef')
        self.assertEqual(_compress_tiff(b'aaaabbbbbbbccccaadef'), b'\xfda\xfab\xfdc\xffa\x02def')

        # Example from the spec
        self.assertEqual(_compress_tiff(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x22\x22\x23\xBA\xBF\xA2\x22\x2B'
        ),  b'\xED\x00\xff\x22\x05\x23\xBA\xBF\xA2\x22\x2B')
