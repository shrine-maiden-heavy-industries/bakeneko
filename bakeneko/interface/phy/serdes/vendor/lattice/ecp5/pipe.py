# SPDX-License-Identifier: BSD-3-Clause

'''
PIPE interface for Lattice Semiconductor ECP5/ECP5-5G devices.
'''

from torii.build.plat import Platform
from torii.hdl.dsl    import Module
from torii.hdl.ir     import Elaboratable

from .dcu             import DCU
from .sci             import SCI

__all__ = (
	'ECP5SerDesPIPE',
)

class ECP5SerDesPIPE(Elaboratable):
	'''

	'''

	def __init__(self) -> None:
		pass

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		return m
