# psdtags/psdtags.py

# Copyright (c) 2022, Christoph Gohlke
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Read and write layered TIFF ImageSourceData and ImageResources tags.

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

:Version: 2022.1.18

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

"""

from __future__ import annotations

__version__ = '2022.1.18'

__all__ = [
    'PsdBlendMode',
    'PsdChannel',
    'PsdChannelId',
    'PsdClippingType',
    'PsdColorSpaceType',
    'PsdCompressionType',
    'PsdFilterMask',
    'PsdFormat',
    'PsdFormatSignatures',
    'PsdImageModes',
    'PsdLayer',
    'PsdLayerFlags',
    'PsdLayerMask',
    'PsdLayerMaskFlags',
    'PsdLayerMaskParameterFlags',
    'PsdLayers',
    'PsdRectangle',
    'PsdResourceKey',
    'PsdUserMask',
    'TiffImageSourceData',
    'read_tifftag',
]


import sys
import os
import io
import enum
import struct
import zlib
import dataclasses

import numpy

from typing import Any, BinaryIO, Literal, Iterable, NamedTuple


class BytesEnumMeta(enum.EnumMeta):
    """Metaclass for bytes enums."""

    def __contains__(cls, value: object) -> bool:
        try:
            cls(value)
        except ValueError:
            return False
        else:
            return True

    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        try:
            # big endian
            c = enum.EnumMeta.__call__(cls, *args, **kwds)
        except ValueError as exc:
            try:
                # little endian
                if args:
                    args = (args[0][::-1],) + args[1:]
                c = enum.EnumMeta.__call__(cls, *args, **kwds)
            except Exception:
                raise exc
        return c


class BytesEnum(bytes, enum.Enum, metaclass=BytesEnumMeta):
    """Base class for bytes enums."""

    def tobytes(self, byteorder: str = '>') -> bytes:
        return self.value if byteorder == '>' else self.value[::-1]


class PsdResourceKey(BytesEnum):
    """Resource keys."""

    ALPHA = b'Alph'
    ANIMATION_EFFECTS = b'anFX'
    ANNOTATIONS = b'Anno'
    ARTBOARD_DATA = b'artb'
    ARTBOARD_DATA_2 = b'artd'
    ARTBOARD_DATA_3 = b'abdd'
    BLACK_AND_WHITE = b'blwh'
    BLEND_CLIPPING_ELEMENTS = b'clbl'
    BLEND_INTERIOR_ELEMENTS = b'infx'
    BRIGHTNESS_AND_CONTRAST = b'brit'
    CHANNEL_BLENDING_RESTRICTIONS_SETTING = b'brst'
    CHANNEL_MIXER = b'mixr'
    COLOR_BALANCE = b'blnc'
    COLOR_LOOKUP = b'clrL'
    COMPOSITOR_INFO = b'cinf'
    CONTENT_GENERATOR_EXTRA_DATA = b'CgEd'
    CURVES = b'curv'
    EFFECTS_LAYER = b'lrFX'
    EXPOSURE = b'expA'
    FILTER_EFFECTS = b'FXid'
    FILTER_EFFECTS_2 = b'FEid'
    FILTER_MASK = b'FMsk'
    FOREIGN_EFFECT_ID = b'ffxi'
    GRADIENT_FILL_SETTING = b'GdFl'
    GRADIENT_MAP = b'grdm'
    HUE_SATURATION = b'hue2'
    HUE_SATURATION_PS4 = b'hue '
    INVERT = b'nvrt'
    KNOCKOUT_SETTING = b'knko'
    LAYER = b'Layr'
    LAYER_16 = b'Lr16'
    LAYER_32 = b'Lr32'
    LAYER_ID = b'lyid'
    LAYER_MASK_AS_GLOBAL_MASK = b'lmgm'
    LAYER_NAME_SOURCE_SETTING = b'lnsr'
    LAYER_VERSION = b'lyvr'
    LEVELS = b'levl'
    LINKED_LAYER = b'lnkD'
    LINKED_LAYER_2 = b'lnk2'
    LINKED_LAYER_3 = b'lnk3'
    LINKED_LAYER_EXTERNAL = b'lnkE'
    METADATA_SETTING = b'shmd'
    NESTED_SECTION_DIVIDER_SETTING = b'lsdk'
    OBJECT_BASED_EFFECTS_LAYER_INFO = b'lfx2'
    PATT = b'patt'
    PATTERNS = b'Patt'
    PATTERNS_2 = b'Pat2'
    PATTERNS_3 = b'Pat3'
    PATTERN_DATA = b'shpa'
    PATTERN_FILL_SETTING = b'PtFl'
    PHOTO_FILTER = b'phfl'
    PIXEL_SOURCE_DATA = b'PxSc'
    PIXEL_SOURCE_DATA_CC15 = b'PxSD'
    PLACED_LAYER = b'plLd'
    PLACED_LAYER_CS3 = b'PlLd'
    POSTERIZE = b'post'
    PROTECTED_SETTING = b'lspf'
    REFERENCE_POINT = b'fxrp'
    SAVING_MERGED_TRANSPARENCY = b'Mtrn'
    SAVING_MERGED_TRANSPARENCY2 = b'MTrn'
    SAVING_MERGED_TRANSPARENCY_16 = b'Mt16'
    SAVING_MERGED_TRANSPARENCY_32 = b'Mt32'
    SECTION_DIVIDER_SETTING = b'lsct'
    SELECTIVE_COLOR = b'selc'
    SHEET_COLOR_SETTING = b'lclr'
    SMART_OBJECT_LAYER_DATA = b'SoLd'
    SMART_OBJECT_LAYER_DATA_CC15 = b'SoLE'
    SOLID_COLOR_SHEET_SETTING = b'SoCo'
    TEXT_ENGINE_DATA = b'Txt2'
    THRESHOLD = b'thrs'
    TRANSPARENCY_SHAPES_LAYER = b'tsly'
    TYPE_TOOL_INFO = b'tySh'
    TYPE_TOOL_OBJECT_SETTING = b'TySh'
    UNICODE_LAYER_NAME = b'luni'
    UNICODE_PATH_NAME = b'pths'
    USER_MASK = b'LMsk'
    USING_ALIGNED_RENDERING = b'sn2P'
    VECTOR_MASK_AS_GLOBAL_MASK = b'vmgm'
    VECTOR_MASK_SETTING = b'vmsk'
    VECTOR_MASK_SETTING_CS6 = b'vsms'
    VECTOR_ORIGINATION_DATA = b'vogk'
    VECTOR_STROKE_DATA = b'vstk'
    VECTOR_STROKE_CONTENT_DATA = b'vscg'
    VIBRANCE = b'vibA'


class PsdBlendMode(BytesEnum):
    """Blend modes."""

    PASS_THROUGH = b'pass'
    NORMAL = b'norm'
    DISSOLVE = b'diss'
    DARKEN = b'dark'
    MULTIPLY = b'mul '
    COLOR_BURN = b'idiv'
    LINEAR_BURN = b'lbrn'
    DARKER_COLOR = b'dkCl'
    LIGHTEN = b'lite'
    SCREEN = b'scrn'
    COLOR_DODGE = b'div '
    LINEAR_DODGE = b'lddg'
    LIGHTER_COLOR = b'lgCl'
    OVERLAY = b'over'
    SOFT_LIGHT = b'sLit'
    HARD_LIGHT = b'hLit'
    VIVID_LIGHT = b'vLit'
    LINEAR_LIGHT = b'lLit'
    PIN_LIGHT = b'pLit'
    HARD_MIX = b'hMix'
    DIFFERENCE = b'diff'
    EXCLUSION = b'smud'
    SUBTRACT = b'fsub'
    DIVIDE = b'fdiv'
    HUE = b'hue '
    SATURATION = b'sat '
    COLOR = b'colr'
    LUMINOSITY = b'lum '


class PsdColorSpaceType(enum.IntEnum):
    """Color space types."""

    DUMMY = -1
    RGB = 0
    HSB = 1
    CMYK = 2
    Pantone = 3
    Focoltone = 4
    Trumatch = 5
    Toyo = 6
    Lab = 7
    Gray = 8
    WideCMYK = 9
    HKS = 10
    DIC = 11
    TotalInk = 12
    MonitorRGB = 13
    Duotone = 14
    Opacity = 15
    Web = 16
    GrayFloat = 17
    RGBFloat = 18
    OpacityFloat = 19

    @classmethod
    def _missing_(cls, value: object) -> object:
        return -1


class PsdImageModes(enum.IntEnum):
    """Image modes."""

    DUMMY = -1
    Bitmap = 0
    Grayscale = 1
    Indexed = 2
    RGB = 3
    CMYK = 4
    Multichannel = 7
    Duotone = 8
    Lab = 9

    @classmethod
    def _missing_(cls, value: object) -> object:
        return -1


class PsdChannelId(enum.IntEnum):
    """Channel types."""

    CHANNEL0 = 0  # red, cyan, or gray
    CHANNEL1 = 1  # green or magenta
    CHANNEL2 = 2  # blue or yellow
    CHANNEL3 = 3  # black
    CHANNEL4 = 4
    CHANNEL5 = 5
    CHANNEL6 = 6
    CHANNEL7 = 7
    CHANNEL8 = 8
    CHANNEL9 = 9
    TRANSPARENCY_MASK = -1
    USER_LAYER_MASK = -2
    REAL_USER_LAYER_MASK = -3


class PsdClippingType(enum.IntEnum):
    """Clipping types."""

    BASE = 0
    NON_BASE = 1


class PsdCompressionType(enum.IntEnum):
    """Image compression."""

    UNKNOWN = -1
    RAW = 0
    RLE = 1  # PackBits
    ZIP = 2
    ZIP_PREDICTED = 3

    @classmethod
    def _missing_(cls, value: object) -> object:
        return -1


class PsdLayerFlags(enum.IntFlag):
    """Layer record flags."""

    TRANSPARENCY_PROTECTED = 1
    VISIBLE = 2
    OBSOLETE = 4
    PHOTOSHOP5 = 8  # 1 for Photoshop 5.0 and later, tells if bit 4 has info
    IRRELEVANT = 16  # pixel data irrelevant to appearance of document


class PsdLayerMaskFlags(enum.IntFlag):
    """Layer mask flags."""

    RELATIVE = 1  # position relative to layer
    DISABLED = 2  # layer mask disabled
    INVERT = 4  # invert layer mask when blending (obsolete)
    RENDERED = 8  # user mask actually came from rendering other data
    APPLIED = 16  # user and/or vector masks have parameters applied to them


class PsdLayerMaskParameterFlags(enum.IntFlag):
    """Layer mask parameters."""

    USER_DENSITY = 1  # user mask density, 1 byte
    USER_FEATHER = 2  # user mask feather, 8 byte, double
    VECTOR_DENSITY = 4  # vector mask density, 1 byte
    VECTOR_FEATHER = 8  # vector mask feather, 8 bytes, double


class PsdFormatSignatures(bytes, enum.Enum):

    BE32BIT = b'8BIM'
    LE32BIT = b'MIB8'
    BE64BIT = b'8B64'
    LE64BIT = b'46B8'


class PsdRectangle(NamedTuple):
    top: int
    left: int
    bottom: int
    right: int

    def __str__(self) -> str:
        return str(tuple(self))


class PsdFormat:
    """PSD format."""

    __slots__ = ('signature', 'byteorder', 'sizeformat')

    signature: PsdFormatSignatures
    byteorder: Literal['<'] | Literal['>']
    sizeformat: str

    def __init__(
        self, signature: PsdFormat | PsdFormatSignatures | bytes = b'8BIM'
    ) -> None:
        if isinstance(signature, PsdFormat):
            self.signature = signature.signature
        else:
            self.signature = PsdFormatSignatures(signature)
        if self.signature == PsdFormatSignatures.BE32BIT:
            self.byteorder = '>'
            self.sizeformat = '>I'
        elif self.signature == PsdFormatSignatures.LE32BIT:
            self.byteorder = '<'
            self.sizeformat = '<I'
        elif self.signature == PsdFormatSignatures.BE64BIT:
            self.byteorder = '>'
            self.sizeformat = '>Q'
        elif self.signature == PsdFormatSignatures.LE64BIT:
            self.byteorder = '<'
            self.sizeformat = '<Q'

    @property
    def name(self) -> str:
        return self.signature.decode()

    def read(self, fh: BinaryIO, fmt: str | None = None) -> Any:
        fmt = self.sizeformat if fmt is None else self.byteorder + fmt
        value = struct.unpack(fmt, fh.read(struct.calcsize(fmt)))
        return value[0] if len(value) == 1 else value

    def write(self, fh: BinaryIO, fmt: str | None = None, *values: Any) -> int:
        return fh.write(self.pack(fmt, *values))

    def pack(self, fmt: Any, *values: Any) -> bytes:
        fmt = self.sizeformat if fmt is None else self.byteorder + fmt
        return struct.pack(fmt, *values)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.signature == other.signature
        ) or (
            isinstance(other, (bytes, PsdFormatSignatures))
            and self.signature == other
        )

    def __bool__(self) -> bool:
        return bool(self.signature)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.name}>'


@dataclasses.dataclass(repr=False)
class TiffImageSourceData:
    """TIFF ImageSourceData tag #37724."""

    psdformat: PsdFormat
    name: str | None = None
    layers: PsdLayers | None = None
    usermask: PsdUserMask | None = None
    info: list[Any] = dataclasses.field(default_factory=list)

    SIGNATURE = b'Adobe Photoshop Document Data Block\0'

    @classmethod
    def fromfile(
        cls,
        fh: BinaryIO,
        /,
        name: str | None = None,
        skipsign: bool = False,
    ) -> TiffImageSourceData:
        """Return instance from open file handle."""
        name = type(fh).__name__ if name is None else name

        if not skipsign:
            signature = fh.read(len(TiffImageSourceData.SIGNATURE))
            if signature != TiffImageSourceData.SIGNATURE:
                raise ValueError(f'invalid ImageResourceData {signature!r}')

        signature = fh.read(4)
        if len(signature) == 0:
            return cls(psdformat=PsdFormat(), name=name)
        psdformat = PsdFormat(signature)
        fh.seek(-4, 1)

        layers = None
        usermask = None
        info = []

        while fh.read(4) == psdformat.signature:
            resourcekey = PsdResourceKey(fh.read(4))
            size: int = psdformat.read(fh)
            pos = fh.tell()

            if resourcekey in PsdLayers.TYPES and not layers:
                layers = PsdLayers.fromfile(fh, psdformat, resourcekey)
            elif resourcekey == PsdResourceKey.USER_MASK and not usermask:
                usermask = PsdUserMask.fromfile(fh, psdformat)
            elif resourcekey == PsdResourceKey.FILTER_MASK:
                info.append(PsdFilterMask.fromfile(fh, psdformat))
            # TODO:
            # elif resourcekey in PsdPatterns.KEYS and not patterns:
            #     patterns = PsdPatterns.fromfile(fh, psdformat, resourcekey)
            # elif resourcekey == PsdResourceKey.TEXT_ENGINE_DATA:
            #    pass  # b'Txt2'
            # elif resourcekey == sdResourceKey.COMPOSITOR_INFO:
            #    pass  # b'cinf'
            # elif resourcekey == PsdResourceKey.LINKED_LAYER_2:
            #    pass  # b'lnk2'
            # elif resourcekey in (
            #     PsdResourceKey.SAVING_MERGED_TRANSPARENCY,
            #     PsdResourceKey.SAVING_MERGED_TRANSPARENCY2,
            #     PsdResourceKey.SAVING_MERGED_TRANSPARENCY_16,
            #     PsdResourceKey.SAVING_MERGED_TRANSPARENCY_32,
            # ):
            #     pass  # what to do with these?
            elif size > 0:
                log_warning(
                    f"<TiffImageSourceData '{name}'>"
                    f" skipped {size} bytes {resourcekey.value.decode()!r} section"
                )
            size += (4 - size % 4) % 4
            fh.seek(pos + size)

        return cls(
            psdformat=psdformat,
            name=name,
            layers=layers,
            usermask=usermask,
            info=info,
        )

    @classmethod
    def frombytes(
        cls, data: bytes, /, name: str | None = None
    ) -> TiffImageSourceData:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, name=name)
        return self

    @classmethod
    def fromtiff(
        cls, filename: os.PathLike | str, /, pageindex: int = 0
    ) -> TiffImageSourceData:
        """Return instance from TIFF file."""
        data = read_tifftag(filename, 37724, pageindex=pageindex)
        return cls.frombytes(data, name=os.path.split(filename)[-1])

    def write(
        self,
        fh: BinaryIO,
        /,
        psdformat: PsdFormat | PsdFormatSignatures | bytes | None = None,
        compression: PsdCompressionType | int | None = None,
        skipsign: bool = False,
    ) -> int:
        """Write ImageResourceData tag value to open file."""
        psdformat = (
            self.psdformat if psdformat is None else PsdFormat(psdformat)
        )

        start = fh.tell()
        if not skipsign:
            fh.write(TiffImageSourceData.SIGNATURE)

        for section in (self.layers, self.usermask, *self.info):
            if section is None:
                continue
            fh.write(psdformat.signature)
            fh.write(section.resourcekey.tobytes(psdformat.byteorder))
            size_pos = fh.tell()
            psdformat.write(fh, None, 0)
            pos = fh.tell()
            if section is self.layers:
                section.write(
                    fh, psdformat, compression=compression
                )  # type: ignore
            else:
                section.write(fh, psdformat)
            size = fh.tell() - pos
            fh.seek(size_pos)
            psdformat.write(fh, None, size)
            size += (4 - size % 4) % 4
            fh.seek(size, 1)

        return fh.tell() - start

    @property
    def byteorder(self):
        return self.psdformat.byteorder

    def tobytes(
        self,
        /,
        psdformat: PsdFormat | PsdFormatSignatures | bytes | None = None,
        compression: PsdCompressionType | int | None = None,
        skipsign: bool = False,
    ) -> bytes:
        """Return ImageResourceData tag value as bytes."""
        with io.BytesIO() as fh:
            self.write(
                fh, psdformat, compression=compression, skipsign=skipsign
            )
            value = fh.getvalue()
        return value

    def tifftag(
        self,
        /,
        psdformat: PsdFormat | PsdFormatSignatures | bytes | None = None,
        compression: PsdCompressionType | int | None = None,
    ) -> tuple[int, int, int, bytes, bool]:
        """Return tifffile.TiffWriter.write extratags item."""
        value = self.tobytes(psdformat, compression=compression)
        return 37724, 7, len(value), value, True

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.usermask == other.usermask
            and self.layers == other.layers
            and self.info == other.info
            # and self.name == other.name
            # and self.psdformat == other.psdformat
        )

    def __bool__(self) -> bool:
        return self.layers is not None and self.usermask is not None

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.name!r}>'

    def __str__(self) -> str:
        if not self.psdformat:
            return repr(self)
        info = [repr(self), repr(self.psdformat)]
        if self.layers is not None:
            info.append(str(self.layers))
        if self.usermask is not None:
            info.append(str(self.usermask))
        info.extend(self.info)
        return indent(*info)


