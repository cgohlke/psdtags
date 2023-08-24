# psdtags/psdtags.py

# Copyright (c) 2022-2023, Christoph Gohlke
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

"""

from __future__ import annotations

__version__ = '2023.8.24'

__all__ = [
    'PsdBlendMode',
    'PsdBoolean',
    'PsdBytesBlock',
    'PsdChannel',
    'PsdChannelId',
    'PsdClippingType',
    'PsdColorBlock',
    'PsdColorSpaceType',
    'PsdColorType',
    'PsdCompressionType',
    'PsdEmpty',
    'PsdExposure',
    'PsdFilterMask',
    'PsdFormat',
    'PsdImageMode',
    'PsdInteger',
    'PsdKey',
    'PsdKeyABC',
    'PsdLayer',
    'PsdLayerFlag',
    'PsdLayerMask',
    'PsdLayerMaskFlag',
    'PsdLayerMaskParameterFlag',
    'PsdLayers',
    'PsdMetadataSetting',
    'PsdMetadataSettings',
    'PsdPascalString',
    'PsdPascalStringBlock',
    'PsdPascalStringsBlock',
    'PsdPatterns',
    'PsdPoint',
    'PsdRectangle',
    'PsdReferencePoint',
    'PsdResourceBlockABC',
    'PsdResourceId',
    'PsdSectionDividerSetting',
    'PsdSectionDividerType',
    'PsdSheetColorSetting',
    'PsdString',
    'PsdStringBlock',
    'PsdStringsBlock',
    'PsdTextEngineData',
    'PsdThumbnailBlock',
    'PsdUnicodeString',
    'PsdUnknown',
    'PsdUserMask',
    'PsdVersionBlock',
    'PsdVirtualMemoryArray',
    'PsdVirtualMemoryArrayList',
    'PsdWord',
    'TiffImageResources',
    'TiffImageSourceData',
    'read_tifftag',
    'read_psdblocks',
    'read_psdtags',
    'write_psdblocks',
    'write_psdtags',
    'overlay',
    'compress',
    'decompress',
    'REPR_MAXLEN',
]


import sys
import os
import io
import enum
import struct
import zlib
import dataclasses
import abc
from functools import cached_property

import numpy

from typing import TYPE_CHECKING, cast, NamedTuple

if TYPE_CHECKING:
    from typing import Any, BinaryIO, Literal
    from collections.abc import Generator, Iterable

    from numpy.typing import NDArray, DTypeLike


REPR_MAXLEN = 24
"""Maximum length of bytes to show in repr()."""


class BytesEnumMeta(enum.EnumMeta):
    """Metaclass for bytes enums."""

    def __contains__(cls, value: object) -> bool:
        try:
            cls(value)
        except ValueError:
            return False
        return True

    def __call__(cls, *args, **kwds) -> Any:  # type: ignore
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
                if args and len(args[0]) == 4 and args[0].strip().isalnum():
                    log_warning(
                        f'psdtags.{cls.__name__}({args[0]!r}) not defined'
                    )
                    newargs = (b'?unk',) + args[1:]
                    c = enum.EnumMeta.__call__(cls, *newargs, **kwds)
                    c._value_ = args[0]
                else:
                    raise exc
        return c


class BytesEnum(bytes, enum.Enum, metaclass=BytesEnumMeta):
    """Base class for bytes enums."""

    value: bytes

    def tobytes(self, byteorder: str = '>') -> bytes:
        """Return enum value as bytes."""
        return self.value if byteorder == '>' else self.value[::-1]

    def write(self, fh: BinaryIO, byteorder: str = '>', /) -> int:
        """Write enum value to open file."""
        return fh.write(self.value if byteorder == '>' else self.value[::-1])


class PsdKey(BytesEnum):
    """Keys of tagged structures."""

    UNKNOWN = b'?unk'
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
    COMPOSITOR_USED = b'cinf'
    CONTENT_GENERATOR_EXTRA_DATA = b'CgEd'
    CURVES = b'curv'
    EFFECTS_LAYER = b'lrFX'
    EXPOSURE = b'expA'
    FILL_OPACITY = b'iOpa'
    FILTER_EFFECTS = b'FXid'
    FILTER_EFFECTS_2 = b'FEid'
    FILTER_MASK = b'FMsk'
    FOREIGN_EFFECT_ID = b'ffxi'
    FRAMED_GROUP = b'frgb'
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


class PsdResourceId(enum.IntEnum):
    """Image resource IDs."""

    UNKNOWN = -1
    OBSOLETE_1 = 1000
    MAC_PRINT_MANAGER_INFO = 1001
    MAC_PAGE_FORMAT_INFO = 1002
    OBSOLETE_2 = 1003
    RESOLUTION_INFO = 1005
    ALPHA_NAMES_PASCAL = 1006
    DISPLAY_INFO_OBSOLETE = 1007
    CAPTION_PASCAL = 1008
    BORDER_INFO = 1009
    BACKGROUND_COLOR = 1010
    PRINT_FLAGS = 1011
    GRAYSCALE_HALFTONING_INFO = 1012
    COLOR_HALFTONING_INFO = 1013
    DUOTONE_HALFTONING_INFO = 1014
    GRAYSCALE_TRANSFER_FUNCTION = 1015
    COLOR_TRANSFER_FUNCTION = 1016
    DUOTONE_TRANSFER_FUNCTION = 1017
    DUOTONE_IMAGE_INFO = 1018
    EFFECTIVE_BW = 1019
    OBSOLETE_3 = 1020
    EPS_OPTIONS = 1021
    QUICK_MASK_INFO = 1022
    OBSOLETE_4 = 1023
    LAYER_STATE_INFO = 1024
    WORKING_PATH = 1025
    LAYER_GROUP_INFO = 1026
    OBSOLETE_5 = 1027
    IPTC_NAA = 1028
    IMAGE_MODE_RAW = 1029
    JPEG_QUALITY = 1030
    GRID_AND_GUIDES_INFO = 1032
    THUMBNAIL_RESOURCE_PS4 = 1033
    COPYRIGHT_FLAG = 1034
    URL = 1035
    THUMBNAIL_RESOURCE = 1036
    GLOBAL_ANGLE = 1037
    COLOR_SAMPLERS_RESOURCE_OBSOLETE = 1038
    ICC_PROFILE = 1039
    WATERMARK = 1040
    ICC_UNTAGGED_PROFILE = 1041
    EFFECTS_VISIBLE = 1042
    SPOT_HALFTONE = 1043
    IDS_SEED_NUMBER = 1044
    ALPHA_NAMES_UNICODE = 1045
    INDEXED_COLOR_TABLE_COUNT = 1046
    TRANSPARENCY_INDEX = 1047
    GLOBAL_ALTITUDE = 1049
    SLICES = 1050
    WORKFLOW_URL = 1051
    JUMP_TO_XPEP = 1052
    ALPHA_IDENTIFIERS = 1053
    URL_LIST = 1054
    VERSION_INFO = 1057
    EXIF_DATA_1 = 1058
    EXIF_DATA_3 = 1059
    XMP_METADATA = 1060
    CAPTION_DIGEST = 1061
    PRINT_SCALE = 1062
    PIXEL_ASPECT_RATIO = 1064
    LAYER_COMPS = 1065
    ALTERNATE_DUOTONE_COLORS = 1066
    ALTERNATE_SPOT_COLORS = 1067
    LAYER_SELECTION_IDS = 1069
    HDR_TONING_INFO = 1070
    PRINT_INFO_CS2 = 1071
    LAYER_GROUPS_ENABLED_ID = 1072
    COLOR_SAMPLERS_RESOURCE = 1073
    MEASUREMENT_SCALE = 1074
    TIMELINE_INFO = 1075
    SHEET_DISCLOSURE = 1076
    DISPLAY_INFO = 1077
    ONION_SKINS = 1078
    COUNT_INFO = 1080
    PRINT_INFO_CS5 = 1082
    PRINT_STYLE = 1083
    MAC_NSPRINTINFO = 1084
    WINDOWS_DEVMODE = 1085
    AUTO_SAVE_FILE_PATH = 1086
    AUTO_SAVE_FORMAT = 1087
    PATH_SELECTION_STATE = 1088
    PATH_INFO = 2000  # ..2997
    CLIPPING_PATH_NAME = 2999
    ORIGIN_PATH_INFO = 3000
    PLUGIN_RESOURCE = 4000  # ..4999
    IMAGE_READY_VARIABLES = 7000
    IMAGE_READY_DATA_SETS = 7001
    IMAGE_READY_DEFAULT_SELECTED_STATE = 7002
    IMAGE_READY_7_ROLLOVER_EXPANDED_STATE = 7003
    IMAGE_READY_ROLLOVER_EXPANDED_STATE = 7004
    IMAGE_READY_SAVE_LAYER_SETTINGS = 7005
    IMAGE_READY_VERSION = 7006
    LIGHTROOM_WORKFLOW = 8000
    PRINT_FLAGS_INFO = 10000

    @classmethod
    def _missing_(cls, value: object) -> object:
        assert isinstance(value, int)
        if 2000 <= value <= 2997:
            obj = cls(2000)  # PATH_INFO
        elif 4000 <= value <= 4999:
            obj = cls(4000)  # PATH_INFO
        else:
            obj = cls(-1)  # UNKNOWN
        obj._value_ = value
        return obj


class PsdBlendMode(BytesEnum):
    """Blend modes."""

    UNKNOWN = b'?unk'
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

    UNKNOWN = -1
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
        assert isinstance(value, int)
        obj = cls(-1)
        obj._value_ = value
        return obj


class PsdImageMode(enum.IntEnum):
    """Image modes."""

    UNKNOWN = -1
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
        assert isinstance(value, int)
        obj = cls(-1)
        obj._value_ = value
        return obj


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
    """Image compression types."""

    UNKNOWN = -1
    RAW = 0
    RLE = 1  # PackBits
    ZIP = 2
    ZIP_PREDICTED = 3

    @classmethod
    def _missing_(cls, value: object) -> object:
        assert isinstance(value, int)
        obj = cls(-1)
        obj._value_ = value
        return obj


class PsdThumbnailFormat(enum.IntEnum):
    """PsdThumbnailBlock format types."""

    UNKNOWN = -1
    RAW_RGB = 0  # kRawRGB
    JPEG_RGB = 1  # kJpegRGB

    @classmethod
    def _missing_(cls, value: object) -> object:
        assert isinstance(value, int)
        obj = cls(-1)
        obj._value_ = value
        return obj


class PsdLayerFlag(enum.IntFlag):
    """Layer record flags."""

    TRANSPARENCY_PROTECTED = 1
    VISIBLE = 2
    OBSOLETE = 4
    PHOTOSHOP5 = 8  # 1 for Photoshop 5.0 and later, tells if bit 4 has info
    IRRELEVANT = 16  # pixel data irrelevant to appearance of document
    _32 = 32
    _64 = 64


class PsdLayerMaskFlag(enum.IntFlag):
    """Layer mask flags."""

    RELATIVE = 1  # position relative to layer
    DISABLED = 2  # layer mask disabled
    INVERT = 4  # invert layer mask when blending (obsolete)
    RENDERED = 8  # user mask actually came from rendering other data
    APPLIED = 16  # user and/or vector masks have parameters applied to them
    _32 = 32
    _64 = 64


class PsdLayerMaskParameterFlag(enum.IntFlag):
    """Layer mask parameters."""

    USER_DENSITY = 1  # user mask density, 1 byte
    USER_FEATHER = 2  # user mask feather, 8 byte, double
    VECTOR_DENSITY = 4  # vector mask density, 1 byte
    VECTOR_FEATHER = 8  # vector mask feather, 8 bytes, double
    _16 = 16
    _32 = 32
    _64 = 64


class PsdColorType(enum.IntEnum):
    """Color IDs used by sheet color setting structure."""

    UNKNOWN = -1
    NONE = 0
    RED = 1
    ORANGE = 2
    YELLOW = 3
    GREEN = 4
    BLUE = 5
    VIOLET = 6
    GRAY = 7

    @classmethod
    def _missing_(cls, value: object) -> object:
        assert isinstance(value, int)
        obj = cls(-1)
        obj._value_ = value
        return obj


class PsdSectionDividerType(enum.IntEnum):
    """Section divider setting types."""

    UNKNOWN = -1
    OTHER = 0
    OPEN_FOLDER = 1
    CLOSED_FOLDER = 2
    BOUNDING_SECTION_DIVIDER = 3

    @classmethod
    def _missing_(cls, value: object) -> object:
        assert isinstance(value, int)
        obj = cls(-1)
        obj._value_ = value
        return obj


class PsdPoint(NamedTuple):
    """Point."""

    y: int
    x: int

    def __repr__(self) -> str:
        return str(tuple(self))


class PsdRectangle(NamedTuple):
    """Rectangle."""

    top: int
    left: int
    bottom: int
    right: int

    @property
    def shape(self) -> tuple[int, int]:
        """Height and width of rectangle."""
        return (self.bottom - self.top, self.right - self.left)

    @property
    def offset(self) -> tuple[int, int]:
        """Top-left position of rectangle."""
        return self.top, self.left

    def __bool__(self) -> bool:
        return self.bottom - self.top > 0 and self.right - self.left > 0

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}('
            f'{self.top}, {self.left}, {self.bottom}, {self.right})'
        )


@dataclasses.dataclass(repr=False)
class PsdPascalString:
    """Pascal string."""

    value: str

    @classmethod
    def read(cls, fh: BinaryIO, pad: int = 1) -> PsdPascalString:
        """Return instance from open file."""
        size = fh.read(1)[0]
        if size > 255:
            raise ValueError(f'invalid length of pascal string, {size} > 255')
        data = fh.read(size)
        if len(data) != size:
            raise OSError(f'could not read enough data, {len(data)} != {size}')
        value = data.decode('macroman')
        fh.seek((pad - (size + 1) % pad) % pad, 1)
        return cls(value=value)

    def write(self, fh: BinaryIO, pad: int = 1) -> int:
        """Write Pascal string to open file."""
        value = self.value[:255]
        data = value.encode('macroman')
        size = len(data)
        fh.write(struct.pack('B', size))
        fh.write(data)
        pad = fh.write(b'\0' * ((pad - (size + 1) % pad) % pad))
        return 1 + size + pad

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclasses.dataclass(repr=False)
class PsdUnicodeString:
    """Unicode string."""

    value: str

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> PsdUnicodeString:
        """Return instance from open file."""
        size = psdformat.read(fh, 'I') * 2
        assert size >= 0
        data = fh.read(size)
        if len(data) != size:
            raise OSError(f'could not read enough data, {len(data)} != {size}')
        value = data.decode(psdformat.utf16)
        if value and value[-1] == '\0':
            value = value[:-1]
        return cls(value=value)

    def write(
        self, fh: BinaryIO, psdformat: PsdFormat, /, terminate: bool = True
    ) -> int:
        """Write unicode string to open file."""
        value = self.value + '\0' if terminate else self.value
        written = psdformat.write(fh, 'I', len(value))
        written += fh.write(value.encode(psdformat.utf16))
        return written

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


class PsdFormat(bytes, enum.Enum):
    """PSD format."""

    BE32BIT = b'8BIM'
    LE32BIT = b'MIB8'
    BE64BIT = b'8B64'
    LE64BIT = b'46B8'

    @property
    def byteorder(self) -> Literal['>'] | Literal['<']:
        """Byte-order of PSD format."""
        if self.value in {PsdFormat.BE32BIT, PsdFormat.BE64BIT}:
            return '>'
        return '<'

    @property
    def sizeformat(self) -> str:
        """Struct format string for size values."""
        if self.value == PsdFormat.BE32BIT:
            return '>I'
        if self.value == PsdFormat.LE32BIT:
            return '<I'
        if self.value == PsdFormat.BE64BIT:
            return '>Q'
        return '<Q'

    @property
    def utf16(self) -> str:
        """UTF-16 encoding."""
        if self.value in {PsdFormat.BE32BIT, PsdFormat.BE64BIT}:
            return 'UTF-16-BE'
        return 'UTF-16-LE'

    @property
    def isb64(self) -> bool:
        """PSD format is 64-bit."""
        return self.value in {PsdFormat.BE64BIT, PsdFormat.LE64BIT}

    def read(self, fh: BinaryIO, fmt: str) -> Any:
        """Return unpacked values."""
        fmt = self.byteorder + fmt
        value = struct.unpack(fmt, fh.read(struct.calcsize(fmt)))
        return value[0] if len(value) == 1 else value

    def write(self, fh: BinaryIO, fmt: str, *values: Any) -> int:
        """Write values to open file."""
        return fh.write(struct.pack(self.byteorder + fmt, *values))

    def pack(self, fmt: str, *values: Any) -> bytes:
        """Return packed values."""
        return struct.pack(self.byteorder + fmt, *values)

    def read_size(self, fh: BinaryIO, key: PsdKey | None = None) -> int:
        """Return integer whose size depends on signature or key from file."""
        if key is None:
            fmt = self.sizeformat
        elif self.isb64 and key in PSD_KEY_64BIT:
            fmt = self.sizeformat  # TODO: test this
        else:
            fmt = self.byteorder + 'I'
        return int(struct.unpack(fmt, fh.read(struct.calcsize(fmt)))[0])

    def write_size(
        self, fh: BinaryIO, value: int, key: PsdKey | None = None
    ) -> int:
        """Write integer whose size depends on signature or key to file."""
        return fh.write(self.pack_size(value, key))

    def pack_size(self, value: int, key: PsdKey | None = None) -> bytes:
        """Pack integer whose size depends on signature or key."""
        if key is None:
            fmt = self.sizeformat
        elif self.isb64 and key in PSD_KEY_64BIT:
            fmt = self.sizeformat  # TODO: test this
        else:
            fmt = self.byteorder + 'I'
        return struct.pack(fmt, value)

    def write_signature(self, fh: BinaryIO, signature: bytes, /) -> int:
        """Write signature to file."""
        return fh.write(
            signature if self.byteorder == '>' else signature[::-1]
        )

    def write_key(self, fh: BinaryIO, key: PsdKey, /) -> int:
        """Write signature to file."""
        return fh.write(
            key.value if self.byteorder == '>' else key.value[::-1]
        )


class PsdKeyABC(metaclass=abc.ABCMeta):
    """Abstract base class for structures with key."""

    key: PsdKey

    @classmethod
    @abc.abstractmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdKeyABC:
        """Return instance from open file."""

    @classmethod
    def frombytes(
        cls, data: bytes, psdformat: PsdFormat, key: PsdKey, /
    ) -> PsdKeyABC:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.read(fh, psdformat, key, length=len(data))
        return self

    @abc.abstractmethod
    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance values to open file."""

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return instance values as bytes."""
        with io.BytesIO() as fh:
            self.write(fh, psdformat)
            data = fh.getvalue()
        return data

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}{enumstr(self.key)})>'


@dataclasses.dataclass(repr=False)
class PsdLayers(PsdKeyABC):
    """Sequence of PsdLayer."""

    key: PsdKey
    layers: list[PsdLayer] = dataclasses.field(default_factory=list)
    has_transparency: bool = False

    TYPES = {
        PsdKey.LAYER: 'B',
        PsdKey.LAYER_16: 'H',
        PsdKey.LAYER_32: 'f',
    }

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
        unknown: bool = True,
    ) -> PsdLayers:
        """Return instance from open file."""
        count = psdformat.read(fh, 'h')
        has_transparency = count < 0
        count = abs(count)

        # layer records
        layers: list[PsdLayer] = []
        for _ in range(count):
            layers.append(PsdLayer.read(fh, psdformat, unknown=unknown))

        # channel image data
        dtype = PsdLayers.TYPES[key]
        shape: tuple[int, ...] = ()
        for layer in layers:
            for channel in layer.channels:
                if channel.channelid < -1 and layer.mask is not None:
                    shape = layer.mask.shape
                else:
                    shape = layer.shape
                channel.read_image(fh, psdformat, shape, dtype)

        return cls(
            key=key,
            layers=layers,
            has_transparency=has_transparency,
        )

    @classmethod
    def frombytes(
        cls,
        data: bytes,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        unknown: bool = True,
    ) -> PsdLayers:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.read(
                fh, psdformat, key, length=len(data), unknown=unknown
            )
        return self

    def write(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | None = None,
        unknown: bool = True,
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
            data = layer.write(
                fh, psdformat, compression=compression, unknown=unknown
            )
            channel_image_data.append(data)
        # channel info data
        for data in channel_image_data:
            fh.write(data)
        size = fh.tell() - pos
        if size % 2:
            # length of layers info must be multiple of 2
            fh.write(b'\0')
            size += 1
        return size

    def tobytes(
        self,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | None = None,
        unknown: bool = True,
    ) -> bytes:
        """Return layer records and channel info data as bytes."""
        with io.BytesIO() as fh:
            self.write(fh, psdformat, compression=compression, unknown=unknown)
            data = fh.getvalue()
        return data

    @property
    def dtype(self) -> numpy.dtype[Any]:
        """Data type of layer images."""
        return numpy.dtype(PsdLayers.TYPES[self.key])

    @property
    def shape(self) -> tuple[int, int]:
        """Height and width of layer images."""
        shape = [0, 0]
        for layer in self.layers:
            if layer.rectangle[2] > shape[0]:
                shape[0] = layer.rectangle[2]
            if layer.rectangle[3] > shape[1]:
                shape[1] = layer.rectangle[3]
            if layer.mask is not None and layer.mask.rectangle is not None:
                if layer.mask.rectangle[2] > shape[0]:
                    shape[0] = layer.mask.rectangle[2]
                if layer.mask.rectangle[3] > shape[1]:
                    shape[1] = layer.mask.rectangle[3]
        return shape[0], shape[1]

    def __bool__(self) -> bool:
        return len(self.layers) > 0

    def __len__(self) -> int:
        return len(self.layers)

    def __getitem__(self, key: int) -> PsdLayer:
        return self.layers[key]

    def __setitem__(self, key: int, value: PsdLayer) -> None:
        self.layers[key] = value

    def __iter__(self) -> Generator[PsdLayer, None, None]:
        yield from self.layers

    def __repr__(self) -> str:
        sz = len(self.layers)
        return indent(
            f'{self.__class__.__name__}(',
            f'# {self.shape!r} {self.dtype}',
            f'key={enumstr(self.key)},',
            f'has_transparency={self.has_transparency},',
            f'layers=[  # {sz}\n    {indent(*self.layers, sep=",")},\n],',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdLayer:
    """PSD layer record."""

    name: str
    channels: list[PsdChannel]
    rectangle: PsdRectangle
    mask: PsdLayerMask | None = None
    opacity: int = 255
    blendmode: PsdBlendMode = PsdBlendMode.NORMAL
    blending_ranges: tuple[int, ...] = ()
    clipping: PsdClippingType = PsdClippingType(0)
    flags: PsdLayerFlag = PsdLayerFlag(0)
    info: list[Any] = dataclasses.field(default_factory=list)

    @classmethod
    def read(
        cls, fh: BinaryIO, psdformat: PsdFormat, /, unknown: bool = True
    ) -> PsdLayer:
        """Return instance from open file.

        Channel image data must be read separately.

        """
        rectangle = PsdRectangle(*psdformat.read(fh, 'iiii'))
        count = psdformat.read(fh, 'H')
        channels = []
        for _ in range(count):
            channels.append(PsdChannel.read(fh, psdformat))

        signature = fh.read(4)
        assert signature in (b'8BIM', b'MIB8')
        blendmode = PsdBlendMode(fh.read(4))
        opacity = fh.read(1)[0]
        clipping = PsdClippingType(fh.read(1)[0])
        flags = PsdLayerFlag(fh.read(1)[0])
        filler = fh.read(1)[0]
        assert filler == 0

        extra_size = psdformat.read(fh, 'I')
        end = fh.tell() + extra_size

        # layer mask data
        mask = PsdLayerMask.read(fh, psdformat)

        # layer blending ranges
        nbytes = psdformat.read(fh, 'I')
        assert nbytes % 4 == 0
        blending_ranges = psdformat.read(fh, 'i' * (nbytes // 4))

        name = str(PsdPascalString.read(fh, pad=4))

        info = read_psdtags(
            fh, psdformat, length=end - fh.tell(), unknown=unknown, align=2
        )

        fh.seek(end)

        return cls(
            name=name,
            channels=channels,
            blending_ranges=blending_ranges,
            mask=mask,
            rectangle=rectangle,
            opacity=opacity,
            blendmode=blendmode,
            clipping=clipping,
            flags=flags,
            info=info,
        )

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat, /) -> PsdLayer:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.read(fh, psdformat)
        return self

    def write(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | None = None,
        unknown: bool = True,
    ) -> bytes:
        """Write layer record to open file and return channel data records."""
        psdformat.write(fh, 'iiii', *self.rectangle)
        psdformat.write(fh, 'H', len(self.channels))

        channel_image_data = []
        for channel in self.channels:
            data = channel.write(fh, psdformat, compression=compression)
            channel_image_data.append(data)

        psdformat.write_signature(fh, b'8BIM')  # blend mode signature
        psdformat.write(
            fh,
            '4sBBBB',
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

        PsdPascalString(self.name).write(fh, pad=4)

        write_psdtags(fh, psdformat, compression, unknown, 2, *self.info)

        extra_size = fh.tell() - pos
        fh.seek(extra_size_pos)
        psdformat.write(fh, 'I', extra_size)
        fh.seek(extra_size, 1)

        return b''.join(channel_image_data)

    def tobytes(
        self,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | None = None,
        unknown: bool = True,
    ) -> tuple[bytes, bytes]:
        """Return layer and channel data records."""
        with io.BytesIO() as fh:
            channel_image_data = self.write(
                fh, psdformat, compression=compression, unknown=unknown
            )
            layer_record = fh.getvalue()
        return layer_record, channel_image_data

    def asarray(
        self, channelid: PsdChannelId | None = None, planar: bool = False
    ) -> NDArray[Any]:
        """Return channel image data."""
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
        """Height and width of layer image."""
        return self.rectangle.shape if self.rectangle else (0, 0)

    @property
    def offset(self) -> tuple[int, int]:
        """Top-left position of layer image."""
        return self.rectangle.offset

    @property
    def title(self) -> str:
        """Name of layer."""
        return f'{self.__class__.__name__} {self.name!r}'

    @property
    def has_unknowns(self) -> bool:
        """Layer has unknown structures in info."""
        return any(isinstance(tag, PsdUnknown) for tag in self.info)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            # and self.name == other.name
            and self.rectangle == other.rectangle
            and self.opacity == other.opacity
            and self.blendmode == other.blendmode
            and self.blending_ranges == other.blending_ranges
            and self.clipping == other.clipping
            and self.flags == other.flags
            and self.mask == other.mask
            and self.info == other.info
            and self.channels == other.channels
        )

    def __repr__(self) -> str:
        szc = len(self.channels)
        szi = len(self.info)
        return indent(
            f'{self.__class__.__name__}(',
            f'name={self.name!r},',
            f'channels=[  # {szc}\n    {indent(*self.channels, sep=",")},\n],',
            f'rectangle={self.rectangle},',
            f'mask={self.mask},',
            f'opacity={self.opacity},',
            f'blendmode={enumstr(self.blendmode)},',
            f'blending_ranges={self.blending_ranges},',
            f'clipping={enumstr(self.clipping)},',
            f'flags={enumstr(self.flags)},',
            f'info=[  # {szi}\n    {indent(*self.info, sep=",")},\n],',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdChannel:
    """ChannelInfo and ChannelImageData."""

    channelid: PsdChannelId
    compression: PsdCompressionType = PsdCompressionType.RAW
    data: NDArray[Any] | None = None
    _data_length: int = 0

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> PsdChannel:
        """Return instance from open file.

        Channel image data must be read separately using
        :py:meth:`PsdChannel.read_image`.

        """
        channelid = PsdChannelId(psdformat.read(fh, 'h'))
        data_length = psdformat.read_size(fh)
        return cls(channelid=channelid, _data_length=data_length)

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat, /) -> PsdChannel:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.read(fh, psdformat)
        return self

    def read_image(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        shape: tuple[int, ...],
        dtype: DTypeLike,
    ) -> None:
        """Read channel image data from open file."""
        if self.data is not None:
            raise RuntimeError

        self.compression = PsdCompressionType(psdformat.read(fh, 'H'))

        data = fh.read(self._data_length - 2)
        rlecountfmt = psdformat.byteorder + ('I' if psdformat.isb64 else 'H')

        self.data = decompress(
            data, self.compression, shape, dtype, rlecountfmt
        )

    def tobytes(
        self,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | None = None,
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
        rlecountfmt = psdformat.byteorder + ('I' if psdformat.isb64 else 'H')

        channel_image_data += compress(data, compression, rlecountfmt)

        channel_info = psdformat.pack('h', self.channelid)
        channel_info += psdformat.pack_size(len(channel_image_data))

        return channel_info, channel_image_data

    def write(
        self,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        compression: PsdCompressionType | None = None,
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
        if self.data is None:
            data = 'data=None,'
        else:
            data = (
                'data=...,  # numpy.ndarray('
                f"{self.data.shape}, '{self.data.dtype}')"
            )
        return indent(
            f'{self.__class__.__name__}(',
            f'channelid={enumstr(self.channelid)},',
            f'compression={enumstr(self.compression)},',
            data,
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdLayerMask:
    """Layer mask / adjustment layer data."""

    default_color: int = 0
    rectangle: PsdRectangle | None = None
    flags: PsdLayerMaskFlag = PsdLayerMaskFlag(0)
    user_mask_density: int | None = None
    user_mask_feather: float | None = None
    vector_mask_density: int | None = None
    vector_mask_feather: float | None = None
    real_flags: PsdLayerMaskFlag | None = None
    real_background: int | None = None
    real_rectangle: PsdRectangle | None = None

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> PsdLayerMask:
        """Return instance from open file."""
        size = psdformat.read(fh, 'I')
        if size == 0:
            return cls()

        rectangle = PsdRectangle(*psdformat.read(fh, 'iiii'))
        default_color = fh.read(1)[0]
        flags = PsdLayerMaskFlag(fh.read(1)[0])

        user_mask_density = None
        user_mask_feather = None
        vector_mask_density = None
        vector_mask_feather = None
        if flags & 0b1000:
            param_flags = PsdLayerMaskParameterFlag(fh.read(1)[0])
            if param_flags & PsdLayerMaskParameterFlag.USER_DENSITY:
                user_mask_density = fh.read(1)[0]
            if param_flags & PsdLayerMaskParameterFlag.USER_FEATHER:
                user_mask_feather = psdformat.read(fh, 'd')
            if param_flags & PsdLayerMaskParameterFlag.VECTOR_DENSITY:
                vector_mask_density = fh.read(1)[0]
            if param_flags & PsdLayerMaskParameterFlag.VECTOR_FEATHER:
                vector_mask_feather = psdformat.read(fh, 'd')

        if size == 20:
            fh.seek(2, 1)  # padding
            real_flags = None
            real_background = None
            real_rectangle = None
        else:
            real_flags = PsdLayerMaskFlag(fh.read(1)[0])
            real_background = fh.read(1)[0]
            real_rectangle = PsdRectangle(*psdformat.read(fh, 'iiii'))

        return cls(
            rectangle=rectangle,
            default_color=default_color,
            flags=flags,
            user_mask_density=user_mask_density,
            user_mask_feather=user_mask_feather,
            vector_mask_density=vector_mask_density,
            vector_mask_feather=vector_mask_feather,
            real_flags=real_flags,
            real_background=real_background,
            real_rectangle=real_rectangle,
        )

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat, /) -> PsdLayerMask:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.read(fh, psdformat)
        return self

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return layer mask structure."""
        if self.rectangle is None:
            return psdformat.pack('I', 0)

        flags = self.flags
        param_flags = self.param_flags
        if param_flags:
            flags = flags | 0b1000

        data = psdformat.pack('iiii', *self.rectangle)
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
            assert self.real_rectangle is not None
            data += psdformat.pack(
                'BB4i',
                self.real_flags,
                self.real_background,
                *self.real_rectangle,
            )
        else:
            data += b'\0\0'
            assert len(data) == 20

        return psdformat.pack('I', len(data)) + data

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write layer mask structure to open file."""
        return fh.write(self.tobytes(psdformat))

    @property
    def param_flags(self) -> PsdLayerMaskParameterFlag:
        """Layer mask parameter flags."""
        flags = 0
        if self.user_mask_density is not None:
            flags |= PsdLayerMaskParameterFlag.USER_DENSITY
        if self.user_mask_feather is not None:
            flags |= PsdLayerMaskParameterFlag.USER_FEATHER
        if self.vector_mask_density is not None:
            flags |= PsdLayerMaskParameterFlag.VECTOR_DENSITY
        if self.vector_mask_feather is not None:
            flags |= PsdLayerMaskParameterFlag.VECTOR_FEATHER
        return PsdLayerMaskParameterFlag(flags)

    @property
    def shape(self) -> tuple[int, int]:
        """Height and width of layer mask."""
        return self.rectangle.shape if self.rectangle else (0, 0)

    @property
    def offset(self) -> tuple[int, int]:
        """Top-left position of layer mask."""
        return self.rectangle.offset if self.rectangle is not None else (0, 0)

    def __bool__(self) -> bool:
        return self.rectangle is not None

    def __repr__(self) -> str:
        if self.rectangle is None:
            return f'{self.__class__.__name__}()'
        info = [
            f'{self.__class__.__name__}(',
            f'flags={enumstr(self.flags)},',
            f'rectangle={self.rectangle},',
        ]
        if self.default_color:
            info += [f'default_color={self.default_color},']
        if self.user_mask_density is not None:
            info += [f'user_mask_density={self.user_mask_density},']
        if self.user_mask_feather is not None:
            info += [f'user_mask_feather={self.user_mask_feather},']
        if self.vector_mask_density is not None:
            info += [f'vector_mask_density={self.vector_mask_density},']
        if self.vector_mask_feather is not None:
            info += [f'vector_mask_feather={self.vector_mask_feather},']
        if self.real_flags is not None and self.real_background is not None:
            info += [
                f'real_flags={enumstr(self.real_flags)},',
                f'real_background={self.real_background},',
                f'real_rectangle={self.real_rectangle},',
                repr(self.real_flags),
            ]
        return indent(*info, end='\n)')


@dataclasses.dataclass(repr=False)
class PsdUserMask(PsdKeyABC):
    """User mask. Same as global layer mask info table."""

    colorspace: PsdColorSpaceType = PsdColorSpaceType(-1)
    components: tuple[int, int, int, int] = (0, 0, 0, 0)
    opacity: int = 0
    flag: int = 128

    key = PsdKey.USER_MASK

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdUserMask:
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

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return user mask record."""
        data = psdformat.pack('h', self.colorspace.value)
        fmt = '4h' if self.colorspace == PsdColorSpaceType.Lab else '4H'
        data += psdformat.pack(fmt, *self.components)
        data += psdformat.pack('HB', self.opacity, self.flag)
        data += b'\0'
        return data

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write user mask record to open file."""
        return fh.write(self.tobytes(psdformat))

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'colorspace={enumstr(self.colorspace)},',
            f'components={self.components},',
            f'opacity={self.opacity},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdFilterMask(PsdKeyABC):
    """Filter Mask (Photoshop CS3)."""

    colorspace: PsdColorSpaceType
    components: tuple[int, int, int, int] = (0, 0, 0, 0)
    opacity: int = 0

    key = PsdKey.FILTER_MASK

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdFilterMask:
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

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return filter mask record."""
        data = psdformat.pack('h', self.colorspace.value)
        fmt = '4h' if self.colorspace == PsdColorSpaceType.Lab else '4H'
        data += psdformat.pack(fmt, *self.components)
        data += psdformat.pack('H', self.opacity)
        return data

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write filter mask record to open file."""
        return fh.write(self.tobytes(psdformat))

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'colorspace={enumstr(self.colorspace)},',
            f'components={self.components},',
            f'opacity={self.opacity},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdPatterns(PsdKeyABC):
    """Patterns (Photoshop 6.0 and CS 8.0)."""

    key: PsdKey
    imagemode: PsdImageMode
    name: str
    guid: str
    data: PsdVirtualMemoryArrayList
    colortable: NDArray[numpy.uint8] | None = None
    point: PsdPoint = PsdPoint(0, 0)

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdPatterns:
        """Return instance from open file."""
        length, version = psdformat.read(fh, 'II')
        assert version == 1
        imagemode = PsdImageMode(psdformat.read(fh, 'I'))
        point = PsdPoint(*psdformat.read(fh, 'hh'))
        name = str(PsdUnicodeString.read(fh, psdformat))
        guid = str(PsdPascalString.read(fh))

        if imagemode == PsdImageMode.Indexed:
            colortable = numpy.frombuffer(fh.read(768), numpy.uint8, count=768)
            colortable.shape = 256, 3
        else:
            colortable = None

        data = PsdVirtualMemoryArrayList.read(fh, psdformat)

        return cls(
            key=key,
            imagemode=imagemode,
            name=name,
            guid=guid,
            data=data,
            colortable=colortable,
            point=point,
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write patterns to open file."""
        length_pos = fh.tell()
        psdformat.write(fh, 'I', 0)  # length placeholder
        pos = fh.tell()
        psdformat.write(fh, 'I', 1)  # version
        psdformat.write(fh, 'I', self.imagemode.value)
        psdformat.write(fh, 'hh', *self.point)
        PsdUnicodeString(self.name).write(fh, psdformat)
        PsdPascalString(self.guid).write(fh)
        if self.colortable is not None:
            assert self.imagemode == PsdImageMode.Indexed
            fh.write(self.colortable.tobytes())
        self.data.write(fh, psdformat)
        length = fh.tell() - pos
        fh.seek(length_pos)
        psdformat.write(fh, 'I', length)
        fh.seek(length, 1)
        return length + 4

    def asarray(self, planar: bool = False) -> NDArray[Any]:
        """Return channel image data."""
        datalist: list[NDArray[Any]] = [
            channel.data
            for channel in self.data
            if channel and channel.data is not None
        ]
        if len(datalist) == 0:
            raise ValueError('no channel data found')
        if len(datalist) == 1:
            return datalist[0]
        data: NDArray[Any] = numpy.stack(datalist)
        if not planar:
            data = numpy.moveaxis(data, 0, -1)
        return data

    def __repr__(self) -> str:
        if self.colortable is None:
            colortable = None
        else:
            colortable = (
                '...,  # numpy.ndarray('
                f'{self.colortable.shape}, {self.colortable.dtype})'
            )
        return indent(
            f'{self.__class__.__name__}(',
            f'key={enumstr(self.key)},',
            f'imagemode={enumstr(self.imagemode)},',
            f'name={self.name!r},',
            f'guid={self.guid!r},',
            f'colortable={colortable},',
            f'point={self.point},',
            f'data={self.data},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdMetadataSettings(PsdKeyABC):
    """Metadata setting (Photoshop 6.0)."""

    items: list[PsdMetadataSetting] = dataclasses.field(default_factory=list)

    key = PsdKey.METADATA_SETTING

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdMetadataSettings:
        """Return metadata settings from open file."""
        self = cls()
        count = psdformat.read(fh, 'I')
        for _ in range(count):
            self.items.append(PsdMetadataSetting.read(fh, psdformat))
        return self

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write metadata settings to open file."""
        written = psdformat.write(fh, 'I', len(self.items))
        for item in self.items:
            written = item.write(fh, psdformat)
        return written

    def __repr__(self) -> str:
        sz = len(self.items)
        if not self.items:
            return f'{self.__class__.__name__}()'
        return indent(
            f'{self.__class__.__name__}(',
            f'items=[  # {sz}\n    {indent(*self.items, sep=",")},\n],',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdMetadataSetting:
    """Metadata setting item."""

    signature: PsdFormat
    key: bytes  # b'cust', b'cmls', b'extn', b'mlst', b'tmln', b'sgrp'
    data: bytes = b''
    copyonsheet: bool = False

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
    ) -> PsdMetadataSetting:
        """Return metadata setting from open file."""
        signature = PsdFormat(fh.read(4))
        # assert signature in (b'8BIM', b'MIB8')
        key = fh.read(4)
        copyonsheet = psdformat.read(fh, '?xxx')
        length = psdformat.read(fh, 'I')
        # b'mdyn', b'sgrp': int I
        # b'cust', b'cmls', b'extn', b'mlst', b'tmln': DescriptorStructure
        data = fh.read(length)  # TODO: parse DescriptorStructure
        return cls(
            signature=signature, key=key, data=data, copyonsheet=copyonsheet
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write metadata setting to open file."""
        # TODO: can the format change?
        # psdformat.write_signature(fh, self.signature)
        # psdformat.write_key(fh, self.key)
        fh.write(self.signature.value)
        fh.write(self.key)
        psdformat.write(fh, '?xxxI', self.copyonsheet, len(self.data))
        fh.write(self.data)
        return 16 + len(self.data)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            # and self.signature == other.signature
            and self.key == other.key
            and self.copyonsheet == other.copyonsheet
            and self.data == other.data
        )

    def __repr__(self) -> str:
        if len(self.data) > REPR_MAXLEN:
            data = f'data=...,  # bytes({len(self.data)})'
        else:
            data = f'data={self.data!r},'
        return indent(
            f'{self.__class__.__name__}(',
            f'signature={enumstr(self.signature)},',
            f'key={self.key!r},',
            f'copyonsheet={self.copyonsheet},',
            data if self.data else '',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdVirtualMemoryArrayList:
    """Virtual memory array list."""

    rectangle: PsdRectangle
    channels: list[PsdVirtualMemoryArray] = dataclasses.field(
        default_factory=list
    )

    @classmethod
    def read(
        cls, fh: BinaryIO, psdformat: PsdFormat, /
    ) -> PsdVirtualMemoryArrayList:
        """Return instance from open file."""
        version = psdformat.read(fh, 'I')
        assert version == 3
        length = psdformat.read(fh, 'I')  # noqa
        rectangle = PsdRectangle(*psdformat.read(fh, '4I'))
        channelcount = psdformat.read(fh, 'I')

        channels = []
        for _ in range(channelcount + 2):
            channels.append(PsdVirtualMemoryArray.read(fh, psdformat))

        return cls(rectangle=rectangle, channels=channels)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write virtual memory array list to open file."""
        psdformat.write(fh, 'I', 3)
        length_pos = fh.tell()
        psdformat.write(fh, 'I', 0)  # length placeholder
        pos = fh.tell()
        psdformat.write(fh, '4I', *self.rectangle)
        psdformat.write(fh, 'I', len(self.channels) - 2)
        for channel in self.channels:
            channel.write(fh, psdformat)
        length = fh.tell() - pos
        fh.seek(length_pos)
        psdformat.write(fh, 'I', length)
        fh.seek(length, 1)
        return length + 8

    def __len__(self) -> int:
        return len(self.channels)

    def __getitem__(self, key: int) -> PsdVirtualMemoryArray:
        return self.channels[key]

    def __setitem__(self, key: int, value: PsdVirtualMemoryArray) -> None:
        self.channels[key] = value

    def __iter__(self) -> Generator[PsdVirtualMemoryArray, None, None]:
        yield from self.channels

    def __repr__(self) -> str:
        sz = len(self.channels)
        return indent(
            f'{self.__class__.__name__}(',
            f'rectangle={self.rectangle},',
            f'channels=[  # {sz}\n    {indent(*self.channels, sep=",")},\n],',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdVirtualMemoryArray:
    """Virtual memory array."""

    iswritten: bool = False
    depth: int | None = None
    rectangle: PsdRectangle | None = None
    pixeldepth: int | None = None
    compression: PsdCompressionType = PsdCompressionType.RAW
    data: NDArray[Any] | None = None

    @classmethod
    def read(
        cls, fh: BinaryIO, psdformat: PsdFormat, /
    ) -> PsdVirtualMemoryArray:
        """Return instance from open file."""
        iswritten = bool(psdformat.read(fh, 'I'))
        if not iswritten:
            return cls(iswritten=iswritten)

        length = psdformat.read(fh, 'I')
        if length == 0:
            return cls(iswritten=iswritten)

        depth = psdformat.read(fh, 'I')
        rectangle = PsdRectangle(*psdformat.read(fh, '4I'))
        pixeldepth = psdformat.read(fh, 'H')
        compression = PsdCompressionType(psdformat.read(fh, 'B'))
        dtype = {8: 'B', 16: 'H', 32: 'f'}[pixeldepth]

        data = decompress(
            fh.read(length - 23),
            compression,
            rectangle.shape,
            dtype,
            psdformat.byteorder + 'H',
        )

        return cls(
            iswritten=iswritten,
            depth=depth,
            rectangle=rectangle,
            pixeldepth=pixeldepth,
            compression=compression,
            data=data,
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write virtual memory array to open file."""
        start = fh.tell()
        psdformat.write(fh, 'I', self.iswritten)
        if not self.iswritten:
            return fh.tell() - start

        if (
            self.depth is None
            or self.rectangle is None
            or self.pixeldepth is None
            or self.data is None
        ):
            psdformat.write(fh, 'I', 0)
            return fh.tell() - start

        length_pos = fh.tell()
        psdformat.write(fh, 'I', 0)  # length placeholder
        pos = fh.tell()

        psdformat.write(fh, 'I', self.depth)
        psdformat.write(fh, '4I', *self.rectangle)
        psdformat.write(fh, 'H', self.pixeldepth)
        psdformat.write(fh, 'B', self.compression)

        data = compress(
            self.data,
            self.compression,
            psdformat.byteorder + 'H',
        )
        fh.write(data)

        length = fh.tell() - pos
        fh.seek(length_pos)
        psdformat.write(fh, 'I', length)
        fh.seek(length, 1)

        return fh.tell() - start

    @property
    def dtype(self) -> numpy.dtype[Any]:
        """Data type of virtual memory array."""
        if self.pixeldepth is None:
            return numpy.dtype('B')
        return numpy.dtype({8: 'B', 16: 'H', 32: 'f'}[self.pixeldepth])

    @property
    def shape(self) -> tuple[int, int]:
        """Height and width of virtual memory array."""
        return self.rectangle.shape if self.rectangle else (0, 0)

    @property
    def offset(self) -> tuple[int, int]:
        """Top-left position of virtual memory array."""
        return self.rectangle.offset if self.rectangle else (0, 0)

    def __bool__(self) -> bool:
        return self.iswritten and bool(self.rectangle)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.iswritten is other.iswritten
            and self.depth == other.depth
            and self.pixeldepth == other.pixeldepth
            and self.rectangle == other.rectangle
            and numpy.array_equal(self.data, other.data)  # type: ignore
            # and self.compression == other.compression
        )

    def __repr__(self) -> str:
        if not self.iswritten or self.rectangle is None:
            return f'{self.__class__.__name__}()'
        return indent(
            f'{self.__class__.__name__}(',
            f'iswritten={self.iswritten},',
            f'depth={self.depth},',
            f'rectangle={self.rectangle},',
            f'pixeldepth={self.pixeldepth},',
            f'compression={enumstr(self.compression)},',
            f'data=...,  # numpy.ndarray({self.shape}, {self.dtype})',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdSectionDividerSetting(PsdKeyABC):
    """Section divider setting (Photoshop 6.0)."""

    kind: PsdSectionDividerType
    blendmode: PsdBlendMode | None = None
    subtype: int | None = None

    key = PsdKey.SECTION_DIVIDER_SETTING

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdSectionDividerSetting:
        """Return instance from open file."""
        kind = PsdSectionDividerType(psdformat.read(fh, 'I'))
        if length < 12:
            return cls(kind=kind)
        signature = fh.read(4)
        assert signature in (b'8BIM', b'MIB8')
        blendmode = PsdBlendMode(fh.read(4))
        if length < 16:
            return cls(kind=kind, blendmode=blendmode)
        subtype = psdformat.read(fh, 'I')
        return cls(kind=kind, blendmode=blendmode, subtype=subtype)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write section divider settin to open file."""
        psdformat.write(fh, 'I', self.kind.value)
        if self.blendmode is None:
            return 4
        psdformat.write_signature(fh, b'8BIM')
        psdformat.write_signature(fh, self.blendmode.value)
        if self.subtype is None:
            return 12
        psdformat.write(fh, 'I', self.subtype)
        return 16

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'kind={enumstr(self.kind)},',
            f'blendmode={enumstr(self.blendmode)},',
            f'subtype={self.subtype},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdSheetColorSetting(PsdKeyABC):
    """Sheet color setting (Photoshop 6.0)."""

    color: PsdColorType
    key = PsdKey.SHEET_COLOR_SETTING

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdSheetColorSetting:
        """Return instance from open file."""
        color = PsdColorType(psdformat.read(fh, 'H6x'))
        return cls(color=color)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write color setting to open file."""
        psdformat.write(fh, 'H6x', self.color.value)
        return 8

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({enumstr(self.color)})'


@dataclasses.dataclass(repr=False)
class PsdReferencePoint(PsdKeyABC):
    """Reference point."""

    y: float
    x: float
    key = PsdKey.REFERENCE_POINT

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdReferencePoint:
        """Return instance from open file."""
        return cls(*psdformat.read(fh, 'dd'))

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write reference point to open file."""
        return psdformat.write(fh, 'dd', self.y, self.x)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.y}, {self.x})'


@dataclasses.dataclass(repr=False)
class PsdExposure(PsdKeyABC):
    """Exposure."""

    exposure: float
    offset: float
    gamma: float

    key = PsdKey.EXPOSURE

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdExposure:
        """Return exposure from open file."""
        version, exposure, offset, gamma = psdformat.read(fh, 'Hfff')
        assert version == 1
        return cls(exposure=exposure, offset=offset, gamma=gamma)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write exposure to open file."""
        return psdformat.write(
            fh, 'Hfff', 1, self.exposure, self.offset, self.gamma
        )

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'exposure={self.exposure},',
            f'offset={self.offset},',
            f'gamma={self.gamma},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdTextEngineData(PsdKeyABC):
    """Text Engine Data (Photoshop CS3)."""

    data: bytes
    key = PsdKey.TEXT_ENGINE_DATA

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdTextEngineData:
        """Return instance from open file."""
        length = psdformat.read(fh, 'I')
        return cls(data=fh.read(length))

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write unicode string to open file."""
        written = psdformat.write(fh, 'I', len(self.data))
        written += fh.write(self.data)
        return written

    def __repr__(self) -> str:
        if len(self.data) <= REPR_MAXLEN:
            return f'{self.__class__.__name__}({self.data!r})'
        return indent(
            f'{self.__class__.__name__}(',
            f'...,  # bytes({len(self.data)})',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdString(PsdKeyABC):
    """Unicode string."""

    key: PsdKey
    value: str

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdString:
        """Return instance from open file."""
        value = str(PsdUnicodeString.read(fh, psdformat))
        return cls(key=key, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write unicode string to open file."""
        return PsdUnicodeString(self.value).write(
            fh, psdformat, terminate=False
        )

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}({enumstr(self.key)}, {self.value!r})'
        )


