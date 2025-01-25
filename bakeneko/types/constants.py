# SPDX-License-Identifier: BSD-3-Clause

'''
Various constants used throughout Bakeneko.
'''

from typing import NamedTuple
from enum   import IntEnum, auto, unique

__all__ = (
	'LinkSpeed',
	'LinkWidth',
	'PCIeStandard',
	'LinkState',

	'PCIeConfiguration',
	'VALID_PCIE_CONFIGURATIONS',
)

@unique
class LinkSpeed(IntEnum):
	''' PCIe Link Speeds '''

	LS2_5  = auto() # PCIe v1.0/v1.1
	''' 2.5 GT/s '''
	LS5_0  = auto() # PCIe v2.0
	''' 5 GT/s '''
	LS8_0  = auto() # PCIe v3.0
	''' 8 GT/s '''
	LS16_0 = auto() # PCIe v4.0
	''' 16 GT/s '''
	LS32_0 = auto() # PCIe v5.0
	''' 32 GT/s '''
	LS64_0 = auto() # PCIe v6.0/v6.2/v6.4
	''' 64 GT/s '''
	LS128_0 = auto()
	''' 128 GT/s ''' # PCIe v7.0

	UNKNOWN = auto()
	''' Unknown '''

	def __str__(self) -> str:
		match self:
			case LinkSpeed.LS2_5:
				return '2.5 GT/s'
			case LinkSpeed.LS5_0:
				return '5 GT/s'
			case LinkSpeed.LS8_0:
				return '8 GT/s'
			case LinkSpeed.LS16_0:
				return '16 GT/s'
			case LinkSpeed.LS32_0:
				return '32 GT/s'
			case LinkSpeed.LS64_0:
				return '64 GT/s'
			case LinkSpeed.LS128_0:
				return '128 GT/s'
			case LinkSpeed.UNKNOWN:
				return 'Unknown'
			case _:
				return 'INVALID'

	@staticmethod
	def from_str(speed: str) -> 'LinkSpeed':
		match speed:
			case '2.5 GT/s' | '2.5 GT/s PCIe':
				return LinkSpeed.LS2_5
			case '5 GT/s' | '5.0 GT/s PCIe':
				return LinkSpeed.LS5_0
			case '8 GT/s' | '8.0 GT/s PCIe':
				return LinkSpeed.LS8_0
			case '16 GT/s' | '16.0 GT/s PCIe':
				return LinkSpeed.LS16_0
			case '32 GT/s' | '32.0 GT/s PCIe':
				return LinkSpeed.LS32_0
			case '64 GT/s' | '64.0 GT/s PCIe':
				return LinkSpeed.LS64_0
			case '128 GT/s' | '128.0 GT/s PCIe':
				return LinkSpeed.LS128_0
			case _:
				return LinkSpeed.UNKNOWN


@unique
class LinkWidth(IntEnum):
	''' PCIe Link Widths '''

	X1  = 1
	''' PCIe x1 '''
	X2  = 2
	''' PCIe x2 '''
	X4  = 4
	''' PCIe x4 '''
	X8 = 8
	''' PCIe x8 '''
	X12 = 12
	''' PCIe x12 '''
	X16 = 16
	''' PCIe x16 '''
	X32 = 32
	''' PCIe x32 '''

	UNKNOWN = 0
	''' Unknown '''

	def __str__(self) -> str:
		match self:
			case LinkWidth.X1:
				return 'x1'
			case LinkWidth.X2:
				return 'x2'
			case LinkWidth.X4:
				return 'x4'
			case LinkWidth.X8:
				return 'x8'
			case LinkWidth.X12:
				return 'x12'
			case LinkWidth.X16:
				return 'x16'
			case LinkWidth.X32:
				return 'x32'
			case LinkWidth.UNKNOWN:
				return 'Unknown'
			case _:
				return 'INVALID'

	@staticmethod
	def from_str(width: str) -> 'LinkWidth':
		match width:
			case 'x1':
				return LinkWidth.X1
			case 'x2':
				return LinkWidth.X2
			case 'x4':
				return LinkWidth.X4
			case 'x8':
				return LinkWidth.X8
			case 'x12':
				return LinkWidth.X12
			case 'x16':
				return LinkWidth.X16
			case 'x32':
				return LinkWidth.X32
			case _:
				return LinkWidth.UNKNOWN