@dataclasses.dataclass(repr=False)
class PsdLayers:
    """Sequence of PsdLayer."""

    resourcekey: PsdResourceKey
    layers: list[PsdLayer] = dataclasses.field(default_factory=list)
    has_transparency: bool = False

    TYPES = {
        PsdResourceKey.LAYER: 'B',
        PsdResourceKey.LAYER_16: 'H',
        PsdResourceKey.LAYER_32: 'f',
    }

    @classmethod
    def fromfile(
        cls, fh: BinaryIO, psdformat: PsdFormat, resourcekey: PsdResourceKey
    ) -> PsdLayers:
        """Return instance from open file."""
        count = psdformat.read(fh, 'h')
        has_transparency = count < 0
        count = abs(count)

        # layer records
        layers = []
        for _ in range(count):
            layers.append(PsdLayer.fromfile(fh, psdformat))

        # channel image data
        dtype = PsdLayers.TYPES[resourcekey]
        shape: tuple[int, ...] = ()
        for layer in layers:
            for channel in layer.channels:
                if channel.channelid < -1 and layer.mask is not None:
                    shape = layer.mask.shape
                else:
                    shape = layer.shape
                channel.read_image(fh, psdformat, shape, dtype)

        return cls(
            resourcekey=resourcekey,
            layers=layers,
            has_transparency=has_transparency,
        )

    @classmethod
    def frombytes(
        cls, data: bytes, psdformat: PsdFormat, resourcekey: PsdResourceKey
    ) -> PsdLayers:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, psdformat, resourcekey)
        return self

    def write(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | int | None = None,
    ) -> int:
        """Write layer records and channel info data to open file."""
        pos = fh.tell()
        # channel count
        psdformat.write(
            fh, 'h', (-1 if self.has_transparency else 1) * len(self.layers)
        )
        # layer records
        channel_image_data = []
        for layer in self.layers:
            data = layer.write(fh, psdformat, compression=compression)
            channel_image_data.append(data)
        # channel info data
        for data in channel_image_data:
            fh.write(data)
        size = fh.tell() - pos
        if size % 2:
            # length of layers info section must be multiple of 2
            fh.seek(1, 1)
            size += 1
        return size

    def tobytes(self, psdformat: PsdFormat) -> bytes:
        """Return layer records and channel info data."""
        with io.BytesIO() as fh:
            self.write(fh, psdformat)
            value = fh.getvalue()
        return value

    @property
    def dtype(self) -> numpy.dtype:
        return numpy.dtype(PsdLayers.TYPES[self.resourcekey])

    @property
    def shape(self) -> tuple[int, int]:
        shape = [0, 0]
        for layer in self.layers:
            if layer.rect[2] > shape[0]:
                shape[0] = layer.rect[2]
            if layer.rect[3] > shape[1]:
                shape[1] = layer.rect[3]
            if layer.mask is not None and layer.mask.rect is not None:
                if layer.mask.rect[2] > shape[0]:
                    shape[0] = layer.mask.rect[2]
                if layer.mask.rect[3] > shape[1]:
                    shape[1] = layer.mask.rect[3]
        return shape[0], shape[1]

    def __len__(self) -> int:
        return len(self.layers)

    def __getitem__(self, key: int) -> PsdLayer:
        return self.layers[key]

    def __setitem__(self, key: int, value: PsdLayer):
        self.layers[key] = value

    def __iter__(self):
        yield from self.layers

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.resourcekey == other.resourcekey
            and self.has_transparency == other.has_transparency
            and self.layers == other.layers
        )

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} '
            f'{self.resourcekey.value.decode()}[{len(self)}]>'
        )

    def __str__(self) -> str:
        return indent(
            repr(self),
            # f'length: {len(self)}',
            f'shape: {self.shape!r}',
            f'dtype: {numpy.dtype(self.dtype)}',
            f'has_transparency: {self.has_transparency!r}',
            *self.layers,
        )


