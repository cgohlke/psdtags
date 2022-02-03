Read and write layered TIFF ImageSourceData and ImageResources tags
===================================================================

Psdtags is a Python library to read and write the Adobe Photoshop(r) specific
ImageResources (#34377) and ImageSourceData (#37724) TIFF tags, which contain
image resource blocks, layer and mask information found in a typical layered
TIFF file created by Photoshop.

The format is specified in the
`Adobe Photoshop TIFF Technical Notes (March 22, 2002)
<https://www.adobe.io/open/standards/TIFF.html>`_
and
`Adobe Photoshop File Formats Specification (November 2019)
<https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/>`_.

Adobe Photoshop is a registered trademark of Adobe Systems Inc.

:Author:
  `Christoph Gohlke <https://www.lfd.uci.edu/~gohlke/>`_

:Organization:
  Laboratory for Fluorescence Dynamics, University of California, Irvine

:License: BSD 3-Clause

:Version: 2022.2.2

:Status: Alpha

Requirements
------------
This release has been tested with the following requirements and dependencies
(other versions may work):

* `CPython 3.8.10, 3.9.10, 3.10.2 64-bit <https://www.python.org>`_
* `Numpy 1.21.5 <https://pypi.org/project/numpy/>`_
* `Imagecodecs 2021.11.20 <https://pypi.org/project/imagecodecs/>`_  (optional)
* `Tifffile 2021.11.2 <https://pypi.org/project/tifffile/>`_  (optional)
* `Matplotlib 3.4.3 <https://pypi.org/project/matplotlib/>`_  (optional)


Revisions
---------
2022.2.2
    Various API changes (breaking).
    Handle additional layer information.
    Preserve structures of unknown format as opaque bytes.
    Add options to skip tag structures of unknown format.
    Add abstract base class for tag structures.
    Add classes for many structures.
2022.1.18
    Various API changes (breaking).
    Various fixes for writing TiffImageSourceData.
    Support filter masks.
    Add option to change channel compression on write.
    Warn when skipping ResourceKey sections.
2022.1.14
    Initial release.

Notes
-----

The API is not stable yet and might change between revisions.

This module has been tested with a limited number of files only.

Additional layer information is not yet supported.

Consider `psd-tools <https://github.com/psd-tools/psd-tools>`_ and
`pytoshop <https://github.com/mdboom/pytoshop>`_  for working with
Adobe Photoshop PSD files.

Examples
--------
Read the ImageSourceData tag value from a layered TIFF file and iterate over
all the channels:

>>> psd = TiffImageSourceData.fromtiff('layered.tif')
>>> for layer in psd.layers:
...     layer.name
...     for channel in layer.channels:
...         ch = channel.data  # a numpy array
'Background'
'Reflect1'
'Reflect2'
'image'
'Layer 1'
'ORight'
'I'
'IShadow'
'O'

Write the image and ImageSourceData to a new layered TIFF file:

>>> from tifffile import imread, imwrite
>>> image = imread('layered.tif')
>>> imwrite(
...     '_layered.tif',
...     image,
...     byteorder=psd.byteorder,  # must match ImageSourceData
...     photometric='rgb',  # must match ImageSourceData
...     metadata=None,  # do not write any tifffile specific metadata
...     extratags=[psd.tifftag()],
... )

Verify that the new layered TIFF file contains readable ImageSourceData:

>>> assert psd == TiffImageSourceData.fromtiff('_layered.tif')

To view the layer and mask information in a layered TIFF file from a
command line, run::

    python -m psdtags layered.tif
