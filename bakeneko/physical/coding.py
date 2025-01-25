# SPDX-License-Identifier: BSD-3-Clause

'''
Line-coding helpers and definitions.
'''

from enum      import Enum, IntEnum

from torii.hdl import Const

__all__ = (
	'K', 'D', 'Symbol', 'Symbols',
)


def K(x: int, y: int)  -> int:
	''' Returns the 8b/10b encoded value for the given K symbol. '''

	return 0x100 | (y << 5) | x

def D(x: int, y: int)  -> int:
	''' Returns the 8b/10b encoded value for the given D symbol '''

	return (y << 5) | x

class Symbol:
	'''
	A simple encapsulation for PCIe 8b/10b named symbols

	Parameters
	----------
	name : str
		The symbol name.

	value : int
		The numerical value of the symbol. Normally the result of a call to :ref:`D` or :ref:`K`.

	sym_type : Symbol.Type
		The type of symbol this is, either Control or Data.

	description : str
		A brief description of this symbol.

	'''

	class Type(IntEnum):
		''' Named symbol type '''
		CONTROL = 0
		DATA    = 1

	@staticmethod
	def control(name: str, value: int, description: str = '') -> 'Symbol':
		''' Construct a named control symbol '''
		return Symbol((value & 0xFF), sym_type = Symbol.Type.CONTROL, name = name, description = description)

	@staticmethod
	def data(name: str, value: int, description: str = '') -> 'Symbol':
		''' Construct a named data symbol '''
		return Symbol(value, sym_type = Symbol.Type.DATA, name = name, description = description)

	@staticmethod
	def from_bits(bits: int, *, name: str = '', description: str = '') -> 'Symbol | None':
		''' Convert a 10-bit code into a Symbol object if possible '''
		x = (bits & 0b00011111)
		y = (bits & 0b11100000) >> 5

		if (bits & 0x1FF) == 0x1EE:
			return None
		else:
			# Check to see if we know about this symbol already
			known_sym = next(filter(lambda s: s.value.decompose() == (x, y), iter(Symbols)), None)
			if known_sym is not None:
				return known_sym.value # Unpack the enum value to a raw Symbol

			# If we don't we can construct one with an empty name/desc
			sym_type = Symbol.Type.CONTROL if (bits & 0x100) else Symbol.Type.DATA
			return Symbol((y << 5) | x, sym_type = sym_type, name = name, description = description)


	def __init__(self, value: int, *, sym_type: 'Symbol.Type | None' = None, name: str = '', description: str = '') -> None:
		self.value = value

		if sym_type is None:
			self.sym_type = Symbol.Type.CONTROL if (value & 0x100) else Symbol.Type.DATA
		else:
			self.sym_type = sym_type

		self.name        = name
		self.description = description

	def x(self) -> int:
		''' Return the x component of the symbol '''
		return (self.value & 0b00011111)

	def y(self) -> int:
		''' Return the y component of the symbol '''
		return (self.value & 0b11100000) >> 5


	def decompose(self) -> tuple[int, int]:
		''' Decompose a symbol value into an (x, y) pair '''
		return (self.x(), self.y())

	def as_value(self, *, repeat: int = 1) -> Const:
		''' Returns the data value of this symbol as a Torii :ref:`Const` '''

		value = Const(self.value, 8)
		return value.replicate(repeat)

	def as_ctrl(self, *, repeat: int = 1) -> Const:
		''' Returns the ctrl value of this symbol as a Torii :ref:`Const` '''

		ctrl = Const(int(self.sym_type), 1)
		return ctrl.replicate(repeat)

	def __str__(self) -> str:
		ty      = 'K' if self.sym_type == Symbol.Type.CONTROL else 'D'
		sym_rep = f'{ty}{self.x()}.{self.y()}'
		if self.name == '':
			return f'{""}{sym_rep}'
		else:
			return f'{self.name} ({sym_rep})'

	def __repr__(self) -> str:
		ty      = 'K' if self.sym_type == Symbol.Type.CONTROL else 'D'
		sym_rep = f'{ty}{self.x()}.{self.y()}'

		return f'<Symbol: {sym_rep}, value=0x{self.value:02X}, name=\'{self.name}\', desc=\'{self.description}\'>'


class Symbols(Enum):
	''' List of known PCIe named symbols '''

	COM = Symbol.control('COM', K(28, 5), 'Comma')
	STP = Symbol.control('STP', K(27, 7), 'Start Transaction Layer Packet')
	SDP = Symbol.control('SDP', K(28, 2), 'Start Data Link Layer Packet')
	END = Symbol.control('END', K(29, 7), 'End TLP or DLLP')
	EDB = Symbol.control('EDB', K(30, 7), 'End of nullified TLP')
	PAD = Symbol.control('PAD', K(23, 7), 'LTSSM Initialization')
	SKP = Symbol.control('SKP', K(28, 0), 'Bit rate difference compensation')
	FTS = Symbol.control('FTS', K(28, 1), 'Fast Training Sequence (L0s -> L0)')
	IDL = Symbol.control('IDL', K(28, 3), 'Idle/EIOS')
	RV0 = Symbol.control('RV0', K(28, 4), 'Reserved')
	RV1 = Symbol.control('RV1', K(28, 6), 'Reserved')
	EIE = Symbol.control('EIE', K(28, 7), 'Electrical Idle Exit')

	def __str__(self) -> str:
		return str(self.value)
