# SPDX-License-Identifier: BSD-3-Clause

'''
Lattice Semiconductor ECP5/ECP5-5G devices have something called the SerDes Client Interface
or SCI. It is an interface accessible from the FPGA fabric to allow for configuring and inspecting
the status of a :py:class:`DCU <bakeneko.interface.phy.serdes.vendor.lattice.ecp5.lattice.dcu.DCU>`
and it's channels.
'''

from torii.build.plat import Platform
from torii.hdl.ast    import Cat, Signal
from torii.hdl.dsl    import Module
from torii.hdl.rec    import Direction, Record
from torii.hdl.ir     import Elaboratable

from .registers       import CHRegister, DCURegister

__all__ = (
	'SCI',
)


class DCUInterface(Record):
	sci_sel: Signal[1, Direction.FANIN]
	''' DCU Select '''
	sci_en: Signal[1, Direction.FANIN]
	''' DCU SCI enable '''
	sci_en_ch0: Signal[1, Direction.FANIN]
	''' DCU Channel 0 SCI enable '''
	sci_sel_ch0: Signal[1, Direction.FANIN]
	''' DCU Channel 0 select '''
	sci_en_ch1: Signal[1, Direction.FANIN]
	''' DCU Channel 1 SCI enable '''
	sci_sel_ch1: Signal[1, Direction.FANIN]
	''' DCU Channel 1 select '''
	sci_int: Signal[1, Direction.FANOUT]
	''' SCI Interrupt '''
	sci_wrn: Signal[1, Direction.FANIN]
	''' SCI Write Strobe '''
	sci_rd: Signal[1, Direction.FANIN]
	''' SCI Read Strobe '''
	sci_rdata: Signal[8, Direction.FANOUT]
	''' Read port '''
	sci_wdata: Signal[8, Direction.FANIN]
	''' Write port '''
	sci_addr: Signal[6, Direction.FANIN]
	''' Register address '''


class SCI(Elaboratable):
	'''
	Simple interface to interact with the ECP5/ECP5G's SCI of a single DCU.

	Attributes
	----------
	dcu_sel: Signal
		Target DCU

	ch_sel: Signal
		Target DCU Channel

	re: Signal
		Read-enable

	we: Signal
		Write-enable

	done: Signal
		Transaction done

	addr: Signal
		6-bit SCI Register address

	data_w: Signal
		8-bit write data

	data_r: Signal
		8-bit read data

	interrupt: Signal
		The SCI interrupt signals
	'''

	def __init__(self) -> None:
		# Public interface
		self.dcu_sel   = Signal()
		self.ch_sel    = Signal()
		self.re        = Signal()
		self.we        = Signal()
		self.done      = Signal()
		self.addr      = Signal(6)
		self.data_w    = Signal(8)
		self.data_r    = Signal(8)
		self.interrupt = Signal(2)

		# DCU Interfaces
		self.dcu0 = DCUInterface()
		self.dcu1 = DCUInterface()

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

			self.interrupt.eq(Cat(self.dcu0.sci_int, self.dcu1.sci_int)),

			# Hook up the DCU signals
			self.dcu0.sci_wdata.eq(self.sci_data_w),
			self.dcu0.sci_addr.eq(self.sci_addr),
			self.dcu1.sci_wdata.eq(self.sci_data_w),
			self.dcu1.sci_addr.eq(self.sci_addr),
		]

		# Depending on which DCU is selected connect to that DCU's output data bus
		with m.If(self.dcu_sel):
			m.d.comb += [
				self.sci_data_r.eq(self.dcu1.sci_rdata),
			]
		with m.Else():
			m.d.comb += [
				self.sci_data_r.eq(self.dcu0.sci_rdata),
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
