# SPDX-License-Identifier: BSD-3-Clause

'''
Lattice Semiconductor ECP5/ECP5-5G Dual-Channel Unit (DCU) Interface.
'''

from enum             import IntFlag, IntEnum, auto, unique

from torii.build.plat import Platform
from torii.hdl.dsl    import Module
from torii.hdl.ir     import Elaboratable, Instance

__all__ = (
	'DCU',
)

@unique
class Channel(IntFlag):
	'''
	The specific channel(s) of the ECP5 DCU to use

	These can be or'd together in order to enable both channels for the
	target DCU
	'''

	CH0 = 0x01
	''' DCU Channel 0 '''
	CH1 = 0x02
	''' DCU Channel 1 '''

	def __str__(self) -> str:
		chans = []

		if Channel.CH0 in self:
			chans.append('CH0')

		if Channel.CH1 in self:
			chans.append('CH1')

		return ','.join(chans)


@unique
class DCUNumber(IntEnum):
	''' The specific DCU to use '''

	DCU0 = auto()
	'''
	Device DCU0, this is usually the leftmost DCU and is capable of sharing the input reference clock
	and/or the bitclock with DCU1.
	'''
	DCU1 = auto()
	'''
	Device DCU0, this is usually the rightmost DCU on the device, and is not capable of sharing the input
	reference/bit clocks, it can however use them from DCU0
	'''

	def __str__(self) -> str:
		match self:
			case DCUNumber.DCU0:
				return 'DCU0'
			case DCUNumber.DCU1:
				return 'DCU1'

class DCU(Elaboratable):
	'''
	Lattice Semiconductor ECP5/ECP5-5G devices have a concept called a Dual-Channel Unit (DCU), it represents
	an encapsulation of 2 SerDes channels.

	Each ECP5/ECP5-5G device has 2 DCUs on the larger 45k an 85k variants, and a single DCU on the smaller 25k variants
	with no DCUs the non-UM devices.

	The overall structure of a DCU looks like this:

	.. code-block::

		╭───────────╮
		│    DCU    │
		├─────┬─────┤
		│ CH0 │ CH1 │
		╰─────┴─────╯

	Within each DCU, there is also an ``EXTREF`` block, which deals with internal reference clock generation
	from the DCU, as well as an auxiliary control channel.

	A more detailed block diagram of a DCU would be as follows:

	.. code-block::

		╭───────────────────────────────╮
		│              DCU              │
		│ ╭─────────╮ ╭─────────╮ ╭───╮ │
		│ │         │ │         │ │ A │ │
		│ │   CH0   │ │   CH1   │ │ U │ │
		│ │         │ │         │ │ X │ │
		│ ├─────────┤ ├─────────┤ ╰───╯ │
		│ │         │ │         │ ╭───╮ │
		│ │   PCS   │ │   PCS   │ │ E │ │
		│ │         │ │         │ │ X │ │
		│ ├─────────┤ ├─────────┤ │ T │ │
		│ │ SERDES0 │ │ SERDES1 │ │ R │ │
		│ ├────┬────┤ ├────┬────┤ │ E │ │
		│ │ RX │ TX │ │ RX │ TX │ │ F │ │
		│ ╰────┴────╯ ╰────┴────╯ ╰───╯ │
		╰───────────────────────────────╯

	For more details on the ECP5 DCUs see the Lattice Technical Note
	`FPGA-TN-02206 <https://www.latticesemi.com/view_document?document_id=50463>`_.

	Note
	----
	Many of the DCU and channel properties are set at elaboration time for the synthesis and
	place-and-route tools, however, many, if not most of them are able to be modified via the
	SerDes Client Interface (``SCI``) for the DCU.

	Parameters
	----------
	dcu: DCUNumber
		The specific DCU on the device to use.

	channel: Channel
		The specific channel or channels to use for the given DCU.

	'''

	def _get_dcu_instance(self) -> Instance:
		dcu = Instance(
			'DCUA',
		)

		return dcu

	def __init__(self, dcu: DCUNumber, channel: Channel) -> None:
		self.dcu_num = dcu
		self.chan    = channel

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		return m
