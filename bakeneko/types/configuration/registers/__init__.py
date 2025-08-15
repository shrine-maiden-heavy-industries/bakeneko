# SPDX-License-Identifier: BSD-3-Clause

'''
Machinery for defining registers for the PCIe capability structures and configuration space.
'''

from enum      import IntEnum, auto, unique
from itertools import takewhile
from typing    import Any

from construct import (
	BitsInteger, BytesInteger, Bytewise, Default,
	Int8sb, Int8sl, Int8ub, Int8ul, Int16sb, Int16sl, Int16ub, Int16ul,
	Int24sb, Int24sl, Int24ub, Int24ul, Int32sb, Int32sl, Int32ub, Int32ul,
	Int64sb, Int64sl, Int64ub, Int64ul, Renamed, Struct, Subconstruct,
)

from torii.util.tracer import get_var_name

__all__ = (
	'PCIOnlyField',
	'Register',
	'RegisterField',
	'RegisterType',
	'ReservedField',
)

@unique
class RegisterType(IntEnum):
	''' Describes the type of the PCIe register/field and how it behaves. '''

	HWINIT = auto()
	'''
	Hardware Initialized Register/Field

	Bits are initialized by firmware or hardware such as pin strapping or EEPROM values.

	Values are read-only after initialization, and can only be reset with a fundamental bus reset.
	'''

	RO     = auto()
	'''
	Read-Only Register/Field

	Bits are read-only and can not be altered by software, and may be set via pin strapping or EEPROM
	initialization.
	'''

	RW     = auto()
	'''
	Read/Write Register/Field

	Bits are read/write and may be set or cleared by software to the desired state.
	'''

	RW1C   = auto()
	'''
	Read-Only Status, Write `1` to clear

	Bits indicate some status when read, and status is reset/cleared when writing a `1` value to the
	register/field. Writing a `0` has no effect.
	'''

	ROS    = auto()
	'''
	Read-Only, Sticky

	Bits are read-only and can not be altered by software, they are not initialized or modified by a
	hot reset.

	If noted, devices that consume auxiliary power must preserve sticky register values when auxiliary power
	is enabled. When this is the case, bits are not initialized or modified by hot, warm, or cold resets.
	'''

	RWS    = auto()
	'''
	Read/Write, Sticky

	Bits are read/write and may be set or cleared by software, they are not initialized or modified by a
	hot reset.

	If noted, devices that consume auxiliary power must preserve sticky register values when auxiliary power
	is enabled. When this is the case, bits are not initialized or modified by hot, warm, or cold resets.
	'''

	RW1CS  = auto()
	'''
	Read-Only Status, Write `1` to clear, Sticky

	Bits indicate some status when read, and status is reset/cleared when writing a `1` value to the
	register/field. Writing a `0` has no effect, they are not initialized or modified by a
	hot reset.

	If noted, devices that consume auxiliary power must preserve sticky register values when auxiliary power
	is enabled. When this is the case, bits are not initialized or modified by hot, warm, or cold resets.
	'''

	RSVDP  = auto()
	'''
	Reserved and Preserved

	Reserved for future Read/Write fields.

	Bits are read-only and must return 0 when read, software must preserve the value read for writes to bits.
	'''

	RSVDZ  = auto()
	'''
	Reserved and Zero

	Reserved for future `RW1C` fields.

	Bits are read-only and must return 0 when read, software must write these bits with 0.
	'''