@dataclasses.dataclass(repr=False)
class PsdLayer:
    """PSD layer record."""

    name: str
    channels: list[PsdChannel]
    rect: PsdRectangle
    mask: PsdLayerMask | None = None
    opacity: int = 255
    blendmode: PsdBlendMode = PsdBlendMode.NORMAL
    blending_ranges: tuple[int, ...] = ()
    clipping: PsdClippingType = PsdClippingType(0)
    flags: PsdLayerFlags = PsdLayerFlags(0)
    info: list[Any] = dataclasses.field(default_factory=list)

    @classmethod
    def fromfile(cls, fh: BinaryIO, psdformat: PsdFormat) -> PsdLayer:
        """Return instance from open file.

        Channel image data must be read separately.

        """
        rect = PsdRectangle(*psdformat.read(fh, 'iiii'))
        count = psdformat.read(fh, 'H')
        channels = []
        for _ in range(count):
            channels.append(PsdChannel.fromfile(fh, psdformat))

        assert fh.read(4) == psdformat.signature
        blendmode = PsdBlendMode(fh.read(4))
        opacity = fh.read(1)[0]
        clipping = PsdClippingType(fh.read(1)[0])
        flags = PsdLayerFlags(fh.read(1)[0])
        assert fh.read(1)[0] == 0  # filler

        extra_size = psdformat.read(fh, 'I')
        end = fh.tell() + extra_size

        # layer mask data
        mask = PsdLayerMask.fromfile(fh, psdformat)

        # layer blending ranges
        nbytes = psdformat.read(fh, 'I')
        assert nbytes % 4 == 0
        blending_ranges = psdformat.read(fh, 'i' * (nbytes // 4))

        # layer name is a Pascal string
        strlen = fh.read(1)[0]
        name = fh.read(strlen).decode('macroman')
        fh.seek((4 - (strlen + 1) % 4) % 4, 1)  # pad to multiple of 4 bytes

        info: list[Any] = []
        # TODO: read additional layer information
        # while fh.tell() < end:
        #     info.append(TaggedBlock.fromfile(fh, psdformat))

        fh.seek(end)

        return cls(
            name=name,
            channels=channels,
            blending_ranges=blending_ranges,
            mask=mask,
            rect=rect,
            opacity=opacity,
            blendmode=blendmode,
            clipping=clipping,
            flags=flags,
            info=info,
        )

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat) -> PsdLayer:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, psdformat)
        return self

    def write(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | int | None = None,
    ) -> bytes:
        """Write layer record to open file and return channel data records."""
        psdformat.write(fh, 'iiii', *self.rect)
        psdformat.write(fh, 'H', len(self.channels))

        channel_image_data = []
        for channel in self.channels:
            data = channel.write(fh, psdformat, compression=compression)
            channel_image_data.append(data)

        psdformat.write(
            fh,
            '4s4sBBBB',
            psdformat.signature.value,
            self.blendmode.tobytes(psdformat.byteorder),
            self.opacity,
            self.clipping.value,
            self.flags,
            0,
        )

        extra_size_pos = fh.tell()
        psdformat.write(fh, 'I', 0)  # placeholder
        pos = fh.tell()

        # layer mask data
        if self.mask is None:
            psdformat.write(fh, 'I', 0)
        else:
            size = self.mask.write(fh, psdformat)
            assert size in (4, 24, 40)

        # layer blending ranges
        psdformat.write(fh, 'I', len(self.blending_ranges) * 4)
        psdformat.write(
            fh, 'i' * len(self.blending_ranges), *self.blending_ranges
        )

        # layer name is a Pascal string
        name = self.name[:255]
        strlen = len(name)
        psdformat.write(fh, f'B{strlen}s', strlen, name.encode('macroman'))
        fh.seek((4 - (strlen + 1) % 4) % 4, 1)  # pad to multiple of 4 bytes

        # TODO: write additional layer information
        # for tag in self.info:
        #     tag.write(fh, psdformat)

        extra_size = fh.tell() - pos
        fh.seek(extra_size_pos)
        psdformat.write(fh, 'I', extra_size)
        fh.seek(extra_size, 1)

        return b''.join(channel_image_data)

    def tobytes(self, psdformat: PsdFormat) -> tuple[bytes, bytes]:
        """Return layer and channel data records."""
        with io.BytesIO() as fh:
            channel_image_data = self.write(fh, psdformat)
            layer_record = fh.getvalue()
        return layer_record, channel_image_data

    def asarray(
        self, channelid: bytes | None = None, planar: bool = False
    ) -> numpy.ndarray:
        """Return channel image data as numpy array."""
        if channelid is not None:
            datalist = [
                channel.data
                for channel in self.channels
                if channel.channelid == channelid and channel.data is not None
            ]
        else:
            datalist = [
                channel.data
                for channel in self.channels
                if channel.channelid >= 0 and channel.data is not None
            ]
            for channel in self.channels:
                if channel.channelid == -1 and channel.data is not None:
                    datalist.append(channel.data)
                    break
        if len(datalist) == 0:
            raise ValueError('no channel matching selection found')
        if len(datalist) == 1:
            data = datalist[0]
        else:
            data = numpy.stack(datalist)
            if not planar:
                data = numpy.moveaxis(data, 0, -1)
        return data

    @property
    def shape(self) -> tuple[int, int]:
        return (
            self.rect.bottom - self.rect.top,
            self.rect.right - self.rect.left,
        )

    @property
    def offset(self) -> tuple[int, int]:
        return self.rect.top, self.rect.left

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.rect == other.rect
            and self.opacity == other.opacity
            and self.blendmode == other.blendmode
            and self.blending_ranges == other.blending_ranges
            and self.clipping == other.clipping
            and self.flags == other.flags
            and self.channels == other.channels
        )

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.name!r}>'

    def __str__(self) -> str:
        return indent(
            repr(self),
            f'rect: {self.rect}',
            f'opacity: {self.opacity}',
            f'blendmode: {self.blendmode.name}',
            f'clipping: {self.clipping.name}',
            f'flags: {str(self.flags)}',
            indent(f'channels[{len(self.channels)}]', *self.channels),
            self.mask,
            *self.info,
        )