@dataclasses.dataclass(repr=False)
class PsdBoolean(PsdKeyABC):
    """Boolean."""

    key: PsdKey
    value: bool

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdBoolean:
        """Return instance from open file."""
        value = bool(fh.read(1))
        fh.read(3)
        return cls(key=key, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write boolean to open file."""
        return fh.write(b'\1\0\0\0' if self.value else b'\0\0\0\0')

    def __bool__(self) -> bool:
        return self.value

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({enumstr(self.key)}, {self.value})'


@dataclasses.dataclass(repr=False)
class PsdInteger(PsdKeyABC):
    """4 Byte Integer."""

    key: PsdKey
    value: int

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdInteger:
        """Return instance from open file."""
        value = psdformat.read(fh, 'i')
        return cls(key=key, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write integer to open file."""
        return psdformat.write(fh, 'i', self.value)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({enumstr(self.key)}, {self.value})'


@dataclasses.dataclass(repr=False)
class PsdWord(PsdKeyABC):
    """Four bytes."""

    key: PsdKey
    value: bytes

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdWord:
        """Return instance from open file."""
        return cls(key=key, value=fh.read(4))

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write four bytes value to open file."""
        return fh.write(self.value)

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}({enumstr(self.key)}, {self.value!r})'
        )


@dataclasses.dataclass(repr=False)
class PsdUnknown(PsdKeyABC):
    """Unknown keys stored as opaque bytes."""

    key: PsdKey
    psdformat: PsdFormat
    value: bytes

    @classmethod
    def frombytes(
        cls, data: bytes, psdformat: PsdFormat, key: PsdKey, /
    ) -> PsdUnknown:
        """Return instance from bytes."""
        return cls(key=key, psdformat=psdformat, value=data)

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdUnknown:
        """Return instance from open file."""
        return cls(key=key, psdformat=psdformat, value=fh.read(length))

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write opaque binary value to open file."""
        if len(self.value) <= 1 or self.psdformat != psdformat:
            raise ValueError(f'can not write opaque bytes as {psdformat}')
        return fh.write(self.value)

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return opaque binary value."""
        if len(self.value) <= 1 or self.psdformat != psdformat:
            raise ValueError(f'can not write opaque bytes as{psdformat}')
        return self.value

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.key == other.key
            and (len(self.value) <= 1 or self.psdformat == other.psdformat)
            and self.value == other.value
        )

    def __repr__(self) -> str:
        if len(self.value) > REPR_MAXLEN:
            value = f'value=...,  # bytes({len(self.value)})'
        else:
            value = f'value={self.value!r},'
        return indent(
            f'{self.__class__.__name__}(',
            f'key={enumstr(self.key)},',
            f'psdformat={enumstr(self.psdformat)},',
            value,
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdEmpty(PsdKeyABC):
    """Empty structure, no data associated with key."""

    key: PsdKey

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> PsdEmpty:
        """Return instance from open file."""
        assert length == 0
        return cls(key=key)

    @classmethod
    def frombytes(
        cls, data: bytes, psdformat: PsdFormat, key: PsdKey, /
    ) -> PsdEmpty:
        """Return instance from bytes."""
        assert len(data) == 0
        return cls(key=key)

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return empty byte string."""
        return b''

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write nothing to open file."""
        return 0

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({enumstr(self.key)})'


class PsdResourceBlockABC(metaclass=abc.ABCMeta):
    """Abstract base class for image resource block data."""

    resourceid: PsdResourceId
    name: str

    @classmethod
    @abc.abstractmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdResourceBlockABC:
        """Return instance from open file."""

    @classmethod
    def frombytes(
        cls,
        data: bytes,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
    ) -> PsdResourceBlockABC:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.read(
                fh, psdformat, resourceid, name=name, length=len(data)
            )
        return self

    @abc.abstractmethod
    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance values to open file."""

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return instance values as bytes."""
        with io.BytesIO() as fh:
            self.write(fh, psdformat)
            data = fh.getvalue()
        return data

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}('
            f'{enumstr(self.resourceid)}, {self.name!r})'
        )


@dataclasses.dataclass(repr=False)
class PsdBytesBlock(PsdResourceBlockABC):
    """Image resource blocks stored as opaque bytes."""

    resourceid: PsdResourceId
    value: bytes
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdBytesBlock:
        """Return instance from open file."""
        value = fh.read(length)
        return cls(resourceid=resourceid, name=name, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance values to open file."""
        return fh.write(self.value)

    def __repr__(self) -> str:
        if len(self.value) > REPR_MAXLEN:
            value = f'value=...,  # bytes({len(self.value)})'
        else:
            value = f'value={self.value!r},'
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            value,
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdVersionBlock(PsdResourceBlockABC):
    """Image resource blocks stored as opaque bytes."""

    resourceid: PsdResourceId
    version: int
    file_version: int
    writer_name: str
    reader_name: str
    has_real_merged_data: bool
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdVersionBlock:
        """Return instance from open file."""
        version = psdformat.read(fh, 'I')
        has_real_merged_data = bool(fh.read(1))
        writer_name = str(PsdUnicodeString.read(fh, psdformat))
        reader_name = str(PsdUnicodeString.read(fh, psdformat))
        file_version = psdformat.read(fh, 'I')
        return cls(
            resourceid=resourceid,
            name=name,
            version=version,
            file_version=file_version,
            writer_name=writer_name,
            reader_name=reader_name,
            has_real_merged_data=has_real_merged_data,
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance values to open file."""
        written = 0
        written += psdformat.write(fh, 'I', self.version)
        written += fh.write(b'\1' if self.has_real_merged_data else b'\0')
        written += PsdUnicodeString(self.writer_name).write(fh, psdformat)
        written += PsdUnicodeString(self.reader_name).write(fh, psdformat)
        written += psdformat.write(fh, 'I', self.file_version)
        return written

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            f'version={self.version},',
            f'file_version={self.file_version},',
            f'writer_name={self.writer_name!r},',
            f'reader_name={self.reader_name!r},',
            f'has_real_merged_data={self.has_real_merged_data},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdStringBlock(PsdResourceBlockABC):
    """Unicode string."""

    resourceid: PsdResourceId
    value: str
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdStringBlock:
        """Return instance from open file."""
        value = str(PsdUnicodeString.read(fh, psdformat))
        return cls(resourceid=resourceid, name=name, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write Pascal string to open file."""
        return PsdUnicodeString(self.value).write(fh, psdformat)

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            f'value={self.value!r},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdStringsBlock(PsdResourceBlockABC):
    """Series of Unicode strings."""

    resourceid: PsdResourceId
    values: list[str]
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdStringsBlock:
        """Return instance from open file."""
        values = []
        pos = fh.tell()
        while fh.tell() - pos < length:
            values.append(str(PsdUnicodeString.read(fh, psdformat)))
        return cls(resourceid=resourceid, name=name, values=values)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write sequence of Unicode strings to open file."""
        written = 0
        for value in self.values:
            written += PsdUnicodeString(value).write(fh, psdformat)
        return written

    def __repr__(self) -> str:
        values = tuple(f"'{v}'" for v in self.values)
        sz = len(values)
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            f'values=[  # {sz}\n    {indent(*values, sep=",")},\n],',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdPascalStringBlock(PsdResourceBlockABC):
    """Pascal string."""

    resourceid: PsdResourceId
    value: str
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdPascalStringBlock:
        """Return instance from open file."""
        value = str(PsdPascalString.read(fh, pad=2))
        return cls(resourceid=resourceid, name=name, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write Pascal string to open file."""
        return PsdPascalString(self.value).write(fh, pad=2)

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            f'value={self.value!r},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdPascalStringsBlock(PsdResourceBlockABC):
    """Series of Pascal strings."""

    resourceid: PsdResourceId
    values: list[str]
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdPascalStringsBlock:
        """Return instance from open file."""
        values = []
        pos = fh.tell()
        while fh.tell() - pos < length:
            values.append(str(PsdPascalString.read(fh, pad=1)))
        return cls(resourceid=resourceid, name=name, values=values)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write sequence of Pascal strings to open file."""
        written = 0
        for value in self.values:
            written += PsdPascalString(value).write(fh, pad=1)
        return written

    def __repr__(self) -> str:
        values = tuple(f"'{v}'" for v in self.values)
        sz = len(values)
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            f'values=[  # {sz}\n    {indent(*values, sep=",")},\n],',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdColorBlock(PsdResourceBlockABC):
    """Color structure."""

    resourceid: PsdResourceId
    colorspace: PsdColorSpaceType
    components: tuple[int, int, int, int] = (0, 0, 0, 0)
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdColorBlock:
        """Return instance from open file."""
        colorspace = PsdColorSpaceType(psdformat.read(fh, 'h'))
        fmt = '4h' if colorspace == PsdColorSpaceType.Lab else '4H'
        components = psdformat.read(fh, fmt)
        return cls(
            resourceid=resourceid,
            name=name,
            colorspace=colorspace,
            components=components,
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance values to open file."""
        fmt = 'h4h' if self.colorspace == PsdColorSpaceType.Lab else 'h4H'
        return psdformat.write(fh, fmt, self.colorspace, *self.components)

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            f'colorspace={enumstr(self.colorspace)},',
            f'components={self.components},',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class PsdThumbnailBlock(PsdResourceBlockABC):
    """Thumbnail resource format."""

    resourceid: PsdResourceId
    format: PsdThumbnailFormat
    width: int
    height: int
    rawdata: bytes
    name: str = ''

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> PsdThumbnailBlock:
        """Return instance from open file."""
        (
            fmt,
            width,
            height,
            widthbytes,
            size,
            size_compressed,
            bitsperpixel,
            planes,
        ) = psdformat.read(fh, 'IIIIIIHH')

        assert bitsperpixel == 24
        assert planes == 1
        assert widthbytes == (width * bitsperpixel + 31) // 32 * 4
        assert size == widthbytes * height * planes
        assert size_compressed == length - 28

        rawdata = fh.read(length - 28)
        return cls(
            resourceid=resourceid,
            name=name,
            format=PsdThumbnailFormat(fmt),
            width=width,
            height=height,
            rawdata=rawdata,
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write Thumbnail resource format to open file."""
        planes = 1
        bitsperpixel = 24
        widthbytes = (self.width * bitsperpixel + 31) // 32 * 4
        size = widthbytes * self.height * planes
        size_compressed = len(self.rawdata)
        psdformat.write(
            fh,
            'IIIIIIHH',
            self.format,
            self.width,
            self.height,
            widthbytes,
            size,
            size_compressed,
            bitsperpixel,
            planes,
        )
        return 28 + fh.write(self.rawdata)

    @property
    def is_bgr(self) -> bool:
        """Thumbnail image is BGR."""
        return self.resourceid.value == 1033

    @property
    def data(self) -> NDArray[Any]:
        """Thumbnail image array."""
        if self.format == PsdThumbnailFormat.RAW_RGB:
            data = numpy.frombuffer(self.rawdata, dtype=numpy.uint8)
            data.shape = (self.height, (self.width * 24 + 31) // 32 * 4)
            data = data[:, : self.width * 3]
            data = data.reshape(self.height, self.width, 3)
        elif self.format == PsdThumbnailFormat.JPEG_RGB:
            from imagecodecs import jpeg8_decode

            data = jpeg8_decode(self.rawdata)
            assert data.shape == (self.height, self.width, 3)
        else:
            raise ValueError(f'unknown PsdThumbnailBlock format {format!r}')
        return data

    @property
    def title(self) -> str:
        """Short representation of instance."""
        return f'{self.__class__.__name__} {self.name!r}'

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'resourceid={enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            f'format={enumstr(self.format)},',
            f'width={self.width},',
            f'height={self.height},',
            f'rawdata=...,  # bytes({len(self.rawdata)})',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class TiffImageSourceData:
    """TIFF ImageSourceData tag #37724."""

    psdformat: PsdFormat
    layers: PsdLayers
    usermask: PsdUserMask
    info: list[PsdKeyABC] = dataclasses.field(default_factory=list)
    name: str | None = None

    SIGNATURE = b'Adobe Photoshop Document Data Block\0'

    @classmethod
    def read(
        cls, fh: BinaryIO, /, name: str | None = None, unknown: bool = True
    ) -> TiffImageSourceData:
        """Return instance from open file."""
        name = type(fh).__name__ if name is None else name

        signature = fh.read(len(TiffImageSourceData.SIGNATURE))
        if signature != TiffImageSourceData.SIGNATURE:
            raise ValueError(f'invalid ImageResourceData {signature!r}')

        signature = fh.read(4)
        if len(signature) == 0:
            return cls(
                psdformat=PsdFormat.BE32BIT,
                layers=PsdLayers(PsdKey.LAYER),
                usermask=PsdUserMask(),
                name=name,
            )
        psdformat = PsdFormat(signature)
        fh.seek(-4, 1)

        layers = None
        usermask = None
        info: list[PsdKeyABC] = []

        while fh.read(4) == psdformat:
            key = PsdKey(fh.read(4))
            size = psdformat.read_size(fh, key)
            pos = fh.tell()

            if size == 0:
                info.append(PsdEmpty(key))
            elif key in PsdLayers.TYPES and layers is None:
                layers = PsdLayers.read(
                    fh, psdformat, key, length=size, unknown=unknown
                )
            elif key == PsdKey.USER_MASK and usermask is None:
                usermask = PsdUserMask.read(fh, psdformat, key, length=size)
            elif key in PSD_KEY_TYPE:
                info.append(
                    PSD_KEY_TYPE[key].read(fh, psdformat, key, length=size)
                )
            elif unknown:
                info.append(PsdUnknown.read(fh, psdformat, key, length=size))
                # log_warning(
                #     f"<TiffImageSourceData '{name}'> skipped {size} bytes "
                #     f"in {key.value.decode()!r} info"
                # )
            size += (4 - size % 4) % 4
            fh.seek(pos + size)

        if layers is None:
            log_warning(f'<{cls.__name__} {name!r}> contains no layers')
            layers = PsdLayers(PsdKey.LAYER)

        if usermask is None:
            log_warning(f'<{cls.__name__} {name!r}> contains no usermask')
            usermask = PsdUserMask()

        return cls(
            psdformat=psdformat,
            name=name,
            layers=layers,
            usermask=usermask,
            info=info,
        )

    @classmethod
    def frombytes(
        cls, data: bytes, /, name: str | None = None, unknown: bool = True
    ) -> TiffImageSourceData:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            self = cls.read(fh, name=name, unknown=unknown)
        return self

    @classmethod
    def fromtiff(
        cls,
        filename: os.PathLike[Any] | str,
        /,
        pageindex: int = 0,
        unknown: bool = True,
    ) -> TiffImageSourceData:
        """Return instance from TIFF file."""
        data = read_tifftag(filename, 37724, pageindex=pageindex)
        if data is None:
            raise ValueError('TIFF file contains no ImageSourceData tag')
        return cls.frombytes(
            data, name=os.path.split(filename)[-1], unknown=unknown
        )

    def write(
        self,
        fh: BinaryIO,
        /,
        psdformat: PsdFormat | bytes | None = None,
        compression: PsdCompressionType | None = None,
        unknown: bool = True,
    ) -> int:
        """Write ImageResourceData tag value to open file."""
        psdformat = (
            self.psdformat if psdformat is None else PsdFormat(psdformat)
        )
        written = fh.write(TiffImageSourceData.SIGNATURE)
        written += write_psdtags(
            fh,
            psdformat,
            compression,
            unknown,
            4,
            self.layers,
            self.usermask,
            *self.info,
        )
        return written

    def tobytes(
        self,
        psdformat: PsdFormat | bytes | None = None,
        compression: PsdCompressionType | None = None,
        unknown: bool = True,
    ) -> bytes:
        """Return ImageResourceData tag value as bytes."""
        with io.BytesIO() as fh:
            self.write(
                fh,
                psdformat,
                compression=compression,
                unknown=unknown,
            )
            value = fh.getvalue()
        return value

    def tifftag(
        self,
        psdformat: PsdFormat | bytes | None = None,
        compression: PsdCompressionType | None = None,
        unknown: bool = True,
    ) -> tuple[int, int, int, bytes, bool]:
        """Return tifffile.TiffWriter.write extratags item."""
        value = self.tobytes(
            psdformat, compression=compression, unknown=unknown
        )
        return 37724, 7, len(value), value, True

    @property
    def byteorder(self) -> Literal['>', '<']:
        """Byte-order of PSD structures."""
        return self.psdformat.byteorder

    def has_unknowns(self) -> bool:
        """ImageSourceData has unknown structures in info or layers."""
        return any(isinstance(tag, PsdUnknown) for tag in self.info) or any(
            layer.has_unknowns for layer in self.layers
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.layers == other.layers
            and self.info == other.info
            # and self.name == other.name
            # and self.psdformat == other.psdformat
        )

    def __bool__(self) -> bool:
        return bool(self.layers) or len(self.info) > 1

    def __repr__(self) -> str:
        sz = len(self.info)
        return indent(
            f'{self.__class__.__name__}(',
            f'name={self.name!r},' if self.name else '',
            f'psdformat={enumstr(self.psdformat)},',
            f'layers={self.layers},',
            f'usermask={self.usermask},',
            f'info=[  # {sz}\n    {indent(*self.info, sep=",")},\n],',
            end='\n)',
        )


@dataclasses.dataclass(repr=False)
class TiffImageResources:
    """TIFF ImageResources tag #34377."""

    psdformat: PsdFormat
    blocks: list[PsdResourceBlockABC]
    name: str | None = None

    @classmethod
    def read(
        cls, fh: BinaryIO, length: int, name: str | None = None
    ) -> TiffImageResources:
        """Return instance from open file."""
        fname = type(fh).__name__ if name is None else name
        blocks = read_psdblocks(fh, length=length)

        return cls(
            psdformat=PsdFormat.BE32BIT,
            name=fname,
            blocks=blocks,
        )

    @classmethod
    def frombytes(
        cls, data: bytes, name: str | None = None
    ) -> TiffImageResources:
        """Return instance from ImageResources tag value."""
        with io.BytesIO(data) as fh:
            self = cls.read(fh, length=len(data), name=name)
        return self

    @classmethod
    def fromtiff(
        cls, filename: os.PathLike[Any] | str, /, pageindex: int = 0
    ) -> TiffImageResources:
        """Return instance from ImageResources tag in TIFF file."""
        data = read_tifftag(filename, 34377, pageindex=pageindex)
        if data is None:
            raise ValueError('TIFF file contains no ImageResources tag')
        return cls.frombytes(data, name=os.path.split(filename)[-1])

    def write(self, fh: BinaryIO) -> int:
        """Write ImageResources tag value to open file."""
        return write_psdblocks(fh, *self.blocks)

    def tobytes(self) -> bytes:
        """Return ImageResources tag value as bytes."""
        with io.BytesIO() as fh:
            self.write(fh)
            value = fh.getvalue()
        return value

    def tifftag(self) -> tuple[int, int, int, bytes, bool]:
        """Return tifffile.TiffWriter.write extratags item."""
        value = self.tobytes()
        return 34377, 7, len(value), value, True

    def thumbnail(self) -> NDArray[Any] | None:
        """Return thumbnail image if any, else None."""
        if 1036 in self.blocks_dict:
            return cast(PsdThumbnailBlock, self.blocks_dict[1036]).data
        if 1033 in self.blocks_dict:
            return cast(PsdThumbnailBlock, self.blocks_dict[1033]).data
        return None

    @cached_property
    def blocks_dict(self) -> dict[int, PsdResourceBlockABC]:
        """Dictionary of PsdResourceBlock by value."""
        # TODO: use a multidict
        blocks_dict: dict[int, PsdResourceBlockABC] = {}
        for block in self.blocks:
            if block.resourceid.value not in blocks_dict:
                blocks_dict[block.resourceid.value] = block
        return blocks_dict

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.tobytes() == other.tobytes()
        )

    def __contains__(self, key: int) -> bool:
        return key in self.blocks_dict

    def __bool__(self) -> bool:
        return len(self.blocks) > 0

    def __len__(self) -> int:
        return len(self.blocks)

    def __getitem__(self, key: int) -> PsdResourceBlockABC:
        return self.blocks_dict[key]

    def __iter__(self) -> Generator[PsdResourceBlockABC, None, None]:
        yield from self.blocks

    def __repr__(self) -> str:
        sz = len(self.blocks)
        return indent(
            f'{self.__class__.__name__}(',
            f'name={self.name!r},' if self.name else '',
            f'psdformat={enumstr(self.psdformat)},',
            f'blocks=[  # {sz}\n    {indent(*self.blocks, sep=",")},\n],',
            end='\n)',
        )


PSD_KEY_64BIT = {
    # if 64 bit format, these keys use a length count of 8 bytes
    PsdKey.ALPHA,
    PsdKey.FILTER_MASK,
    PsdKey.USER_MASK,
    PsdKey.LAYER,
    PsdKey.LAYER_16,
    PsdKey.LAYER_32,
    PsdKey.SAVING_MERGED_TRANSPARENCY,
    PsdKey.SAVING_MERGED_TRANSPARENCY2,
    PsdKey.SAVING_MERGED_TRANSPARENCY_16,
    PsdKey.SAVING_MERGED_TRANSPARENCY_32,
    PsdKey.LINKED_LAYER_2,
    PsdKey.FILTER_EFFECTS,
    PsdKey.FILTER_EFFECTS_2,
    PsdKey.PIXEL_SOURCE_DATA_CC15,
}

PSD_KEY_TYPE: dict[PsdKey, type[PsdKeyABC]] = {
    PsdKey.BLEND_CLIPPING_ELEMENTS: PsdBoolean,
    PsdKey.BLEND_INTERIOR_ELEMENTS: PsdBoolean,
    PsdKey.KNOCKOUT_SETTING: PsdBoolean,
    PsdKey.PATT: PsdEmpty,
    PsdKey.SAVING_MERGED_TRANSPARENCY: PsdEmpty,
    PsdKey.SAVING_MERGED_TRANSPARENCY2: PsdEmpty,
    PsdKey.SAVING_MERGED_TRANSPARENCY_16: PsdEmpty,
    PsdKey.SAVING_MERGED_TRANSPARENCY_32: PsdEmpty,
    PsdKey.EXPOSURE: PsdExposure,
    PsdKey.FILTER_MASK: PsdFilterMask,
    PsdKey.LAYER_ID: PsdInteger,
    PsdKey.LAYER_VERSION: PsdInteger,
    PsdKey.PROTECTED_SETTING: PsdInteger,
    PsdKey.USING_ALIGNED_RENDERING: PsdInteger,
    PsdKey.LAYER: PsdLayers,
    PsdKey.LAYER_16: PsdLayers,
    PsdKey.LAYER_32: PsdLayers,
    PsdKey.LINKED_LAYER_EXTERNAL: PsdLayers,
    PsdKey.METADATA_SETTING: PsdMetadataSettings,
    PsdKey.PATTERNS: PsdPatterns,
    PsdKey.PATTERNS_2: PsdPatterns,
    PsdKey.PATTERNS_3: PsdPatterns,
    PsdKey.REFERENCE_POINT: PsdReferencePoint,
    PsdKey.NESTED_SECTION_DIVIDER_SETTING: PsdSectionDividerSetting,
    PsdKey.SECTION_DIVIDER_SETTING: PsdSectionDividerSetting,
    PsdKey.SHEET_COLOR_SETTING: PsdSheetColorSetting,
    PsdKey.UNICODE_LAYER_NAME: PsdString,
    PsdKey.TEXT_ENGINE_DATA: PsdTextEngineData,
    PsdKey.USER_MASK: PsdUserMask,
    PsdKey.FOREIGN_EFFECT_ID: PsdWord,
    PsdKey.LAYER_MASK_AS_GLOBAL_MASK: PsdWord,
    PsdKey.LAYER_NAME_SOURCE_SETTING: PsdWord,
    PsdKey.TRANSPARENCY_SHAPES_LAYER: PsdWord,
    PsdKey.VECTOR_MASK_AS_GLOBAL_MASK: PsdWord,
    # TODO:
    # PsdKey.ALPHA: PsdUnknown,
    # PsdKey.ANIMATION_EFFECTS: PsdUnknown,
    # PsdKey.ANNOTATIONS: PsdUnknown,
    # PsdKey.ARTBOARD_DATA: PsdUnknown,
    # PsdKey.ARTBOARD_DATA_2: PsdUnknown,
    # PsdKey.ARTBOARD_DATA_3: PsdUnknown,
    # PsdKey.BLACK_AND_WHITE: PsdUnknown,
    # PsdKey.BRIGHTNESS_AND_CONTRAST: PsdUnknown,
    # PsdKey.CHANNEL_BLENDING_RESTRICTIONS_SETTING: PsdUnknown,
    # PsdKey.CHANNEL_MIXER: PsdUnknown,
    # PsdKey.COLOR_BALANCE: PsdUnknown,
    # PsdKey.COLOR_LOOKUP: PsdUnknown,
    # PsdKey.COMPOSITOR_USED: PsdUnknown,
    # PsdKey.CONTENT_GENERATOR_EXTRA_DATA: PsdUnknown,
    # PsdKey.CURVES: PsdUnknown,
    # PsdKey.EFFECTS_LAYER: PsdUnknown,
    # PsdKey.FILL_OPACITY: PsdUnknown,
    # PsdKey.FILTER_EFFECTS: PsdUnknown,
    # PsdKey.FILTER_EFFECTS_2: PsdUnknown,
    # PsdKey.FRAMED_GROUP: PsdUnknown,
    # PsdKey.GRADIENT_FILL_SETTING: PsdUnknown,
    # PsdKey.GRADIENT_MAP: PsdUnknown,
    # PsdKey.HUE_SATURATION: PsdUnknown,
    # PsdKey.HUE_SATURATION_PS4: PsdUnknown,
    # PsdKey.INVERT: PsdUnknown,
    # PsdKey.LEVELS: PsdUnknown,
    # PsdKey.LINKED_LAYER: PsdUnknown,
    # PsdKey.LINKED_LAYER_2: PsdUnknown,
    # PsdKey.LINKED_LAYER_3: PsdUnknown,
    # PsdKey.OBJECT_BASED_EFFECTS_LAYER_INFO: PsdUnknown,
    # PsdKey.PATTERN_DATA: PsdUnknown,
    # PsdKey.PATTERN_FILL_SETTING: PsdUnknown,
    # PsdKey.PHOTO_FILTER: PsdUnknown,
    # PsdKey.PIXEL_SOURCE_DATA: PsdUnknown,
    # PsdKey.PIXEL_SOURCE_DATA_CC15: PsdUnknown,
    # PsdKey.PLACED_LAYER: PsdUnknown,
    # PsdKey.PLACED_LAYER_CS3: PsdUnknown,
    # PsdKey.POSTERIZE: PsdUnknown,
    # PsdKey.SELECTIVE_COLOR: PsdUnknown,
    # PsdKey.SMART_OBJECT_LAYER_DATA: PsdUnknown,
    # PsdKey.SMART_OBJECT_LAYER_DATA_CC15: PsdUnknown,
    # PsdKey.SOLID_COLOR_SHEET_SETTING: PsdUnknown,
    # PsdKey.THRESHOLD: PsdUnknown,
    # PsdKey.TYPE_TOOL_INFO: PsdUnknown,
    # PsdKey.TYPE_TOOL_OBJECT_SETTING: PsdUnknown,
    # PsdKey.UNICODE_PATH_NAME: PsdUnknown,
    # PsdKey.VECTOR_MASK_SETTING: PsdUnknown,
    # PsdKey.VECTOR_MASK_SETTING_CS6: PsdUnknown,
    # PsdKey.VECTOR_ORIGINATION_DATA: PsdUnknown,
    # PsdKey.VECTOR_STROKE_CONTENT_DATA: PsdUnknown,
    # PsdKey.VECTOR_STROKE_DATA: PsdUnknown,
    # PsdKey.VIBRANCE: PsdUnknown,
}


PSD_RESOURCE_TYPE: dict[PsdResourceId, type[PsdResourceBlockABC]] = {
    PsdResourceId.ALPHA_NAMES_PASCAL: PsdPascalStringsBlock,
    PsdResourceId.CAPTION_PASCAL: PsdPascalStringBlock,
    PsdResourceId.ALPHA_NAMES_UNICODE: PsdStringsBlock,
    PsdResourceId.WORKFLOW_URL: PsdStringBlock,
    # PsdResourceId.AUTO_SAVE_FILE_PATH: PsdStringBlock,
    # PsdResourceId.AUTO_SAVE_FORMAT: PsdStringBlock,
    PsdResourceId.THUMBNAIL_RESOURCE_PS4: PsdThumbnailBlock,
    PsdResourceId.THUMBNAIL_RESOURCE: PsdThumbnailBlock,
    PsdResourceId.VERSION_INFO: PsdVersionBlock,
    PsdResourceId.BACKGROUND_COLOR: PsdColorBlock,
}


def read_psdblocks(fh: BinaryIO, /, length: int) -> list[PsdResourceBlockABC]:
    """Return list of image resource block values from open file."""
    align = 2
    psdformat = PsdFormat.BE32BIT
    blocks: list[PsdResourceBlockABC] = []
    end = fh.tell() + length
    while fh.tell() < end and fh.read(4) == psdformat:
        resourceid = PsdResourceId(psdformat.read(fh, 'H'))
        name = str(PsdPascalString.read(fh, 2))
        size = psdformat.read(fh, 'I')
        pos = fh.tell()
        resourcetype = PSD_RESOURCE_TYPE.get(resourceid, PsdBytesBlock)
        blocks.append(
            resourcetype.read(
                fh, psdformat, resourceid, name=name, length=size
            )
        )
        size += (align - size % align) % align
        fh.seek(pos + size)
    return blocks


def write_psdblocks(fh: BinaryIO, /, *blocks: PsdResourceBlockABC) -> int:
    """Write sequence of blocks to open file."""
    align = 2
    psdformat = PsdFormat.BE32BIT
    start = fh.tell()
    for block in blocks:
        fh.write(psdformat.value)
        psdformat.write(fh, 'H', block.resourceid.value)
        PsdPascalString(block.name).write(fh, 2)
        size_pos = fh.tell()
        psdformat.write(fh, 'I', 0)  # update later
        pos = fh.tell()
        block.write(fh, psdformat)
        size = fh.tell() - pos
        fh.seek(size_pos)
        psdformat.write(fh, 'I', size)
        fh.seek(size, 1)
        fh.write(b'\0' * ((align - size % align) % align))
    return fh.tell() - start


def read_psdtags(
    fh: BinaryIO,
    psdformat: PsdFormat,
    /,
    length: int,
    unknown: bool = True,
    align: int = 2,
) -> list[PsdKeyABC]:
    """Return list of tags from open file."""
    tags: list[PsdKeyABC] = []
    end = fh.tell() + length
    while fh.tell() < end and fh.read(4) == psdformat:
        key = PsdKey(fh.read(4))
        size = psdformat.read_size(fh, key)
        pos = fh.tell()
        if size == 0:
            tags.append(PsdEmpty(key))
        elif key in PSD_KEY_TYPE:
            tags.append(
                PSD_KEY_TYPE[key].read(fh, psdformat, key, length=size)
            )
        elif unknown:
            tags.append(PsdUnknown.read(fh, psdformat, key, length=size))
        size += (align - size % align) % align
        fh.seek(pos + size)
    return tags


def write_psdtags(
    fh: BinaryIO,
    psdformat: PsdFormat,
    /,
    compression: PsdCompressionType | None,
    unknown: bool,
    align: int,
    *tags: PsdKeyABC,
) -> int:
    """Write sequence of tags to open file."""
    start = fh.tell()

    for tag in tags:
        if tag is None:
            continue
        if isinstance(tag, PsdUnknown):
            if not unknown:
                continue
            if tag.psdformat != psdformat:
                log_warning(
                    f'<PsdUnknown {tag.key.value.decode()!r}> not written'
                )
                continue
        fh.write(psdformat.value)
        psdformat.write_key(fh, tag.key)
        size_pos = fh.tell()
        psdformat.write_size(fh, 0, tag.key)
        pos = fh.tell()
        if isinstance(tag, PsdLayers):
            tag.write(fh, psdformat, compression=compression, unknown=unknown)
        else:
            tag.write(fh, psdformat)
        size = fh.tell() - pos
        fh.seek(size_pos)
        psdformat.write_size(fh, size, tag.key)
        fh.seek(size, 1)
        fh.write(b'\0' * ((align - size % align) % align))

    return fh.tell() - start


def read_tifftag(
    filename: os.PathLike[Any] | str, tag: int | str, /, pageindex: int = 0
) -> Any:
    """Return tag value from TIFF file."""
    from tifffile import TiffFile

    with TiffFile(filename) as tif:
        data = tif.pages[pageindex].aspage().tags.valueof(tag)
        # if data is None:
        #     raise ValueError(f'TIFF file contains no tag {tag!r}')
    return data


def compress(
    data: NDArray[Any], compression: PsdCompressionType, rlecountfmt: str
) -> bytes:
    """Return compressed big-endian numpy array."""
    data = data.astype(data.dtype.newbyteorder('>'))
    if data.dtype.char not in 'BHf':
        raise ValueError(f'data type {data.dtype!r} not supported')

    if data.size == 0:
        return b''

    if compression == PsdCompressionType.RAW:
        return data.tobytes()

    if compression == PsdCompressionType.ZIP:
        return zlib.compress(data.tobytes())

    if compression == PsdCompressionType.ZIP_PREDICTED:
        import imagecodecs

        if data.dtype.char == 'f':
            data = imagecodecs.floatpred_encode(data)
        else:
            data = imagecodecs.delta_encode(data)
        return zlib.compress(data.tobytes())

    if compression == PsdCompressionType.RLE:
        import imagecodecs

        lines = [imagecodecs.packbits_encode(line) for line in data]
        sizes = [len(line) for line in lines]
        fmt = f'{rlecountfmt[0]}{len(sizes)}{rlecountfmt[1]}'
        return struct.pack(fmt, *sizes) + b''.join(lines)

    raise ValueError(f'unknown compression type {compression!r}')


def decompress(
    data: bytes,
    compression: PsdCompressionType,
    shape: tuple[int, ...],
    dtype: DTypeLike,
    rlecountfmt: str,
) -> NDArray[Any]:
    """Return decompressed numpy array."""
    dtype = numpy.dtype(dtype).newbyteorder('>')
    if dtype.char not in 'BHf':
        raise ValueError(f'data type {dtype!r} not supported')

    uncompressed_size = product(shape) * dtype.itemsize
    if uncompressed_size == 0:
        return numpy.zeros(shape, dtype=dtype)

    if compression == PsdCompressionType.RAW:
        return numpy.frombuffer(data, dtype=dtype).reshape(shape).copy()

    if compression == PsdCompressionType.ZIP:
        data = zlib.decompress(data)
        return numpy.frombuffer(data, dtype=dtype).reshape(shape).copy()

    if compression == PsdCompressionType.ZIP_PREDICTED:
        import imagecodecs

        data = imagecodecs.zlib_decode(data, out=uncompressed_size)
        image = numpy.frombuffer(data, dtype=dtype).reshape(shape)
        if dtype.kind == 'f':
            return imagecodecs.floatpred_decode(image)
        return imagecodecs.delta_decode(image)

    if compression == PsdCompressionType.RLE:
        import imagecodecs

        offset = shape[0] * struct.calcsize(rlecountfmt)
        data = imagecodecs.packbits_decode(data[offset:])
        return numpy.frombuffer(data, dtype=dtype).reshape(shape).copy()

    raise ValueError(f'unknown compression type {compression!r}')


def overlay(
    *layers: tuple[NDArray[Any], tuple[int, int] | None],
    shape: tuple[int, ...] | None = None,
    vmax: float | None = None,
) -> NDArray[Any]:
    """Return overlay of image layers with unassociated alpha channels.

    Parameters:
        layers:
            RGBA image array and offset of layer in canvas.
            Layers must not exceed the canvas boundaries and must all
            have the same data types. Alpha channels are unassociated.
        shape:
            Canvas height and width.
            By default, this is determined from the first layer.
        vmax:
            Value used to normalize layer values.
            By default, this is determined from data type of the first layer.

    Returns:
        Overlay of image layers.

    """
    dtype = layers[0][0].dtype
    if vmax is None:
        if dtype.kind == 'f':
            vmax = 1.0
        else:
            vmax = numpy.iinfo(dtype).max
    if shape is None:
        shape = layers[0][0].shape

    def over(
        b: NDArray[Any], a: NDArray[Any], offset: tuple[int, int] | None
    ) -> None:
        assert shape is not None
        if offset is None:
            offset = (0, 0)
        if (
            offset[0] < 0
            or offset[1] < 0
            or offset[0] + a.shape[0] > shape[0]
            or offset[1] + a.shape[1] > shape[1]
        ):
            raise ValueError('layer is out of canvas bounds')
        b = b[
            slice(offset[0], offset[0] + a.shape[0]),
            slice(offset[1], offset[1] + a.shape[1]),
        ]
        x = b[..., 3:] * (1.0 - a[..., 3:])
        b *= x
        b += a * a[..., 3:]
        b[..., 3] = a[..., 3] + x[..., 0]
        b[..., :3] /= b[..., 3:]

    composite = numpy.zeros((*shape, 4))
    for layer in layers:
        over(composite, layer[0] / vmax, layer[1])
    composite *= vmax
    return composite.astype(dtype)


def log_warning(msg: Any, *args: Any, **kwargs: Any) -> None:
    """Log message with level WARNING."""
    import logging

    logging.getLogger(__name__).warning(msg, *args, **kwargs)


def product(iterable: Iterable[int]) -> int:
    """Return product of sequence of numbers."""
    prod = 1
    for i in iterable:
        prod *= i
    return prod


def indent(*args: Any, sep='', end='') -> str:
    """Return joined string representations of objects with indented lines."""
    text = (sep + '\n').join(
        arg if isinstance(arg, str) else repr(arg) for arg in args
    )
    return (
        '\n'.join(
            ('    ' + line if line else line)
            for line in text.splitlines()
            if line
        )[4:]
        + end
    )


def enumstr(v: enum.Enum | None, /) -> str:
    """Return IntEnum or IntFlag as str."""
    # repr() and str() of enums are type, value, and version dependent
    if v is None:
        return 'None'
    # return f'{v.__class__.__name__}({v.value})'
    s = repr(v)
    s = s[1:].split(':', 1)[0]
    if 'UNKNOWN' in s:
        s = f'{v.__class__.__name__}({v.value})'
    elif '|' in s:
        # IntFlag combination
        s = s.replace('|', ' | ' + v.__class__.__name__ + '.')
    elif not hasattr(v, 'name') or v.name is None:
        s = f'{v.__class__.__name__}({v.value})'
    return s


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
        if read_tifftag(filename, 34377) is not None:
            res1 = TiffImageResources.fromtiff(filename)
            assert str(res1)
            if verbose:
                print(res1)
                print()
            res2 = TiffImageResources.frombytes(res1.tobytes())
            assert res1 == res2

        isd1 = TiffImageSourceData.fromtiff(filename)
        assert str(isd1)
        if verbose:
            print(isd1)
            print()

        has_unknown = any(
            isinstance(tag, PsdUnknown) for tag in isd1.info
        ) or any(
            isinstance(tag, PsdUnknown)
            for layer in isd1.layers
            for tag in layer.info
        )

        # test roundtrips of psdformat and compression
        for psdformat in PsdFormat:
            unknown = has_unknown and psdformat == isd1.psdformat
            if not unknown:
                isd1 = TiffImageSourceData.fromtiff(filename, unknown=False)
            for compression in PsdCompressionType:
                if compression == PsdCompressionType.UNKNOWN:
                    continue
                print('.', end='', flush=True)
                buffer = isd1.tobytes(
                    psdformat=psdformat,
                    compression=compression,
                    unknown=unknown,
                )
                isd2 = TiffImageSourceData.frombytes(buffer)
                str(isd2)
                if isd2:
                    assert isd2.psdformat == psdformat
                assert isd1 == isd2
                # test not equal after changing data
                if isd2.layers:
                    ch0 = isd2.layers[0].channels[0].data
                    if ch0 is not None and ch0.size > 0:
                        ch0[..., 0] = 123
                        assert isd1 != isd2

        # test tifftag value
        tagid, dtype, size, tagvalue, writeonce = isd1.tifftag()
        assert tagid == 37724
        assert dtype == 7
        assert size == len(tagvalue)
        assert writeonce
        assert isd1 == TiffImageSourceData.frombytes(tagvalue)
        print('.', end=' ', flush=True)

    print()
    # TODO: test TiffImageResources


def main(argv: list[str] | None = None) -> int:
    """Psdtags command line usage main function.

    Print ImageResourceData tag in TIFF file or all TIFF files in directory:

    ``python -m psdtags file_or_directory``

    """
    from glob import glob
    from matplotlib import pyplot
    from tifffile import TiffFile, imshow

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
        doctest.testmod(m)
        print()
        if os.path.exists('tests'):
            # print('running tests')
            test()
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
        name = os.path.split(fname)[-1]
        doplot = False
        try:
            with TiffFile(fname) as tif:
                tags = tif.pages[0].aspage().tags
                imagesourcedata = tags.valueof(37724)
                imageresources = tags.valueof(34377)

            if imageresources is not None:
                irs = TiffImageResources.frombytes(imageresources, name=name)
                print(irs)
                print()

                if 1036 in irs:
                    thumbnailblock = cast(PsdThumbnailBlock, irs[1036])
                elif 1033 in irs:
                    thumbnailblock = cast(PsdThumbnailBlock, irs[1033])
                else:
                    thumbnailblock = None
                if thumbnailblock is not None:
                    thumbnail = thumbnailblock.data
                    if thumbnail.size > 0:
                        imshow(thumbnail, title=thumbnailblock.title)
                        doplot = True
                    else:
                        print('Thumbnail image size is zero')
                        print()

            if imagesourcedata is not None:
                isd = TiffImageSourceData.frombytes(imagesourcedata, name=name)
                print(isd)
                print()
                if isd.layers and len(files) == 1:
                    for layer in isd.layers:
                        image = layer.asarray()
                        if image.size > 0:
                            imshow(image, title=layer.title)
                            doplot = True
                        else:
                            print(f'Layer {layer.name!r} image size is zero')

            if doplot:
                pyplot.show()

        except ValueError as exc:
            # raise  # enable for debugging
            print(fname, exc)
            continue
    return 0


if __name__ == '__main__':
    sys.exit(main())
