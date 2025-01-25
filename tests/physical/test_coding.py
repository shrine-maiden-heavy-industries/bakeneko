# SPDX-License-Identifier: BSD-3-Clause

from unittest                 import TestCase

from bakeneko.physical.coding import K, D, Symbol, Symbols

class BakenekoPhysicalCodingTest(TestCase):

	def test_k_sym(self) -> None:
		self.assertEqual(K(28, 0), 0x11C)
		self.assertEqual(K(28, 1), 0x13C)

	def test_d_sym(self) -> None:
		self.assertEqual(D(31, 1), 0x3F)

	def test_symbol(self) -> None:
		for sym in Symbols:
			val = sym.value
			x = val.x()
			y = val.y()

			if val.sym_type == Symbol.Type.CONTROL:
				self.assertEqual(val.value, (K(x, y) & 0xFF))
			else:
				self.assertEqual(val.value, D(x, y))

		self.assertEqual(str(Symbols.COM), 'COM (K28.5)')
		self.assertEqual(str(Symbol(D(30, 5))), 'D30.5')
		self.assertEqual(str(Symbol(K(28, 4))), 'K28.4')
		self.assertEqual(Symbol.from_bits(0b000_11100).value, (K(28, 0) & 0xFF))
		self.assertEqual(
			repr(Symbols.PAD.value),
			'<Symbol: K23.7, value=0xF7, name=\'PAD\', desc=\'LTSSM Initialization\'>'
		)