@dataclasses.dataclass(repr=False)
class PsdChannel:
    """Channel info and data."""

    channelid: PsdChannelId
    compression: PsdCompressionType = PsdCompressionType.RAW
    data: numpy.ndarray | None = None
    _data_length: int = 0

    @classmethod
    def fromfile(cls, fh: BinaryIO, psdformat: PsdFormat) -> PsdChannel:
        """Return instance from open file.

        Channel image data must be read separately using read_image.

        """
        channelid = PsdChannelId(psdformat.read(fh, 'h'))
        data_length = psdformat.read(fh)
        return cls(channelid=channelid, _data_length=data_length)

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat) -> PsdChannel:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, psdformat)
        return self

    def read_image(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        shape: tuple[int, ...],
        dtype: numpy.dtype | str,
    ) -> None:
        """Read channel image data from open file."""
        if self.data is not None:
            raise RuntimeError

        compression = psdformat.read(fh, 'H')
        self.compression = PsdCompressionType(compression)

        data = fh.read(self._data_length - 2)
        dtype = numpy.dtype(dtype).newbyteorder(psdformat.byteorder)
        uncompressed_size = product(shape) * dtype.itemsize

        if uncompressed_size == 0:
            image = numpy.zeros(shape, dtype=dtype)

        elif compression == PsdCompressionType.RAW:
            image = numpy.frombuffer(data, dtype=dtype).reshape(shape)

        elif compression == PsdCompressionType.ZIP:
            data = zlib.decompress(data)
            image = numpy.frombuffer(data, dtype=dtype).reshape(shape)

        elif compression == PsdCompressionType.ZIP_PREDICTED:
            import imagecodecs

            data = imagecodecs.zlib_decode(data, out=uncompressed_size)
            image = numpy.frombuffer(data, dtype=dtype).reshape(shape)
            if dtype.kind == 'f':
                image = imagecodecs.floatpred_decode(image)
            else:
                image = imagecodecs.delta_decode(image)

        elif compression == PsdCompressionType.RLE:
            import imagecodecs

            offset = shape[0] * (2 if psdformat.sizeformat[-1] == 'I' else 4)
            data = imagecodecs.packbits_decode(data[offset:])
            image = numpy.frombuffer(data, dtype=dtype).reshape(shape)

        else:
            raise ValueError('unknown compression type')

        self.data = image

    def tobytes(
        self,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | int | None = None,
    ) -> tuple[bytes, bytes]:
        """Return channel info and image data records."""
        if self.data is None:
            raise ValueError('data is None')
        if compression is None:
            compression = self.compression
        else:
            compression = PsdCompressionType(compression)
        channel_image_data = psdformat.pack('H', compression)

        dtype = self.data.dtype.newbyteorder(psdformat.byteorder)
        if dtype.char not in PsdLayers.TYPES.values():
            raise ValueError(f'dtype {dtype!r} not supported')
        data = numpy.asarray(self.data, dtype=dtype)

        if data.size == 0:
            pass

        elif compression == PsdCompressionType.RAW:
            channel_image_data += data.tobytes()

        elif compression == PsdCompressionType.ZIP:
            channel_image_data += zlib.compress(data.tobytes())

        elif compression == PsdCompressionType.ZIP_PREDICTED:
            import imagecodecs

            if dtype.char == 'f':
                data = imagecodecs.floatpred_encode(data)
            else:
                data = imagecodecs.delta_encode(data)
            channel_image_data += zlib.compress(data.tobytes())

        elif compression == PsdCompressionType.RLE:
            import imagecodecs

            lines = [imagecodecs.packbits_encode(line) for line in data]
            sizes = [len(line) for line in lines]
            fmt = f'{psdformat.byteorder}{len(sizes)}' + (
                'H' if psdformat.sizeformat[-1] == 'I' else 'I'
            )
            channel_image_data += struct.pack(fmt, *sizes)
            channel_image_data += b''.join(lines)

        else:
            raise ValueError('unknown compression type')

        channel_info = psdformat.pack('h', self.channelid)
        channel_info += psdformat.pack(None, len(channel_image_data))

        return channel_info, channel_image_data

    def write(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | int | None = None,
    ) -> bytes:
        """Write channel info record to file and return image data record."""
        channel_info, channel_image_data = self.tobytes(
            psdformat, compression=compression
        )
        fh.write(channel_info)
        return channel_image_data

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.channelid == other.channelid
            and numpy.array_equal(self.data, other.data)  # type: ignore
            # and self.compression == other.compression
        )

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__}'
            f' {self.channelid.name} {self.compression.name}>'
        )


