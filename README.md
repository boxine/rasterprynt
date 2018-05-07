# rasterprynt

rasterprynt is a Python library and program to print raster graphics on various label printers. As of writing, the following printers are supported:

- Brother PT P950NW
- Brother PT 9800PCN

This uses an undocumented reverse-engineered protocol, similar to the one in use by [brother_ql](https://github.com/pklaus/brother_ql/tree/master/brother_ql).

At the moment, the tape width is fixed at 18mm and the quality as high, but patches are always welcome.

## Installation

As a depency, depend on the PyPi package `rasterprynt`. To install dependencies for a command-line installation, type

    $ pip install -r requirements.txt

## Command Line Usage

All functionality is available as a command-line program, like this:

   $ python -m rasterprynt 192.168.1.123 img1.png img2.jpg img1.png --top-margin 10

## Library Usage

The main method is `rasterprynt.prynt`, which takes a list of images. Cuts will be inserted in between the images.

    import rasterprynt

    import PIL.Image

    # Enter the IP address of your printer below
    printer_ip = '192.168.1.123'

    img1 = PIL.Image.open('example1.png')
    img2 = PIL.Image.open('example2.png')
    data = rasterprynt.prynt([img1, img2, img1], printer_ip)

## Additional utilities

`plotimg.py` provides a way to do the reverse transformation.