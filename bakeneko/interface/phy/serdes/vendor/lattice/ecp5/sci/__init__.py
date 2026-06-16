# SPDX-License-Identifier: BSD-3-Clause

'''
Lattice Semiconductor ECP5/ECP5-5G devices have something called the SerDes Client Interface
or SCI. It is an interface accessible from the FPGA fabric to allow for configuring and inspecting
the status of a :py:class:`DCU <bakeneko.interface.phy.serdes.vendor.lattice.ecp5.lattice.dcu.DCU>`
and it's channels.
'''

from torii.build.plat import Platform
from torii.hdl.ast    import Signal
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
		self.dcu_sel = Signal()
		self.ch_sel  = Signal()
		self.re      = Signal()
		self.we      = Signal()
		self.done    = Signal()
		self.addr    = Signal(6)
		self.data_w  = Signal(8)
		self.data_r  = Signal(8)

		self.sci_rd     = Signal()
		self.sci_wr_n   = Signal()
		self.sci_addr   = Signal(6)
		self.sci_data_w = Signal(8)
		self.sci_data_r = Signal(8)

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		m.d.comb += [
			self.sci_wr_n.eq(1),
			self.sci_addr.eq(self.addr),
			self.sci_data_w.eq(self.data_w),
		]

		with m.FSM(domain = 'phy', name = 'DCU/SCI') as fsm:
			m.d.comb += [ self.done.eq(fsm.ongoing('IDLE')), ]

			with m.State('IDLE'):
				with m.If(self.we):
					m.next = 'WRITE'
				with m.Elif(self.re):
					m.next = 'READ'
					m.d.comb += [ self.sci_rd.eq(1), ]

			with m.State('WRITE'):
				m.next = 'IDLE'
				m.d.comb += [ self.sci_wr_n.eq(0), ]

			with m.State('READ'):
				m.next = 'IDLE'
				m.d.comb += [ self.sci_rd.eq(1), ]
				m.d.phy += [ self.data_r.eq(self.sci_data_r), ]

		return m