@dataclasses.dataclass(repr=False)
class PsdLayerMask:
    """Layer mask / adjustment layer data."""

    default_color: int = 0
    rect: PsdRectangle | None = None
    flags: PsdLayerMaskFlags = PsdLayerMaskFlags(0)
    user_mask_density: int | None = None
    user_mask_feather: float | None = None
    vector_mask_density: int | None = None
    vector_mask_feather: float | None = None
    real_flags: PsdLayerMaskFlags | None = None
    real_background: int | None = None
    real_rect: PsdRectangle | None = None

    @classmethod
    def fromfile(cls, fh: BinaryIO, psdformat: PsdFormat) -> PsdLayerMask:
        """Return instance from open file."""
        size = psdformat.read(fh, 'I')
        if size == 0:
            return cls()

        rect = PsdRectangle(*psdformat.read(fh, 'iiii'))
        default_color = fh.read(1)[0]
        flags = PsdLayerMaskFlags(fh.read(1)[0])

        user_mask_density = None
        user_mask_feather = None
        vector_mask_density = None
        vector_mask_feather = None
        if flags & 0b1000:
            param_flags = PsdLayerMaskParameterFlags(fh.read(1)[0])
            if param_flags & PsdLayerMaskParameterFlags.USER_DENSITY:
                user_mask_density = fh.read(1)[0]
            if param_flags & PsdLayerMaskParameterFlags.USER_FEATHER:
                user_mask_feather = psdformat.read(fh, 'd')
            if param_flags & PsdLayerMaskParameterFlags.VECTOR_DENSITY:
                vector_mask_density = fh.read(1)[0]
            if param_flags & PsdLayerMaskParameterFlags.VECTOR_FEATHER:
                vector_mask_feather = psdformat.read(fh, 'd')

        if size == 20:
            fh.seek(2, 1)  # padding
            real_flags = None
            real_background = None
            real_rect = None
        else:
            real_flags = PsdLayerMaskFlags(fh.read(1)[0])
            real_background = fh.read(1)[0]
            real_rect = PsdRectangle(*psdformat.read(fh, 'iiii'))

        return cls(
            rect=rect,
            default_color=default_color,
            flags=flags,
            user_mask_density=user_mask_density,
            user_mask_feather=user_mask_feather,
            vector_mask_density=vector_mask_density,
            vector_mask_feather=vector_mask_feather,
            real_flags=real_flags,
            real_background=real_background,
            real_rect=real_rect,
        )

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat) -> PsdLayerMask:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, psdformat)
        return self

    def tobytes(self, psdformat: PsdFormat) -> bytes:
        """Return layer mask structure."""
        if self.rect is None:
            return psdformat.pack('I', 0)

        flags = self.flags
        param_flags = self.param_flags
        if param_flags:
            flags = flags | 0b1000

        data = psdformat.pack('iiii', *self.rect)
        data += psdformat.pack('B', 255 if self.default_color else 0)
        data += psdformat.pack('B', flags)
        if param_flags:
            data += psdformat.pack('B', param_flags)
            if self.user_mask_density is not None:
                data += psdformat.pack('B', self.user_mask_density)
            if self.user_mask_feather is not None:
                data += psdformat.pack('d', self.user_mask_feather)
            if self.vector_mask_density is not None:
                data += psdformat.pack('B', self.vector_mask_density)
            if self.vector_mask_feather is not None:
                data += psdformat.pack('d', self.vector_mask_feather)
            assert self.real_flags is not None
            assert self.real_background is not None
            assert self.real_rect is not None
            data += psdformat.pack(
                'BB4i', self.real_flags, self.real_background, *self.real_rect
            )
        else:
            data += b'\0\0'
            assert len(data) == 20

        return psdformat.pack('I', len(data)) + data

    def write(self, fh: BinaryIO, psdformat: PsdFormat) -> int:
        """Write layer mask structure to open file."""
        return fh.write(self.tobytes(psdformat))

    @property
    def param_flags(self) -> PsdLayerMaskParameterFlags:
        flags = 0
        if self.user_mask_density is not None:
            flags |= PsdLayerMaskParameterFlags.USER_DENSITY
        if self.user_mask_feather is not None:
            flags |= PsdLayerMaskParameterFlags.USER_FEATHER
        if self.vector_mask_density is not None:
            flags |= PsdLayerMaskParameterFlags.VECTOR_DENSITY
        if self.vector_mask_feather is not None:
            flags |= PsdLayerMaskParameterFlags.VECTOR_FEATHER
        return PsdLayerMaskParameterFlags(flags)

    @property
    def shape(self) -> tuple[int, int]:
        if self.rect is None:
            return (0, 0)
        return (
            self.rect.bottom - self.rect.top,
            self.rect.right - self.rect.left,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.default_color == other.default_color
            and self.flags == other.flags
            and self.user_mask_density == other.user_mask_density
            and self.user_mask_feather == other.user_mask_feather
            and self.vector_mask_density == other.vector_mask_density
            and self.vector_mask_feather == other.vector_mask_feather
            and self.real_flags == other.real_flags
            and self.real_background == other.real_background
            and self.rect == other.rect
            and self.real_rect == other.real_rect
        )

    def __bool__(self) -> bool:
        return self.rect is not None

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.rect}>'

    def __str__(self) -> str:
        if self.rect is None:
            return repr(self)
        info = [
            repr(self),
            # f'rect: {self.rect}',
            f'default_color: {self.default_color!r}',
        ]
        if self.flags:
            info += [f'flags: {self.flags!r}']
        if self.user_mask_density is not None:
            info += [f'user_mask_density: {self.user_mask_density}']
        if self.user_mask_feather is not None:
            info += [f'user_mask_feather: {self.user_mask_feather}']
        if self.vector_mask_density is not None:
            info += [f'vector_mask_density: {self.vector_mask_density}']
        if self.vector_mask_feather is not None:
            info += [f'vector_mask_feather: {self.vector_mask_feather}']
        if self.real_flags is not None and self.real_background is not None:
            info += [
                f'real_background: {self.real_background!r}',
                repr(self.real_rect),
                repr(self.real_flags),
            ]
        return indent(*info)


