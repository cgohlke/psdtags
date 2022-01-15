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

:Version: 2022.1.14

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
2022.1.14
    Initial release.

Notes
-----

The API is not stable yet and might change between revisions.

This module has been tested with a limited number of files only.

Consider `psd-tools <https://github.com/psd-tools/psd-tools>`_ and
`pytoshop <https://github.com/mdboom/pytoshop>`_  for working with
Adobe Photoshop PSD files.

Examples
--------
Read the ImageSourceData tag value from a layered TIFF file and iterate over
all the channels:

>>> isd = TiffImageSourceData.fromtiff('LayeredTiff.tif')
>>> for layer in isd.layers:
...     layer.name
...     for channel in layer.channels:
...         ch = channel.data
'Background'
'Reflect1'
'Reflect2'
'image'
'Layer 1'
'ORight'
'I'
'IShadow'
'O'

To view the layer and mask information in a layered TIFF file from a
command line, run::

    python -m psdtags LayeredTiff.tif
