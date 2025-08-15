# SPDX-License-Identifier: BSD-3-Clause

'''
Bakeneko pure gateware PCIe PHY
'''

from torii.build.plat import Platform
from torii.hdl.dsl    import Module
from torii.hdl.ir     import Elaboratable

from .receiver        import Receiver
from .transmitter     import Transmitter

__all__ = (
	'GatewarePhy',
)

class GatewarePhy(Elaboratable):
	'''

	'''

	def __init__(self) -> None:
		pass

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		m.submodules.tx = tx = Transmitter()
		m.submodules.rx = rx = Receiver()

		return m