@dataclasses.dataclass(repr=False)
class PsdUserMask:
    """User mask. Same as global layer mask info table."""

    colorspace: PsdColorSpaceType = PsdColorSpaceType(-1)
    components: tuple[int, int, int, int] = (0, 0, 0, 0)
    opacity: int = 0
    flag: int = 128

    resourcekey = PsdResourceKey.USER_MASK

    @classmethod
    def fromfile(cls, fh: BinaryIO, psdformat: PsdFormat) -> PsdUserMask:
        """Return instance from open file."""
        colorspace = PsdColorSpaceType(psdformat.read(fh, 'h'))
        fmt = '4h' if colorspace == PsdColorSpaceType.Lab else '4H'
        components = psdformat.read(fh, fmt)
        opacity = psdformat.read(fh, 'H')
        flag = fh.read(1)[0]
        return cls(
            colorspace=colorspace,
            components=components,
            opacity=opacity,
            flag=flag,
        )

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat) -> PsdUserMask:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, psdformat)
        return self

    def tobytes(self, psdformat: PsdFormat) -> bytes:
        """Return user mask record."""
        data = psdformat.pack('h', self.colorspace.value)
        fmt = '4h' if self.colorspace == PsdColorSpaceType.Lab else '4H'
        data += psdformat.pack(fmt, *self.components)
        data += psdformat.pack('HB', self.opacity, self.flag)
        data += b'\0'
        return data

    def write(self, fh: BinaryIO, psdformat: PsdFormat) -> int:
        """Write user mask record to open file."""
        return fh.write(self.tobytes(psdformat))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.colorspace == other.colorspace
            and self.opacity == other.opacity
            and self.components == other.components
        )

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.colorspace.name!r}>'

    def __str__(self) -> str:
        return indent(
            repr(self),
            f'components: {self.components}',
            f'opacity: {self.opacity}',
            f'flag: {self.flag}',  # always 128
        )