class RegisterField(Subconstruct):
	'''
	PCIe Register Field

	This is a wrapper :py:class:`construct.Subconstruct` to allow for some metadata and automatic
	type deduction to be preformed based on the field name.

	By default PCIe register fields don't have any type prefixing in their name, however
	this class allows for names with a prefix to automatically set the size and type.

	The following table lists the field name prefixes and their type information:

	+----------+-----------------------------------+
	| Prefix   | Type                              |
	+==========+===================================+
	| ``u8l``  | :py:class:`construct.Int8ul`      |
	+----------+-----------------------------------+
	| ``u16l`` | :py:class:`construct.Int16ul`     |
	+----------+-----------------------------------+
	| ``u24l`` | :py:class:`construct.Int24ul`     |
	+----------+-----------------------------------+
	| ``u32l`` | :py:class:`construct.Int32ul`     |
	+----------+-----------------------------------+
	| ``u64l`` | :py:class:`construct.Int64ul`     |
	+----------+-----------------------------------+
	| ``s8l``  | :py:class:`construct.Int8sl`      |
	+----------+-----------------------------------+
	| ``s16l`` | :py:class:`construct.Int16sl`     |
	+----------+-----------------------------------+
	| ``s24l`` | :py:class:`construct.Int24sl`     |
	+----------+-----------------------------------+
	| ``s32l`` | :py:class:`construct.Int32sl`     |
	+----------+-----------------------------------+
	| ``s64l`` | :py:class:`construct.Int64sl`     |
	+----------+-----------------------------------+
	| ``u8b``  | :py:class:`construct.Int8ub`      |
	+----------+-----------------------------------+
	| ``u16b`` | :py:class:`construct.Int16ub`     |
	+----------+-----------------------------------+
	| ``u24b`` | :py:class:`construct.Int24ub`     |
	+----------+-----------------------------------+
	| ``u32b`` | :py:class:`construct.Int32ub`     |
	+----------+-----------------------------------+
	| ``u64b`` | :py:class:`construct.Int64ub`     |
	+----------+-----------------------------------+
	| ``s8b``  | :py:class:`construct.Int8sb`      |
	+----------+-----------------------------------+
	| ``s16b`` | :py:class:`construct.Int16sb`     |
	+----------+-----------------------------------+
	| ``s24b`` | :py:class:`construct.Int24bl`     |
	+----------+-----------------------------------+
	| ``s32b`` | :py:class:`construct.Int32sb`     |
	+----------+-----------------------------------+
	| ``s64b`` | :py:class:`construct.Int64sb`     |
	+----------+-----------------------------------+
	| ``b#``   | :py:class:`construct.BitsInteger` |
	+----------+-----------------------------------+

	An example prefixed field name would be ``u8lAllocLen`` which would define an unsigned
	eight-bit unsigned little-endian integer called ``AllocLen``.

	However, if the ``length`` argument is passed, that will override the prefix
	calculated by the name if any is present.

	Parameters
	----------
	type : RegisterType
		The type of this Register field.

	description : str
		The description of this field.

	Keyword Arguments
	-----------------
	default : Any
		The default value for this field if any.

	length : int
		The length of the field in bits.
	'''

	TYPE_PREFIXES = {
		'u8l':  Int8ul,
		'u16l': Int16ul,
		'u24l': Int24ul,
		'u32l': Int32ul,
		'u64l': Int64ul,
		's8l':  Int8sl,
		's16l': Int16sl,
		's24l': Int24sl,
		's32l': Int32sl,
		's64l': Int64sl,
		'u8b':  Int8ub,
		'u16b': Int16ub,
		'u24b': Int24ub,
		'u32b': Int32ub,
		'u64b': Int64ub,
		's8b':  Int8sb,
		's16b': Int16sb,
		's24b': Int24sb,
		's32b': Int32sb,
		's64b': Int64sb,
	}

	LENGTH_TYPES = {
		1: Int8ul,
		2: Int16ul,
		3: Int24ul,
		4: Int32ul,
		8: Int64ul,
	}

	@classmethod
	def _type_from_prefix(cls, field_name: str):
		'''
		Return appropriate :py:class:`construct.Subconstruct` for given name prefix.

		This method looks at the first few characters of the field name and attempts to
		return the appropriate :py:class:`construct.Subconstruct` type that can store that field.

		The mapping is simple, ``s`` denotes signed, ``u`` denotes unsigned, followed by the size
		in bits, and then an ``l`` or ``b`` to signify the endian; or ``b`` followed by the size in bits if the size is
		not one of the common sizes.

		If the ``length`` for this field is set then it overrides the prefix.

		Parameters
		----------
		field_name : str
			The field name to extract type information from.
		'''

		def _get_prefix(name: str) -> str:
			return ''.join(takewhile(lambda c: not c.isupper(), name))

		pfx = _get_prefix(field_name)

		subcon_type = cls.TYPE_PREFIXES.get(pfx, None)

		if subcon_type is None and len(pfx) >= 2:
			if pfx[0] != 'b':
				raise ValueError(f'The prefix {pfx} is invalid.')
			else:
				sz = int(pfx[1:])
				assert sz > 0, f'Invalid size {sz}'
				subcon_type = BitsInteger(sz)

		return subcon_type

	@classmethod
	def _type_from_size(cls, size: int):
		'''
		Return appropriate :py:class:`construct.Subconstruct` for given size in bits.

		If ``size`` is divisible by a whole number of bytes then an appropriately sized byte
		type is returned, otherwise a :py:class:`construct.BytesInteger` of the requested size
		is returned.

		If ``size`` is not divisible by a whole number of bytes, then a ::py:class:`construct.BitsInteger`
		of the given number of bits wrapped in a :py:class:`construct.Bytewise` is returned.

		Parameters
		----------
		size : int
			The size of the type to get in bits.

		'''
		if size % 8 == 0:
			bc = size // 8
			return Bytewise(cls.LENGTH_TYPES.get(
				bc,
				BytesInteger(bc, signed = False, swapped = True)
			))
		else:
			return BitsInteger(size)

	def __init__(
		self, type: RegisterType, description: str, *, default: Any | None = None, length: int | None = None
	) -> None:
		self.type        = type
		self.description = description
		self.default     = default
		self.len         = length

	def __rtruediv__(self, name: str) -> Renamed:
		'''
		Rename subcon

		This method is overloaded to dynamically construct a :py:class:`construct.Subconstruct`
		for a PCIe register field based on either a name prefix or the specified length.

		Parameters
		----------
		name : str
			The name of the :py:class:`construct.Subconstruct`
		'''

		if self.len is not None:
			subcon_type = self._type_from_size(self.len)
		else:
			subcon_type = self._type_from_prefix(name)

		if subcon_type is None:
			raise ValueError(f'Unable to compute type for \'{name}\', specify a length or prefix name.')

		if self.default is not None:
			subcon_type = Default(subcon_type, self.default)

		# XXX(aki): This is fine type-wise, it's just that `construct` has horrible typing
		return (name / subcon_type) * self.description # type: ignore

