# rasterprynt

rasterprynt is a Python library and program to print raster graphics on various label printers. As of writing, the following printers are supported:

- Brother PT P950NW
- Brother PT 9800PCN

This uses an undocumented reverse-engineered protocol, similar to the one in use by [brother_ql](https://github.com/pklaus/brother_ql/tree/master/brother_ql).

At the moment, the tape width is fixed at 18mm and the quality as high, but patches are always welcome.

## Usage

The main method is `rasterprynt.print`, which takes a list of images. Cuts will be inserted in between the images.

    import rasterprynt

    from Pillow import Image

    img = Pillow.open('image.png')
    data = rasterprynt.print(ip='192.168.1.123', [img, img, img])