@dataclasses.dataclass(repr=False)
class PsdFilterMask:
    """Filter Mask (Photoshop CS3)."""

    colorspace: PsdColorSpaceType
    components: tuple[int, int, int, int] = (0, 0, 0, 0)
    opacity: int = 0

    resourcekey = PsdResourceKey.FILTER_MASK

    @classmethod
    def fromfile(cls, fh: BinaryIO, psdformat: PsdFormat) -> PsdFilterMask:
        """Return instance from open file."""
        colorspace = PsdColorSpaceType(psdformat.read(fh, 'h'))
        fmt = '4h' if colorspace == PsdColorSpaceType.Lab else '4H'
        components = psdformat.read(fh, fmt)
        opacity = psdformat.read(fh, 'H')
        return cls(
            colorspace=colorspace,
            components=components,
            opacity=opacity,
        )

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat) -> PsdFilterMask:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, psdformat)
        return self

    def tobytes(self, psdformat: PsdFormat) -> bytes:
        """Return filter mask record."""
        data = psdformat.pack('h', self.colorspace.value)
        fmt = '4h' if self.colorspace == PsdColorSpaceType.Lab else '4H'
        data += psdformat.pack(fmt, *self.components)
        data += psdformat.pack('H', self.opacity)
        return data

    def write(self, fh: BinaryIO, psdformat: PsdFormat) -> int:
        """Write user mask record to open file."""
        return fh.write(self.tobytes(psdformat))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.colorspace == other.colorspace
            and self.components == other.components
            and self.opacity == other.opacity
        )

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.colorspace.name!r}>'

    def __str__(self) -> str:
        return indent(
            repr(self),
            f'components: {self.components}',
            f'opacity: {self.opacity}',
        )