@unique
class PCIeStandard(IntEnum):
	''' PCIe Version '''

	PCIE_1 = auto()
	''' PCIe v1.0/v1.1 '''
	PCIE_2 = auto()
	''' PCIe v2.0/v2.1 '''
	PCIE_3 = auto() # NOTE(aki): Unimplemented
	''' PCIe v3.0 '''
	PCIE_4 = auto() # NOTE(aki): Unimplemented
	''' PCIe v4.0 '''
	PCIE_5 = auto() # NOTE(aki): Unimplemented
	''' PCIe v5.0 '''
	PCIE_6 = auto() # NOTE(aki): Unimplemented
	''' PCIe v6.0/v6.2/v6.4 '''
	PCIE_7 = auto() # NOTE(aki): Unimplemented
	''' PCIe v7.0 '''

	def __str__(self) -> str:
		match self:
			case PCIeStandard.PCIE_1:
				return 'v1.1'
			case PCIeStandard.PCIE_2:
				return 'v2.1'
			case PCIeStandard.PCIE_3:
				return 'v3.0'
			case PCIeStandard.PCIE_4:
				return 'v4.0'
			case PCIeStandard.PCIE_5:
				return 'v5.0'
			case PCIeStandard.PCIE_6:
				return 'v6.0'
			case PCIeStandard.PCIE_7:
				return 'v7.0'
			case _:
				return 'INVALID'


class PCIeConfiguration(NamedTuple):
	standard: PCIeStandard
	link_speeds: tuple[LinkSpeed, ...]
	link_widths: tuple[LinkWidth, ...]

VALID_PCIE_CONFIGURATIONS: tuple[PCIeConfiguration, ...] = (
	(
		PCIeStandard.PCIE_1,
		(LinkSpeed.LS2_5, ),
		(LinkWidth.X1, LinkWidth.X2, LinkWidth.X4, LinkWidth.X8, LinkWidth.X12, LinkWidth.X16, LinkWidth.X32, )
	),
	(
		PCIeStandard.PCIE_2,
		(LinkSpeed.LS5_0, ),
		(LinkWidth.X1, LinkWidth.X2, LinkWidth.X4, LinkWidth.X8, LinkWidth.X12, LinkWidth.X16, LinkWidth.X32, )
	),
	(
		PCIeStandard.PCIE_3,
		(LinkSpeed.LS8_0, ),
		(LinkWidth.X1, LinkWidth.X2, LinkWidth.X4, LinkWidth.X8, LinkWidth.X12, LinkWidth.X16, LinkWidth.X32, )
	),
	(
		PCIeStandard.PCIE_4,
		(LinkSpeed.LS16_0, ),
		(LinkWidth.X1, LinkWidth.X2, LinkWidth.X4, LinkWidth.X8, LinkWidth.X12, LinkWidth.X16, LinkWidth.X32, )
	),
	(
		PCIeStandard.PCIE_5,
		(LinkSpeed.LS32_0, ),
		(LinkWidth.X1, LinkWidth.X2, LinkWidth.X4, LinkWidth.X8, LinkWidth.X12, LinkWidth.X16, LinkWidth.X32, )
	),
	(
		PCIeStandard.PCIE_6,
		(LinkSpeed.LS64_0, ),
		(LinkWidth.X1, LinkWidth.X2, LinkWidth.X4, LinkWidth.X8, LinkWidth.X16, )
	),
	(
		PCIeStandard.PCIE_7,
		(LinkSpeed.LS128_0, ),
		(LinkWidth.X1, LinkWidth.X2, LinkWidth.X4, LinkWidth.X8, LinkWidth.X16, )
	)
)
''' Valid PCIe standard, Link Speed, and Link Width combinations '''


@unique
class LinkState(IntEnum):
	''' PCIe Link State '''

	L0  = auto()
	''' Fully Active '''
	L0S = auto()
	''' Standby '''
	L1  = auto()
	''' Low-power Standby '''
	L2  = auto()
	''' Low-power Sleep '''
	L3  = auto()
	''' Off '''
