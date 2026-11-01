# psdtags/descriptor.py

# Copyright (c) 2022-2026, Christoph Gohlke
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

"""Experimental Photoshop descriptor parsing and serialization.

This implementation is experimental and incomplete. It is not used
automatically when reading or writing TIFF tags. Its API and roundtrip
behavior are not guaranteed.

The :py:class:`PsdDescriptor` and :py:class:`PsdDescriptorBlock` classes
parse descriptors in layer tagged blocks and image resource blocks.
They have the same interface as the opaque :py:class:`psdtags.PsdDescriptor`
and :py:class:`psdtags.PsdDescriptorBlock` classes.
Unlike the opaque class, :py:class:`PsdDescriptor` tags are not skipped when
reading with ``unknown=False``.

To enable experimental descriptor parsing in psdtags, set the
``PSDTAGS_DESCRIPTOR_PARSING=1`` environment variable.

"""

from __future__ import annotations

__all__ = [
    'PsdDescriptor',
    'PsdDescriptorAlias',
    'PsdDescriptorBlock',
    'PsdDescriptorBool',
    'PsdDescriptorClass',
    'PsdDescriptorEnum',
    'PsdDescriptorFloat',
    'PsdDescriptorFloatUnit',
    'PsdDescriptorFloatUnits',
    'PsdDescriptorGlobalClass',
    'PsdDescriptorGlobalObject',
    'PsdDescriptorInt',
    'PsdDescriptorList',
    'PsdDescriptorLong',
    'PsdDescriptorObjectArray',
    'PsdDescriptorPath',
    'PsdDescriptorRaw',
    'PsdDescriptorReference',
    'PsdDescriptorString',
    'PsdDescriptorStruct',
    'PsdDescriptorType',
    'PsdDescriptorValueABC',
    'PsdIdString',
    'PsdReferenceClass',
    'PsdReferenceEnumerated',
    'PsdReferenceIdentifier',
    'PsdReferenceIndex',
    'PsdReferenceItemABC',
    'PsdReferenceName',
    'PsdReferenceOffset',
    'PsdReferenceProperty',
    'PsdReferenceType',
    'PsdUnitType',
]


import abc
import io
import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from .psdtags import (
    REPR_MAXLEN,
    BytesEnum,
    PsdFormat,
    PsdKey,
    PsdKeyABC,
    PsdResourceBlockABC,
    PsdResourceId,
    PsdUnicodeString,
    enumstr,
    indent,
    logger,
)

if TYPE_CHECKING:
    from typing import BinaryIO, Self

type PsdIdType = bytes | str


class PsdDescriptorType(BytesEnum):
    """Descriptor value types."""

    REFERENCE = b'obj '
    DESCRIPTOR = b'Objc'
    LIST = b'VlLs'
    DOUBLE = b'doub'
    UNIT_FLOAT = b'UntF'
    STRING = b'TEXT'
    ENUMERATED = b'enum'
    INTEGER = b'long'
    LARGE_INTEGER = b'comp'
    BOOLEAN = b'bool'
    GLOBAL_OBJECT = b'GlbO'
    CLASS = b'type'
    GLOBAL_CLASS = b'GlbC'
    ALIAS = b'alis'
    RAW_DATA = b'tdta'
    UNIT_FLOATS = b'UnFl'
    OBJECT_ARRAY = b'ObAr'
    PATH = b'Pth '


class PsdReferenceType(BytesEnum):
    """Reference item types."""

    PROPERTY = b'prop'
    CLASS = b'Clss'
    ENUMERATED = b'Enmr'
    OFFSET = b'rele'
    IDENTIFIER = b'Idnt'
    INDEX = b'indx'
    NAME = b'name'


class PsdUnitType(BytesEnum):
    """Unit float types."""

    ANGLE = b'#Ang'
    DENSITY = b'#Rsl'
    DISTANCE = b'#Rlt'
    NONE = b'#Nne'
    PERCENT = b'#Prc'
    PIXELS = b'#Pxl'
    POINTS = b'#Pnt'
    MILLIMETERS = b'#Mlm'