@dataclasses.dataclass(repr=False)
class TiffImageResources:
    """TIFF ImageResources tag #34377."""

    psdformat: PsdFormat
    name: str | None = None

    @classmethod
    def fromfile(
        cls, fh: BinaryIO, name: str | None = None
    ) -> TiffImageResources:
        """Return instance from open file."""
        raise NotImplementedError
        # TODO
        # psdformat = PsdFormat(fh.read(4))
        # fh.seek(-4, 1)
        # return cls(psdformat)

    @classmethod
    def frombytes(
        cls, data: bytes, name: str | None = None
    ) -> TiffImageResources:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.fromfile(fh, name=name)
        return self

    @classmethod
    def fromtiff(
        cls, filename: os.PathLike | str, /, pageindex: int = 0
    ) -> TiffImageResources:
        """Return instance from TIFF file."""
        data = read_tifftag(filename, 34377, pageindex=pageindex)
        return cls.frombytes(data, name=os.path.split(filename)[-1])

    def write(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat | PsdFormatSignatures | bytes | None = None,
    ) -> int:
        """Write ImageResourceData tag to open file."""
        return fh.write(self.tobytes(psdformat))

    def tobytes(
        self,
        psdformat: PsdFormat | PsdFormatSignatures | bytes | None = None,
    ) -> bytes:
        """Return data of ImageResourceData tag as bytes."""
        psdformat = (
            self.psdformat if psdformat is None else PsdFormat(psdformat)
        )
        return b''

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.name!r}>'

    def __str__(self) -> str:
        if not self.psdformat:
            return repr(self)
        return indent(repr(self), repr(self.psdformat))


def log_warning(msg, *args, **kwargs):
    """Log message with level WARNING."""
    import logging

    logging.getLogger(__name__).warning(msg, *args, **kwargs)


def read_tifftag(
    filename: os.PathLike | str, tag: int | str, /, pageindex: int = 0
) -> bytes:
    """Return tag value from TIFF file."""
    from tifffile import TiffFile  # type: ignore

    with TiffFile(filename) as tif:
        data = tif.pages[pageindex].tags.valueof(tag)
        if data is None:
            raise ValueError('TIFF file contains no tag {tag!r}')
    return data


def product(iterable: Iterable[int]) -> int:
    """Return product of sequence of numbers."""
    prod = 1
    for i in iterable:
        prod *= i
    return prod


def indent(*args: Any) -> str:
    """Return joined string representations of objects with indented lines."""
    text = '\n'.join(str(arg) for arg in args)
    return '\n'.join(
        ('  ' + line if line else line) for line in text.splitlines() if line
    )[2:]


def test(verbose: bool = False) -> None:
    """Test TiffImageSourceData and TiffImageResources classes."""
    from glob import glob
    import tifffile
    import imagecodecs

    print(f'Python {sys.version}')
    print(
        f'psdtags-{__version__},',
        f'numpy-{numpy.__version__},',
        f'tifffile-{tifffile.__version__},',
        f'imagecodecs-{imagecodecs.__version__}',
    )

    for filename in glob('tests/*.tif'):
        psd1 = TiffImageSourceData.fromtiff(filename)
        assert str(psd1)
        if verbose:
            print(psd1)
            print()

        # test roundtrips of psdformat and compression
        for psdformat in PsdFormatSignatures:
            for compression in PsdCompressionType:
                if compression == PsdCompressionType.UNKNOWN:
                    continue
                print('.', end='', flush=True)
                buffer = psd1.tobytes(
                    psdformat=psdformat, compression=compression
                )
                psd2 = TiffImageSourceData.frombytes(buffer)
                assert str(psd2)
                if psd2:
                    assert psd2.psdformat == psdformat
                assert psd1 == psd2

        # test tifftag value
        tagid, dtype, size, tagvalue, writeonce = psd1.tifftag()
        assert tagid == 37724
        assert dtype == 7
        assert size == len(tagvalue)
        assert writeonce
        assert psd1 == TiffImageSourceData.frombytes(tagvalue)
        print('.', end=' ', flush=True)

    print()
    # TODO: test TiffImageResources


def main(argv: list[str] | None = None) -> int:
    """Psdtags command line usage main function.

    Print ImageResourceData tag in TIFF file or all TIFF files in directory:

    ``python -m psdtags file_or_directory``

    """
    from glob import glob

    if argv is None:
        argv = sys.argv

    if len(argv) > 1 and '--test' in argv:
        if os.path.exists('../tests'):
            os.chdir('../')
        import doctest

        m: Any
        try:
            import psdtags.psdtags

            m = psdtags.psdtags
        except ImportError:
            m = None
        if os.path.exists('tests'):
            # print('running tests')
            test()
        # print('running doctests')
        doctest.testmod(m)
        print()
        return 0

    if len(argv) == 1:
        files = glob('*.tif')
    elif '*' in argv[1]:
        files = glob(argv[1])
    elif os.path.isdir(argv[1]):
        files = glob(f'{argv[1]}/*.tif')
    else:
        files = argv[1:]

    for fname in files:
        try:
            psd = TiffImageSourceData.fromtiff(fname)
            print(psd)
            print()
            if psd.layers and len(files) == 1:
                from matplotlib import pyplot
                from tifffile import imshow

                for layer in psd.layers:
                    image = layer.asarray()
                    if image.size > 0:
                        imshow(image, title=repr(layer))
                pyplot.show()
        except ValueError as exc:
            # raise  # enable for debugging
            print(fname, exc)
            continue
    return 0


if __name__ == '__main__':
    sys.exit(main())
