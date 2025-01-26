# SPDX-License-Identifier: BSD-3-Clause

'''
Definition for the PIPE (PHY Interface For the PCI Express* and USB 3.0 Architectures) interface used
to abstract away transceiver implementation details.


This currently implements Version 3.0 of the PIPE specification, which can be found archived here:
https://web.archive.org/web/20240118024533/https://www.intel.in/content/dam/doc/white-paper/usb3-phy-interface-pci-express-paper.pdf
'''

from typing            import Literal

from torii.hdl         import Elaboratable, Signal, Const

from ..types.errors    import PIPEInterfaceError
from ..types.constants import LinkSpeed

__all__ = (
	'PIPEInterface',
)

class PIPEInterface(Elaboratable):
	'''
	Torii PHY Interface for the PCI Express and USB SuperSpeed Architectures (PIPE)
	definition.

	This specific interface attempts to be fully compliant with Version 3.0 of the specification.

	Signal direction is from the perspective of the PHY, i.e. a signal described as an ``output``
	is driven by the PHY and received by the MAC.


	Note
	----
	This is not a "true" PIPE interface in the full definition of the spec, as we don't handle
	all of the super gritty details of the PHY implementation, or link aggregation, or platform
	specific implementation details here. All of that is left for the specializations, this only
	provides the "electrical" internal interface that is PIPE compatible for upstream consumers
	to not care about the guts of PHY implementation.

	Parameters
	----------
	width : Literal[8, 16, 32]
		Interface tx and rx bus width in bits, which is ``width // 8`` in symbol width.
		(default: 8 bits / 1 symbol)

	Attributes
	----------
	width_bits : int
		The PIPE Interface data path width in bits.

	width_symbol' : int
		The PIPE interface data path width in symbols (``width_bits // 8``)


	rst : Signal, in
		Active-high asynchronous transmitter and receiver reset.
		**Note**: This signal is Active-low in the PIPE Specification.

	clk : Signal, in
		PHY transmitter / receiver reference clock.

	pclk : Signal, out
		Parallel interface data clock. All data movement over the interface is synchronized
		to the positive edge of this clock unless otherwise noted. The clock frequency depends
		on the combination of ``rate`` and ``phy_mode`` and may be up to 500MHz


	tx_data : Signal(width_bits), in
	rx_data : Signal(width_bits), out
		Interface data bus, for the 16-bit wide bus, bits ``7:0`` hold the first symbol and bits ``15:8``
		hold the second symbol. In 32-bit mode, bits ``23:16`` are the third symbol and ``31:24`` are
		the fourth symbol. Transmission is in symbol-order (1, 2, 3, 4).

	tx_datak : Signal(width_symbol), in
	rx_datak : Signal(width_symbol), out
		The Data/Control signaling for the symbol in the given position on the data bus. For multi-symbol
		transmit busses, bit ``0`` always is the lowest symbol, and ``n`` is always the upper symbol.


	powerdown : Signal(2), in
		Transceiver power state.

	rate : Signal(LinkSpeed), in
		Set the link signaling rate.

	tx_loopback : Signal, in
		Instruct the PHY transceiver to enable loopback mode or begin rx detection.

	tx_elec_idle : Signal, in
		Section 6.20

	tx_compliance : Signal, in
		Set the running disparity to negative. Used when transmitting the PCIe compliance pattern.

	tx_deemph : Signal(2), in
		Transmitter deemphasis level selection; 0: -6dB, 1: -3.5dB, 2: 0dB.

	tx_margin : Signal(3), in
		Transmitter voltage level selection.

		+-------+-----------------------+
		| Value | Description           |
		+=======+=======================+
		| ``0`` | Nominal Range         |
		+-------+-----------------------+
		| ``1`` | 800-1200mV Full Swing |
		|       | 400-700mV Half Swing  |
		+-------+-----------------------+
		| ``2`` | Vendor Defined        |
		+-------+-----------------------+
		| ``3`` | Vendor Defined        |
		+-------+-----------------------+
		| ``4`` | 200-400mV Full Swing  |
		|       | 100-200mV Half Swing  |
		+-------+-----------------------+

	tx_swing : Signal, in
		Transmitter voltage swing level selection.

	rx_polarity : Signal, in
		Set the PHY receiver to have RX+ and RX-'s polarity inverted.

	phy_status : Signal, out


	data_bus_width : Const(2), out
		The width of the data bus the PIPE interface is configured for;
		``0b00`` for 32-bit, ``0b01`` for 16-bit, and ``0b10`` for 8-bit.

	rx_valid : Signal, out
		Indicates symbol lock and valid data on ``rx_data`` and ``rx_datak``.

	rx_elec_idle : Signal, out
		Indicates detection on the receiver of aan electrical idle state.

	rx_status : Signal(3), out
		Receiver status and error codes.

	Raises
	------
	PIPEInterfaceError
		If the provided width is not supported by this PIPE interface.
	'''

	# TODO(aki): Enum?
	# Map interface width to data_bus_width signal values
	_WIDTH_MODE = {
		8:  0b10,
		16: 0b01,
		32: 0b00,
	}

	def __init__(self, width: Literal[8, 16, 32] = 8) -> None:
		if width not in (8, 16, 32):
			raise PIPEInterfaceError(
				f'PIPE Interface does not support width of {width}, only 8, 16, or 32'
			)

		# Store both the bit, and symbol widths in the interface
		self.width_bits   = width
		self.width_symbol = width // 8

		# Clocking + Reset
		self.rst  = Signal(name = 'PIPE/Reset')
		self.clk  = Signal(name = 'PIPE/Clk')
		self.pclk = Signal(name = 'PIPE/PClk')

		# Tx/Rx Data
		self.tx_data  = Signal(self.width_bits,   name = 'PIPE/TX/Data')
		self.tx_datak = Signal(self.width_symbol, name = 'PIPE/TX/DataK')

		self.rx_data  = Signal(self.width_bits,   name = 'PIPE/RX/Data')
		self.rx_datak = Signal(self.width_symbol, name = 'PIPE/RX/DataK')

		# Control
		self.powerdown = Signal(2,         name = 'PIPE/Powerdown') # TODO(aki): Enum?
		self.rate      = Signal(LinkSpeed, name = 'PIPE/Rate')

		self.tx_loopback   = Signal(name = 'PIPE/TX/Loopback')
		self.tx_elec_idle  = Signal(name = 'PIPE/TX/ElectricalIdle')
		self.tx_compliance = Signal(name = 'PIPE/TX/Compliance')
		self.tx_deemph     = Signal(2, name = 'PIPE/TX/Deemphasis') # TODO(aki): Enum?
		self.tx_margin     = Signal(3, name = 'PIPE/TX/Margin') # TODO(aki): Enum?
		self.tx_swing      = Signal(name = 'PIPE/TX/Swing')

		self.rx_polarity = Signal(name = 'PIPE/RX/Polarity')

		# Status
		self.phy_status     = Signal(name = 'PIPE/PHYStatus')
		self.data_bus_width = Const(self._WIDTH_MODE[self.width_bits], 2)

		self.rx_valid     = Signal(name = 'PIPE/RX/Valid')
		self.rx_elec_idle = Signal(name = 'PIPE/RX/ElectricalIdle')
		self.rx_status    = Signal(3, name = 'PIPE/RX/Status') # TODO(aki): Enum?