@dataclass(repr=False)
class PsdIdString:
    """ID string of either 4 bytes or ASCII string."""

    value: str | bytes  # bytes are stored in big-endian order

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value: str | bytes
        length = psdformat.read(fh, 'I')
        if length == 0:
            value = fh.read(4)
            if psdformat.byteorder == '<':
                value = value[::-1]
        else:
            value = fh.read(length).decode('latin-1', errors='replace')
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write ID string to open file."""
        s = self.value
        if isinstance(s, bytes):
            if len(s) == 4:
                if psdformat.byteorder == '<':
                    s = s[::-1]
                return psdformat.write(fh, 'I', 0) + fh.write(s)
            msg = 'ID bytes must be length 4'
            raise ValueError(msg)
        if len(s) == 0:
            msg = "empty ID string cannot be written, use b'\\0\\0\\0\\0'"
            raise ValueError(msg)
        data = s.encode('latin-1', errors='replace')
        return psdformat.write(fh, 'I', len(data)) + fh.write(data)

    def __hash__(self) -> int:
        return hash(self.value)

    def __str__(self) -> str:
        if isinstance(self.value, bytes):
            return f'{self.value!r}'
        return self.value

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


class PsdDescriptorValueABC(metaclass=abc.ABCMeta):
    """Descriptor value abstract base class."""

    type: PsdDescriptorType

    @classmethod
    @abc.abstractmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""

    @abc.abstractmethod
    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""

    @classmethod
    def frombytes(cls, data: bytes, psdformat: PsdFormat, /) -> Self:
        """Return instance from bytes."""
        with io.BytesIO(data) as fh:
            return cls.read(fh, psdformat)

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return instance values as bytes."""
        with io.BytesIO() as fh:
            self.write(fh, psdformat)
            return fh.getvalue()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PsdDescriptorValueABC)
            and type(self) is type(other)
            and self.tobytes(PsdFormat.BE32BIT)
            == other.tobytes(PsdFormat.BE32BIT)
        )

    def __hash__(self) -> int:
        return hash((type(self), self.tobytes(PsdFormat.BE32BIT)))

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({enumstr(self.type)})>'


@dataclass(eq=False)
class PsdDescriptorFloat(PsdDescriptorValueABC):
    """Descriptor double (64-bit float) value."""

    value: float

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.DOUBLE, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value = psdformat.read(fh, 'd')
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        return psdformat.write(fh, 'd', self.value)

    def __str__(self) -> str:
        return f'{self.value!r}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False)
class PsdDescriptorString(PsdDescriptorValueABC):
    """Descriptor Unicode string value."""

    value: str

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.STRING, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value = PsdUnicodeString.read(fh, psdformat).value
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        return PsdUnicodeString(value=self.value).write(fh, psdformat)

    def __str__(self) -> str:
        return f'{self.value!r}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False)
class PsdDescriptorInt(PsdDescriptorValueABC):
    """Descriptor 32-bit signed integer value."""

    value: int

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.INTEGER, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value = psdformat.read(fh, 'i')
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        return psdformat.write(fh, 'i', self.value)

    def __str__(self) -> str:
        return f'{self.value!r}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False)
class PsdDescriptorLong(PsdDescriptorValueABC):
    """Descriptor 64-bit signed integer value."""

    value: int

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.LARGE_INTEGER, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value = psdformat.read(fh, 'q')
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        return psdformat.write(fh, 'q', self.value)

    def __str__(self) -> str:
        return f'{self.value!r}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False)
class PsdDescriptorBool(PsdDescriptorValueABC):
    """Descriptor boolean value."""

    value: bool

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.BOOLEAN, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value = psdformat.read(fh, 'B') != 0
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        return psdformat.write(fh, 'B', 1 if self.value else 0)

    def __str__(self) -> str:
        return f'{self.value!r}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False)
