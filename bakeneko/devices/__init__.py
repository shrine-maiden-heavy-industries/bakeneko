# SPDX-License-Identifier: BSD-3-Clause

'''
Pre-baked PCIe Devices
'''

from torii.build.plat  import Platform
from torii.hdl         import Elaboratable, Module

from ..interface.pipe  import PIPEInterface

class PCIeDevice(Elaboratable):
	'''
	A somewhat generic PCIe device.

	Parameters
	----------
	phy : PIPEInterface
		The PIPE Phy to be used for this device.
	'''

	def __init__(self, *, phy: PIPEInterface) -> None:
		self.phy = phy

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		return m