class PCIOnlyField(Subconstruct):
	'''
	PCI Only Field

	This field only has meaning for PCI and PCI-X devices, but due to the backwards compatibility is also
	present in the PCIe registers and control structures.
	'''

	def __init__(self, description: str = '', *, default: Any = 0, length = 1):
		self.description = description
		self.default     = default
		self.length      = length

	def __rtruediv__(self, name: str) -> Renamed:
		'''
		Rename subcon

		This method is overloaded to dynamically construct a :py:class:`construct.Subconstruct`
		for a PCIe register field based on either a name prefix or the specified length.

		Parameters
		----------
		name : str
			The name of the :py:class:`construct.Subconstruct`
		'''

		subcon_type = BitsInteger(self.length)

		if self.default is not None:
			subcon_type = Default(subcon_type, self.default)

		# XXX(aki): This is fine type-wise, it's just that `construct` has horrible typing
		return (name / subcon_type) * self.description # type: ignore


def ReservedField(*, length: int = 1) -> Renamed:
	return '_Reserved' / RegisterField(RegisterType.RO, 'Reserved Field', length = length)


class Register(Struct):
	''' '''

	def __init__(
		self, *subcons, type: RegisterType | None = None, description: str = '', default: Any | None = None,
		length: int | None = None, **subconskw,
	) -> None:

		self.name = get_var_name(default = 'Register')

		super().__init__(*subcons, **subconskw)

		self.type        = type
		self.description = description
		self.default     = default
		self.len         = length