class PsdDescriptorRaw(PsdDescriptorValueABC):
    """Descriptor raw data value."""

    value: bytes

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.RAW_DATA, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        length = psdformat.read(fh, 'I')
        value = fh.read(length)
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = psdformat.write(fh, 'I', len(self.value))
        written += fh.write(self.value)
        return written

    def __repr__(self) -> str:
        if len(self.value) > REPR_MAXLEN:
            return indent(
                f'{self.__class__.__name__}(',
                f'...,  # bytes({len(self.value)})',
                end='\n)',
            )
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False, repr=False)
class PsdDescriptorAlias(PsdDescriptorRaw):
    """Descriptor alias (file reference) value."""

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.ALIAS, init=False, repr=False
    )


@dataclass(eq=False, repr=False)
class PsdDescriptorPath(PsdDescriptorRaw):
    """Descriptor path value (undocumented)."""

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.PATH, init=False, repr=False
    )


@dataclass(eq=False)
class PsdDescriptorFloatUnit(PsdDescriptorValueABC):
    """Descriptor unit float value."""

    value: float
    unit: PsdUnitType

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.UNIT_FLOAT, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        unit = PsdUnitType(psdformat.read_signature(fh))
        value = psdformat.read(fh, 'd')
        return cls(value=value, unit=unit)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = self.unit.write(fh, psdformat.byteorder)
        written += psdformat.write(fh, 'd', self.value)
        return written

    def __str__(self) -> str:
        return f'({self.value!r}, {enumstr(self.unit)})'

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}({self.value!r}, {enumstr(self.unit)})'
        )


@dataclass(eq=False)
class PsdDescriptorFloatUnits(PsdDescriptorValueABC):
    """Descriptor array of unit float values."""

    values: list[float]
    unit: PsdUnitType

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.UNIT_FLOATS, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        unit = PsdUnitType(psdformat.read_signature(fh))
        count = psdformat.read(fh, 'I')
        fmt = f'{psdformat.byteorder}{count}d'
        values = list(struct.unpack(fmt, fh.read(struct.calcsize(fmt))))
        return cls(values=values, unit=unit)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = self.unit.write(fh, psdformat.byteorder)
        written += psdformat.write(fh, 'I', len(self.values))
        written += psdformat.write(fh, f'{len(self.values)}d', *self.values)
        return written

    def __str__(self) -> str:
        return f'({self.values!r}, {enumstr(self.unit)})'

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}({self.values!r}, {enumstr(self.unit)})'
        )


@dataclass(eq=False)
class PsdDescriptorEnum(PsdDescriptorValueABC):
    """Descriptor enumerated value."""

    value: PsdIdType
    typeid: PsdIdType

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.ENUMERATED, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        typeid = PsdIdString.read(fh, psdformat).value
        value = PsdIdString.read(fh, psdformat).value
        return cls(value=value, typeid=typeid)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = PsdIdString(value=self.typeid).write(fh, psdformat)
        written += PsdIdString(value=self.value).write(fh, psdformat)
        return written

    def __str__(self) -> str:
        return f'({self.value!r}, {self.typeid!r})'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r}, {self.typeid!r})'


@dataclass(eq=False)
class PsdDescriptorClass(PsdDescriptorValueABC):
    """Descriptor class value."""

    name: str
    classid: PsdIdType

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.CLASS, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        name = PsdUnicodeString.read(fh, psdformat).value
        classid = PsdIdString.read(fh, psdformat).value
        return cls(name=name, classid=classid)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = PsdUnicodeString(value=self.name).write(fh, psdformat)
        written += PsdIdString(value=self.classid).write(fh, psdformat)
        return written


@dataclass(eq=False)
class PsdDescriptorGlobalClass(PsdDescriptorClass):
    """Descriptor global class value."""

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.GLOBAL_CLASS, init=False, repr=False
    )


