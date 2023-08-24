Read and write layered TIFF ImageSourceData and ImageResources tags
===================================================================

Psdtags is a Python library to read and write the Adobe Photoshop(r) specific
ImageResources (#34377) and ImageSourceData (#37724) TIFF tags, which contain
image resource blocks, layer and mask information found in a typical layered
TIFF file created by Photoshop.

The format is specified in the
`Adobe Photoshop TIFF Technical Notes (March 22, 2002)
<https://www.awaresystems.be/imaging/tiff/specification/TIFFphotoshop.pdf>`_
and
`Adobe Photoshop File Formats Specification (November 2019)
<https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/>`_.

Adobe Photoshop is a registered trademark of Adobe Systems Inc.

:Author: `Christoph Gohlke <https://www.cgohlke.com>`_
:License: BSD 3-Clause
:Version: 2023.8.24
:DOI: `10.5281/zenodo.7879187 <https://doi.org/10.5281/zenodo.7879187>`_

Quickstart
----------

Install the psdtags package and all dependencies from the
`Python Package Index <https://pypi.org/project/psdtags/>`_::

    python -m pip install -U psdtags[all]

View the layer image and metadata stored in a layered TIFF file::

    python -m psdtags file.tif

See `Examples`_ for using the programming interface.

Source code, examples, and support are available on
`GitHub <https://github.com/cgohlke/psdtags>`_.

Requirements
------------

This revision was tested with the following requirements and dependencies
(other versions may work):

- `CPython <https://www.python.org>`_ 3.9.13, 3.10.11, 3.11.5, 3.12rc
- `NumPy <https://pypi.org/project/numpy/>`_ 1.25.2
- `Imagecodecs <https://pypi.org/project/imagecodecs/>`_ 2023.8.12
  (required for compressing/decompressing image data)
- `Tifffile <https://pypi.org/project/tifffile/>`_ 2023.8.12
  (required for reading/writing tags from/to TIFF files)
- `Matplotlib <https://pypi.org/project/matplotlib/>`_ 3.7.2
  (required for plotting)

Revisions
---------

2023.8.24

- Fix channel data in layer and pattern blocks must be in big-endian order.

2023.6.15

- Use PsdThumbnailFormat enum for PsdThumbnailBlock.format.

2023.4.30

- Few API changes (breaking).
- Improve object repr.
- Drop support for Python 3.8 and numpy < 1.21 (NEP29).

2023.2.18

- Allow unknown PsdKeys (#5).

2023.2.8

- Change PsdPoint and PsdReferencePoint signatures (breaking).
- Add helper function to create composite from layers.

2022.8.25

- Update metadata.

2022.2.11

- Fix struct padding.
- Support TiffImageResources.

2022.2.2

- Various API changes (breaking).
- Handle additional layer information.
- Preserve structures of unknown format as opaque bytes.
- Add options to skip tag structures of unknown format.
- Add abstract base class for tag structures.
- Add classes for many structures.

2022.1.18

- Various API changes (breaking).
- Various fixes for writing TiffImageSourceData.
- Support filter masks.
- Add option to change channel compression on write.
- Warn when skipping ResourceKey sections.

2022.1.14

- Initial release.

Notes
-----

The API is not stable yet and might change between revisions.

This library has been tested with a limited number of files only.

Additional layer information is not yet supported.

Consider `psd-tools <https://github.com/psd-tools/psd-tools>`_ and
`pytoshop <https://github.com/mdboom/pytoshop>`_  for working with
Adobe Photoshop PSD files.

See also `Reading and writing a Photoshop TIFF <https://www.amyspark.me/blog/
posts/2021/11/14/reading-and-writing-tiff-psds.html>`_

Examples
--------

Read the ImageSourceData tag value from a layered TIFF file and iterate over
all the channels:

>>> isd = TiffImageSourceData.fromtiff('layered.tif')
>>> for layer in isd.layers:
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

Read the ImageResources tag value from the TIFF file, iterate over the blocks,
and get the thumbnail image:

>>> res = TiffImageResources.fromtiff('layered.tif')
>>> for block in res.blocks:
...     blockname = block.name
>>> res.thumbnail().shape
(90, 160, 3)

Write the image, ImageSourceData and ImageResources to a new layered TIFF file:

>>> from tifffile import imread, imwrite
>>> image = imread('layered.tif')
>>> imwrite(
...     '_layered.tif',
...     image,
...     byteorder=isd.byteorder,  # must match ImageSourceData
...     photometric='rgb',  # must match ImageSourceData
...     metadata=None,  # do not write any tifffile specific metadata
...     extratags=[isd.tifftag(), res.tifftag()],
... )

Verify that the new layered TIFF file contains readable ImageSourceData:

>>> assert isd == TiffImageSourceData.fromtiff('_layered.tif')
>>> assert res == TiffImageResources.fromtiff('_layered.tif')

View the layer and mask information as well as the image resource blocks in
a layered TIFF file from a command line::

    python -m psdtags layered.tif

Refer to the `layered_tiff.py` example in the source distribution for
creating a layered TIFF file from individual layer images.
