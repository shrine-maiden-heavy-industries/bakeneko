# SPDX-License-Identifier: BSD-3-Clause

from unittest                 import TestCase

from bakeneko.types.constants import LinkSpeed, LinkWidth, PCIeStandard

class BakenekoTypesConstantsTest(TestCase):

	def test_link_speed(self) -> None:
		self.assertEqual(LinkSpeed(1), LinkSpeed.LS2_5)
		self.assertEqual(LinkSpeed.from_str('2.5 GT/s'), LinkSpeed.LS2_5)
		self.assertEqual(LinkSpeed.from_str('2.5 GT/s PCIe'), LinkSpeed.LS2_5)
		self.assertEqual(str(LinkSpeed.LS2_5), '2.5 GT/s')

		self.assertEqual(LinkSpeed(2), LinkSpeed.LS5_0)
		self.assertEqual(LinkSpeed.from_str('5 GT/s'), LinkSpeed.LS5_0)
		self.assertEqual(LinkSpeed.from_str('5.0 GT/s PCIe'), LinkSpeed.LS5_0)
		self.assertEqual(str(LinkSpeed.LS5_0), '5 GT/s')

		self.assertEqual(LinkSpeed(3), LinkSpeed.LS8_0)
		self.assertEqual(LinkSpeed.from_str('8 GT/s'), LinkSpeed.LS8_0)
		self.assertEqual(LinkSpeed.from_str('8.0 GT/s PCIe'), LinkSpeed.LS8_0)
		self.assertEqual(str(LinkSpeed.LS8_0), '8 GT/s')

		self.assertEqual(LinkSpeed(4), LinkSpeed.LS16_0)
		self.assertEqual(LinkSpeed.from_str('16 GT/s'), LinkSpeed.LS16_0)
		self.assertEqual(LinkSpeed.from_str('16.0 GT/s PCIe'), LinkSpeed.LS16_0)
		self.assertEqual(str(LinkSpeed.LS16_0), '16 GT/s')

		self.assertEqual(LinkSpeed(5), LinkSpeed.LS32_0)
		self.assertEqual(LinkSpeed.from_str('32 GT/s'), LinkSpeed.LS32_0)
		self.assertEqual(LinkSpeed.from_str('32.0 GT/s PCIe'), LinkSpeed.LS32_0)
		self.assertEqual(str(LinkSpeed.LS32_0), '32 GT/s')

		self.assertEqual(LinkSpeed(6), LinkSpeed.LS64_0)
		self.assertEqual(LinkSpeed.from_str('64 GT/s'), LinkSpeed.LS64_0)
		self.assertEqual(LinkSpeed.from_str('64.0 GT/s PCIe'), LinkSpeed.LS64_0)
		self.assertEqual(str(LinkSpeed.LS64_0), '64 GT/s')

		self.assertEqual(LinkSpeed(7), LinkSpeed.LS128_0)
		self.assertEqual(LinkSpeed.from_str('128 GT/s'), LinkSpeed.LS128_0)
		self.assertEqual(LinkSpeed.from_str('128.0 GT/s PCIe'), LinkSpeed.LS128_0)
		self.assertEqual(str(LinkSpeed.LS128_0), '128 GT/s')

		self.assertEqual(LinkSpeed(8), LinkSpeed.UNKNOWN)
		self.assertEqual(LinkSpeed.from_str('256 GT/s'), LinkSpeed.UNKNOWN)
		self.assertEqual(LinkSpeed.from_str('256.0 GT/s PCIe'), LinkSpeed.UNKNOWN)
		self.assertEqual(str(LinkSpeed.UNKNOWN), 'Unknown')

	def test_link_width(self) -> None:
		self.assertEqual(LinkWidth.X1, 1)
		self.assertEqual(str(LinkWidth.X1), 'x1')
		self.assertEqual(LinkWidth.from_str('x1'), LinkWidth.X1)
		self.assertEqual(LinkWidth(1), LinkWidth.X1)

		self.assertEqual(LinkWidth.X2, 2)
		self.assertEqual(str(LinkWidth.X2), 'x2')
		self.assertEqual(LinkWidth.from_str('x2'), LinkWidth.X2)
		self.assertEqual(LinkWidth(2), LinkWidth.X2)

		self.assertEqual(LinkWidth.X4, 4)
		self.assertEqual(str(LinkWidth.X4), 'x4')
		self.assertEqual(LinkWidth.from_str('x4'), LinkWidth.X4)
		self.assertEqual(LinkWidth(4), LinkWidth.X4)

		self.assertEqual(LinkWidth.X8, 8)
		self.assertEqual(str(LinkWidth.X8), 'x8')
		self.assertEqual(LinkWidth.from_str('x8'), LinkWidth.X8)
		self.assertEqual(LinkWidth(8), LinkWidth.X8)

		self.assertEqual(LinkWidth.X12, 12)
		self.assertEqual(str(LinkWidth.X12), 'x12')
		self.assertEqual(LinkWidth.from_str('x12'), LinkWidth.X12)
		self.assertEqual(LinkWidth(12), LinkWidth.X12)

		self.assertEqual(LinkWidth.X16, 16)
		self.assertEqual(str(LinkWidth.X16), 'x16')
		self.assertEqual(LinkWidth.from_str('x16'), LinkWidth.X16)
		self.assertEqual(LinkWidth(16), LinkWidth.X16)

		self.assertEqual(LinkWidth.X32, 32)
		self.assertEqual(str(LinkWidth.X32), 'x32')
		self.assertEqual(LinkWidth.from_str('x32'), LinkWidth.X32)
		self.assertEqual(LinkWidth(32), LinkWidth.X32)

		self.assertEqual(LinkWidth.UNKNOWN, 0)
		self.assertEqual(str(LinkWidth.UNKNOWN), 'Unknown')
		self.assertEqual(LinkWidth.from_str('x128'), LinkWidth.UNKNOWN)
		self.assertEqual(LinkWidth(0), LinkWidth.UNKNOWN)

	def test_pcie_standard(self) -> None:
		self.assertEqual(str(PCIeStandard.PCIE_1), 'v1.1')
		self.assertEqual(str(PCIeStandard.PCIE_2), 'v2.1')
		self.assertEqual(str(PCIeStandard.PCIE_3), 'v3.0')
		self.assertEqual(str(PCIeStandard.PCIE_4), 'v4.0')
		self.assertEqual(str(PCIeStandard.PCIE_5), 'v5.0')
		self.assertEqual(str(PCIeStandard.PCIE_6), 'v6.0')
		self.assertEqual(str(PCIeStandard.PCIE_7), 'v7.0')