@dataclass(eq=False)
class PsdDescriptorList(PsdDescriptorValueABC):
    """Descriptor list value."""

    items: list[PsdDescriptorValueABC]

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.LIST, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        count = psdformat.read(fh, 'I')
        items: list[PsdDescriptorValueABC] = []

        for _ in range(count):
            type_code = PsdDescriptorType(psdformat.read_signature(fh))
            value_cls = PSD_DESCRIPTOR_TYPE.get(type_code)
            if value_cls is None:
                msg = f'unknown descriptor type: {type_code!r}'
                raise ValueError(msg)
            items.append(value_cls.read(fh, psdformat))

        return cls(items=items)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = psdformat.write(fh, 'I', len(self.items))
        for item in self.items:
            written += item.type.write(fh, psdformat.byteorder)
            written += item.write(fh, psdformat)
        return written

    def __repr__(self) -> str:
        if not self.items:
            return f'{self.__class__.__name__}(items=[])'
        sz = len(self.items)
        items_repr = ',\n'.join(f'{item!r}' for item in self.items)
        return indent(
            f'{self.__class__.__name__}(',
            f'items=[  # {sz}\n    {indent(items_repr)},\n],',
            end='\n)',
        )


@dataclass(repr=False, eq=False)
class PsdDescriptorStruct(PsdDescriptorValueABC):
    """Descriptor structure.

    Descriptors are used to serialize general Photoshop data objects.

    """

    classid: PsdIdType
    items: dict[PsdIdType, PsdDescriptorValueABC]
    name: str = ''

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.DESCRIPTOR, init=False, repr=False
    )

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        *,
        version: int = 0,
    ) -> Self:
        """Return instance from open file."""
        if version:
            ver = psdformat.read(fh, 'I')
            if ver != version:
                msg = (
                    'unsupported descriptor version: '
                    f'{ver}, expected {version}'
                )
                raise ValueError(msg)
        name, classid, items = cls._read_body(fh, psdformat)
        return cls(classid=classid, name=name, items=items)

    @staticmethod
    def _read_body(
        fh: BinaryIO, psdformat: PsdFormat, /
    ) -> tuple[str, PsdIdType, dict[PsdIdType, PsdDescriptorValueABC]]:
        """Return name, class ID, and items from open file."""
        name = PsdUnicodeString.read(fh, psdformat).value
        classid = PsdIdString.read(fh, psdformat).value
        count = psdformat.read(fh, 'I')

        items: dict[PsdIdType, PsdDescriptorValueABC] = {}
        for _ in range(count):
            key = PsdIdString.read(fh, psdformat).value
            type_code = PsdDescriptorType(psdformat.read_signature(fh))
            value_cls = PSD_DESCRIPTOR_TYPE.get(type_code)
            if value_cls is None:
                msg = f'unknown descriptor type: {type_code!r}'
                raise ValueError(msg)
            items[key] = value_cls.read(fh, psdformat)
        return name, classid, items

    def write(
        self, fh: BinaryIO, psdformat: PsdFormat, /, *, version: int = 0
    ) -> int:
        """Write descriptor structure to file."""
        written = 0
        if version:
            written += psdformat.write(fh, 'I', version)
        return written + self._write_body(fh, psdformat)

    def _write_body(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write name, class ID, and items to open file."""
        written = PsdUnicodeString(value=self.name).write(fh, psdformat)
        written += PsdIdString(value=self.classid).write(fh, psdformat)
        written += psdformat.write(fh, 'I', len(self.items))

        for key, value in self.items.items():
            written += PsdIdString(value=key).write(fh, psdformat)
            written += value.type.write(fh, psdformat.byteorder)
            written += value.write(fh, psdformat)

        return written

    def __repr__(self) -> str:
        sz = len(self.items)
        if sz:
            items_repr = ',\n'.join(
                f'{k!r}: {v!r}' for k, v in self.items.items()
            )
            items = f'items={{  # {sz}\n    {indent(items_repr)},\n}},'
        else:
            items = 'items={},'
        return indent(
            f'{self.__class__.__name__}(',
            f'classid={self.classid!r},',
            f'name={self.name!r},' if self.name else '',
            items,
            end='\n)',
        )


@dataclass(repr=False, eq=False)
class PsdDescriptorGlobalObject(PsdDescriptorStruct):
    """Global object descriptor structure."""

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.GLOBAL_OBJECT, init=False, repr=False
    )


@dataclass(repr=False, eq=False)
class PsdDescriptorObjectArray(PsdDescriptorStruct):
    """Object array structure (undocumented)."""

    count: int = 0

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.OBJECT_ARRAY, init=False, repr=False
    )

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        /,
        *,
        version: int = 0,
    ) -> Self:
        """Return instance from open file."""
        del version  # unused
        count = psdformat.read(fh, 'I')
        name, classid, items = cls._read_body(fh, psdformat)
        return cls(classid=classid, name=name, items=items, count=count)

    def write(
        self, fh: BinaryIO, psdformat: PsdFormat, /, *, version: int = 0
    ) -> int:
        """Write object array to open file."""
        del version  # unused
        written = psdformat.write(fh, 'I', self.count)
        return written + self._write_body(fh, psdformat)


@dataclass(eq=False)
class PsdDescriptorReference(PsdDescriptorValueABC):
    """Reference value."""

    items: list[PsdReferenceItemABC]

    type: PsdDescriptorType = field(
        default=PsdDescriptorType.REFERENCE, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        count = psdformat.read(fh, 'I')
        items: list[PsdReferenceItemABC] = []

        for _ in range(count):
            ref_type_code = PsdReferenceType(psdformat.read_signature(fh))
            ref_cls = PSD_REFERENCE_TYPE.get(ref_type_code)
            if ref_cls is None:
                msg = f'unknown reference type: {ref_type_code!r}'
                raise ValueError(msg)
            items.append(ref_cls.read(fh, psdformat))

        return cls(items=items)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = psdformat.write(fh, 'I', len(self.items))
        for item in self.items:
            written += item.type.write(fh, psdformat.byteorder)
            written += item.write(fh, psdformat)
        return written

    def __repr__(self) -> str:
        if not self.items:
            return f'{self.__class__.__name__}(items=[])'
        sz = len(self.items)
        items_repr = ',\n'.join(f'{item!r}' for item in self.items)
        return indent(
            f'{self.__class__.__name__}(',
            f'items=[  # {sz}\n    {indent(items_repr)},\n],',
            end='\n)',
        )


class PsdReferenceItemABC(metaclass=abc.ABCMeta):
    """Abstract base class for reference items."""

    type: PsdReferenceType

    @classmethod
    @abc.abstractmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""

    @abc.abstractmethod
    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write value to open file."""

    def tobytes(self, psdformat: PsdFormat, /) -> bytes:
        """Return instance values as bytes."""
        with io.BytesIO() as fh:
            self.write(fh, psdformat)
            return fh.getvalue()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PsdReferenceItemABC)
            and type(self) is type(other)
            and self.tobytes(PsdFormat.BE32BIT)
            == other.tobytes(PsdFormat.BE32BIT)
        )

    def __hash__(self) -> int:
        return hash((type(self), self.tobytes(PsdFormat.BE32BIT)))


