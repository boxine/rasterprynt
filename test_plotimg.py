import unittest

import plotimg


class PlotimgTest(unittest.TestCase):
    def test_tiff_uncompress(self):
        def tiff_uncompress(b):
            return b''.join(plotimg.tiff_uncompress(b))

        self.assertEqual(tiff_uncompress(b'\x02\xa1\xa2\xa3'), b'\xa1\xa2\xa3')
        self.assertEqual(tiff_uncompress(b'\xfe\xa1'), b'\xa1\xa1\xa1')

        # Example from http://download.brother.com/welcome/docp000771/cv_pth500p700e500_eng_raster_110.pdf
        self.assertEqual(
            tiff_uncompress(b'\xED\x00\xFF\x22\x05\x23\xBA\xBF\xA2\x22\x2B'),

            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x22\x22\x23\xBA\xBF\xA2\x22\x2B'
        )
