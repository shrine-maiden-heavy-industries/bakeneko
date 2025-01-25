# SPDX-License-Identifier: BSD-3-Clause

'''
Specialized errors for Bakeneko gateware related things.
'''

from typing     import Sequence

from .constants import LinkSpeed, LinkWidth, PCIeStandard


__all__ = (
	'PCIeGatewareError',

	'PCIeUnsupportedLinkSpeed',
	'PCIeUnsupportedLinkWidth',
	'PCIeUnsupportedConfiguration',

	'PIPEInterfaceError',
)

class PCIeGatewareError(Exception):
	''' Base class for all PCIe gateware errors. '''
	pass

class PCIeUnsupportedLinkSpeed(PCIeGatewareError):
	'''
	Raised when the given PHY can not reach the needed link speed.

	For instance, if a SerDes PHY only supports up to a 5Gbps link speed, and a request for a
	8Gbps link is given, then this error would be raised.

	Parameters
	----------
	requested : bakeneko.types.constants.LinkSpeed
		The requested PCIe link speed.

	supported : Sequence[bakeneko.types.constants.LinkSpeed]
		The supported PCIe link speeds.

	Attributes
	----------
	requested_speed : bakeneko.types.constants.LinkSpeed
		The requested PCIe link speeds.

	supported_speeds : Sequence[bakeneko.types.constants.LinkSpeed]
		The supported PCIe link speeds.
	'''

	def __init__(self, requested: LinkSpeed, supported: Sequence[LinkSpeed]) -> None:
		super().__init__(
			f'The link speed of {requested} is not supported, only the following: {", ".join(map(str, supported))}.'
		)
		self.requested_speed  = requested
		self.supported_speeds = supported

class PCIeUnsupportedLinkWidth(PCIeGatewareError):
	'''
	Raised when the given PHY can not fit the given link width.

	For instance, if a SerDes PHY only supports up to a x2 link width, and a request for a
	x4 interface is given, then this error would be raised.

	Parameters
	----------
	requested : bakeneko.types.constants.LinkWidth
		The requested PCIe link width.

	supported : Sequence[bakeneko.types.constants.LinkWidth]
		The supported PCIe link widths.

	Attributes
	----------
	requested_width : bakeneko.types.constants.LinkWidth
		The requested PCIe link width.

	supported_widths : Sequence[bakeneko.types.constants.LinkWidth]
		The supported PCIe link widths.
	'''

	def __init__(self, requested: LinkWidth, supported: Sequence[LinkWidth]) -> None:
		super().__init__(
			f'The link width of {requested} is not supported, only the following: {", ".join(map(str, supported))}.'
		)
		self.requested_width  = requested
		self.supported_widths = supported

class PCIeUnsupportedConfiguration(PCIeGatewareError):
	'''
	Raised when an incompatible PCIe configuration is provided.

	For example, if a PCIe configuration with the standard version of v2, but with a link speed of
	16 GT/s.

	Parameters
	----------
	std : bakeneko.types.constants.PCIeStandard
		The version of the PCIe standard.

	speed : bakeneko.types.constants.LinkSpeed.
		The PCIe link speed.

	width : bakeneko.types.constants.LinkWidth.
		The PCIe link width.

	Attributes
	----------
	pcie_standard : bakeneko.types.constants.PCIeStandard
		The version of the PCIe standard.

	link_speed : bakeneko.types.constants.LinkSpeed.
		The PCIe link speed.

	link_width : bakeneko.types.constants.LinkWidth.
		The PCIe link width.
	'''

	def __init__(self, std: PCIeStandard, speed: LinkSpeed, width: LinkWidth) -> None:
		super().__init__(
			f'PCIe standard {std} with link speed of {speed} and link width of {width} is an unsupported configuration.'
		)

		self.pcie_standard = std
		self.link_speed    = speed
		self.link_width    = width


class PIPEInterfaceError(PCIeGatewareError):
	''' Subset of PCIe Gateware errors specific to construction of the PIPE interface. '''
	pass