@dataclass(eq=False)
class PsdReferenceProperty(PsdReferenceItemABC):
    """Property reference item."""

    name: str
    classid: PsdIdType
    keyid: PsdIdType

    type: PsdReferenceType = field(
        default=PsdReferenceType.PROPERTY, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        name = PsdUnicodeString.read(fh, psdformat).value
        classid = PsdIdString.read(fh, psdformat).value
        keyid = PsdIdString.read(fh, psdformat).value
        return cls(name=name, classid=classid, keyid=keyid)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = PsdUnicodeString(value=self.name).write(fh, psdformat)
        written += PsdIdString(value=self.classid).write(fh, psdformat)
        written += PsdIdString(value=self.keyid).write(fh, psdformat)
        return written


@dataclass(eq=False)
class PsdReferenceClass(PsdReferenceItemABC):
    """Class reference item."""

    name: str
    classid: PsdIdType

    type: PsdReferenceType = field(
        default=PsdReferenceType.CLASS, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        name = PsdUnicodeString.read(fh, psdformat).value
        classid = PsdIdString.read(fh, psdformat).value
        return cls(name=name, classid=classid)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = PsdUnicodeString(value=self.name).write(fh, psdformat)
        written += PsdIdString(value=self.classid).write(fh, psdformat)
        return written


@dataclass(eq=False)
class PsdReferenceEnumerated(PsdReferenceItemABC):
    """Enumerated reference item."""

    name: str
    classid: PsdIdType
    typeid: PsdIdType
    value: PsdIdType

    type: PsdReferenceType = field(
        default=PsdReferenceType.ENUMERATED, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        name = PsdUnicodeString.read(fh, psdformat).value
        classid = PsdIdString.read(fh, psdformat).value
        typeid = PsdIdString.read(fh, psdformat).value
        value = PsdIdString.read(fh, psdformat).value
        return cls(name=name, classid=classid, typeid=typeid, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = PsdUnicodeString(value=self.name).write(fh, psdformat)
        written += PsdIdString(value=self.classid).write(fh, psdformat)
        written += PsdIdString(value=self.typeid).write(fh, psdformat)
        written += PsdIdString(value=self.value).write(fh, psdformat)
        return written


@dataclass(eq=False)
class PsdReferenceOffset(PsdReferenceItemABC):
    """Offset reference item."""

    name: str
    classid: PsdIdType
    offset: int

    type: PsdReferenceType = field(
        default=PsdReferenceType.OFFSET, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        name = PsdUnicodeString.read(fh, psdformat).value
        classid = PsdIdString.read(fh, psdformat).value
        offset = psdformat.read(fh, 'i')
        return cls(name=name, classid=classid, offset=offset)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = PsdUnicodeString(value=self.name).write(fh, psdformat)
        written += PsdIdString(value=self.classid).write(fh, psdformat)
        written += psdformat.write(fh, 'i', self.offset)
        return written


@dataclass(eq=False)
class PsdReferenceIdentifier(PsdReferenceItemABC):
    """Identifier reference item."""

    value: int

    type: PsdReferenceType = field(
        default=PsdReferenceType.IDENTIFIER, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value = psdformat.read(fh, 'I')
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        return psdformat.write(fh, 'I', self.value)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False)
class PsdReferenceIndex(PsdReferenceItemABC):
    """Index reference item."""

    value: int

    type: PsdReferenceType = field(
        default=PsdReferenceType.INDEX, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        value = psdformat.read(fh, 'i')
        return cls(value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        return psdformat.write(fh, 'i', self.value)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


@dataclass(eq=False)
class PsdReferenceName(PsdReferenceItemABC):
    """Name reference item."""

    name: str
    classid: PsdIdType
    value: str

    type: PsdReferenceType = field(
        default=PsdReferenceType.NAME, init=False, repr=False
    )

    @classmethod
    def read(cls, fh: BinaryIO, psdformat: PsdFormat, /) -> Self:
        """Return instance from open file."""
        name = PsdUnicodeString.read(fh, psdformat).value
        classid = PsdIdString.read(fh, psdformat).value
        value = PsdUnicodeString.read(fh, psdformat).value
        return cls(name=name, classid=classid, value=value)

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance to open file."""
        written = PsdUnicodeString(value=self.name).write(fh, psdformat)
        written += PsdIdString(value=self.classid).write(fh, psdformat)
        written += PsdUnicodeString(value=self.value).write(fh, psdformat)
        return written


@dataclass(repr=False, eq=False)
class PsdDescriptor(PsdKeyABC):
    """Tagged block containing a versioned descriptor structure.

    Drop-in replacement for the opaque ``psdtags.PsdDescriptor``.
    The 4-byte fields preceding the descriptor version are stored in
    big-endian order in `prefix`.
    Trailing data and data that cannot be parsed are kept as opaque bytes
    in `suffix` and `prefix`, and cannot be converted to another byte order.
    Re-serialized descriptors are not guaranteed to be byte-identical.

    """

    key: PsdKey
    psdformat: PsdFormat
    descriptor: PsdDescriptorStruct | None
    prefix: bytes = b''
    suffix: bytes = b''

    VERSION: ClassVar[int] = 16

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        key: PsdKey,
        /,
        length: int,
    ) -> Self:
        """Return instance from open file."""
        data = fh.read(length)
        start = PSD_DESCRIPTOR_PREFIX.get(key, 0)
        descriptor, end = _read_descriptor(
            data, psdformat, start, f'<{cls.__name__} {enumstr(key)}>'
        )
        if descriptor is None:
            return cls(
                key=key, psdformat=psdformat, descriptor=None, prefix=data
            )
        prefix = data[:start]
        if psdformat.byteorder == '<':
            prefix = _swap_words(prefix)
        return cls(
            key=key,
            psdformat=psdformat,
            descriptor=descriptor,
            prefix=prefix,
            suffix=data[end:],
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance values to open file."""
        if (
            self._is_byteorder_specific
            and psdformat.byteorder != self.psdformat.byteorder
        ):
            msg = f'can not write opaque bytes as {psdformat}'
            raise ValueError(msg)
        prefix = self.prefix
        if self.descriptor is not None and psdformat.byteorder == '<':
            prefix = _swap_words(prefix)
        written = fh.write(prefix)
        if self.descriptor is not None:
            written += self.descriptor.write(
                fh, psdformat, version=self.VERSION
            )
        written += fh.write(self.suffix)
        return written

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PsdDescriptor)
            and self.key == other.key
            and self.descriptor == other.descriptor
            and self.prefix == other.prefix
            and self.suffix == other.suffix
            and (
                not self._is_byteorder_specific
                or self.psdformat.byteorder == other.psdformat.byteorder
            )
        )

    def __hash__(self) -> int:
        return hash((self.key, self.descriptor, self.prefix, self.suffix))

    @property
    def _is_byteorder_specific(self) -> bool:
        """Instance contains opaque bytes of unknown structure."""
        # zero padding is byte order independent
        return bool(self.suffix.strip(b'\0')) or (
            self.descriptor is None and len(self.prefix) > 1
        )

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'{enumstr(self.key)},',
            f'psdformat={enumstr(self.psdformat)},',
            _repr_opaque('prefix', self.prefix),
            f'descriptor={self.descriptor!r},',
            _repr_opaque('suffix', self.suffix),
            end='\n)',
        )


@dataclass(repr=False, eq=False)
class PsdDescriptorBlock(PsdResourceBlockABC):
    """Image resource block containing a versioned descriptor structure.

    Drop-in replacement for the opaque ``psdtags.PsdDescriptorBlock``.
    Trailing data and data that cannot be parsed are kept as opaque bytes
    in `suffix` and `prefix`.
    Re-serialized descriptors are not guaranteed to be byte-identical.

    """

    resourceid: PsdResourceId
    descriptor: PsdDescriptorStruct | None
    name: str = ''
    prefix: bytes = b''
    suffix: bytes = b''

    VERSION: ClassVar[int] = 16

    @classmethod
    def read(
        cls,
        fh: BinaryIO,
        psdformat: PsdFormat,
        resourceid: PsdResourceId,
        /,
        name: str,
        length: int,
    ) -> Self:
        """Return instance from open file."""
        data = fh.read(length)
        descriptor, end = _read_descriptor(
            data, psdformat, 0, f'<{cls.__name__} {enumstr(resourceid)}>'
        )
        if descriptor is None:
            return cls(
                resourceid=resourceid, descriptor=None, name=name, prefix=data
            )
        return cls(
            resourceid=resourceid,
            descriptor=descriptor,
            name=name,
            suffix=data[end:],
        )

    def write(self, fh: BinaryIO, psdformat: PsdFormat, /) -> int:
        """Write instance values to open file."""
        written = fh.write(self.prefix)
        if self.descriptor is not None:
            written += self.descriptor.write(
                fh, psdformat, version=self.VERSION
            )
        written += fh.write(self.suffix)
        return written

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PsdDescriptorBlock)
            and self.resourceid == other.resourceid
            and self.name == other.name
            and self.descriptor == other.descriptor
            and self.prefix == other.prefix
            and self.suffix == other.suffix
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.resourceid,
                self.name,
                self.descriptor,
                self.prefix,
                self.suffix,
            )
        )

    def __repr__(self) -> str:
        return indent(
            f'{self.__class__.__name__}(',
            f'{enumstr(self.resourceid)},',
            f'name={self.name!r},' if self.name else '',
            _repr_opaque('prefix', self.prefix),
            f'descriptor={self.descriptor!r},',
            _repr_opaque('suffix', self.suffix),
            end='\n)',
        )


def _read_descriptor(
    data: bytes, psdformat: PsdFormat, start: int, label: str, /
) -> tuple[PsdDescriptorStruct | None, int]:
    """Return versioned descriptor at start of data and its end position."""
    try:
        with io.BytesIO(data) as fh:
            fh.seek(start)
            descriptor = PsdDescriptorStruct.read(fh, psdformat, version=16)
            return descriptor, fh.tell()
    except (ValueError, OSError, struct.error) as exc:
        logger().warning(f'{label} failed to parse descriptor: {exc!r}')
        return None, 0


def _swap_words(data: bytes, /) -> bytes:
    """Return data with byte order of each 4-byte word reversed."""
    fmt = f'{len(data) // 4}I'
    return struct.pack('>' + fmt, *struct.unpack('<' + fmt, data))


def _repr_opaque(name: str, value: bytes, /) -> str:
    """Return keyword argument representation of opaque bytes."""
    if not value:
        return ''
    if len(value) > REPR_MAXLEN:
        return f'{name}=...,  # bytes({len(value)})'
    return f'{name}={value!r},'


# number of opaque bytes preceding the descriptor version
PSD_DESCRIPTOR_PREFIX: dict[PsdKey, int] = {
    PsdKey.VECTOR_STROKE_CONTENT_DATA: 4,  # key
    PsdKey.VECTOR_ORIGINATION_DATA: 4,  # version
    PsdKey.SMART_OBJECT_LAYER_DATA: 8,  # identifier and version
}

PSD_DESCRIPTOR_TYPE: dict[PsdDescriptorType, type[PsdDescriptorValueABC]] = {
    PsdDescriptorType.REFERENCE: PsdDescriptorReference,
    PsdDescriptorType.DESCRIPTOR: PsdDescriptorStruct,
    PsdDescriptorType.LIST: PsdDescriptorList,
    PsdDescriptorType.DOUBLE: PsdDescriptorFloat,
    PsdDescriptorType.UNIT_FLOAT: PsdDescriptorFloatUnit,
    PsdDescriptorType.STRING: PsdDescriptorString,
    PsdDescriptorType.ENUMERATED: PsdDescriptorEnum,
    PsdDescriptorType.INTEGER: PsdDescriptorInt,
    PsdDescriptorType.LARGE_INTEGER: PsdDescriptorLong,
    PsdDescriptorType.BOOLEAN: PsdDescriptorBool,
    PsdDescriptorType.GLOBAL_OBJECT: PsdDescriptorGlobalObject,
    PsdDescriptorType.CLASS: PsdDescriptorClass,
    PsdDescriptorType.GLOBAL_CLASS: PsdDescriptorGlobalClass,
    PsdDescriptorType.ALIAS: PsdDescriptorAlias,
    PsdDescriptorType.RAW_DATA: PsdDescriptorRaw,
    PsdDescriptorType.UNIT_FLOATS: PsdDescriptorFloatUnits,
    PsdDescriptorType.OBJECT_ARRAY: PsdDescriptorObjectArray,
    PsdDescriptorType.PATH: PsdDescriptorPath,
}

PSD_REFERENCE_TYPE: dict[PsdReferenceType, type[PsdReferenceItemABC]] = {
    PsdReferenceType.PROPERTY: PsdReferenceProperty,
    PsdReferenceType.CLASS: PsdReferenceClass,
    PsdReferenceType.ENUMERATED: PsdReferenceEnumerated,
    PsdReferenceType.OFFSET: PsdReferenceOffset,
    PsdReferenceType.IDENTIFIER: PsdReferenceIdentifier,
    PsdReferenceType.INDEX: PsdReferenceIndex,
    PsdReferenceType.NAME: PsdReferenceName,
}
