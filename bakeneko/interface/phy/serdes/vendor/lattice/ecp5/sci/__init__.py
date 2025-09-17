# SPDX-License-Identifier: BSD-3-Clause

'''
Lattice Semiconductor ECP5/ECP5-5G devices have something called the SerDes Client Interface
or SCI. It is an interface accessible from the FPGA fabric to allow for configuring and inspecting
the status of a :py:class:`DCU <bakeneko.interface.phy.serdes.vendor.lattice.ecp5.lattice.dcu.DCU>`
and it's channels.
'''

from torii.build.plat import Platform
from torii.hdl.dsl    import Module
from torii.hdl.ir     import Elaboratable

from .registers       import CHRegister, DCURegister

__all__ = (
	'SCI',
)


class SCI(Elaboratable):
	'''
	Simple interface to interact with the ECP5/ECP5G's SCI of a single DCU.

	Attributes
	----------


	'''

	def __init__(self) -> None:
		pass

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		return m
