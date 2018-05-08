import rasterprynt

import PIL.Image

# Enter the IP address of your printer below
printer_ip = '192.168.1.123'

img1 = PIL.Image.open('example1.png')
img2 = PIL.Image.open('example2.png')
data = rasterprynt.prynt([img1, img2, img1], printer_ip)
