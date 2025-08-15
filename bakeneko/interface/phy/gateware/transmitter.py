# SPDX-License-Identifier: BSD-3-Clause

'''
Bakeneko GatewarePHY Transmitter machinery
'''

from torii.build.plat import Platform
from torii.hdl.dsl    import Module
from torii.hdl.ir     import Elaboratable

__all__ = (
	'Transmitter',
)

class Transmitter(Elaboratable):
	'''

	'''

	def __init__(self) -> None:
		pass

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		return m
