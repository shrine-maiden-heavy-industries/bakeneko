# SPDX-License-Identifier: BSD-3-Clause

from unittest                 import TestCase

from bakeneko.types.constants import LinkSpeed, LinkWidth, PCIeStandard
from bakeneko.types.errors    import (
	PCIeGatewareError, PCIeUnsupportedLinkSpeed, PCIeUnsupportedLinkWidth, PCIeUnsupportedConfiguration
)

class BakenekoTypesErrorsTest(TestCase):

	def test_unsupported_link_speed(self) -> None:
		REQUESTED = LinkSpeed.LS16_0
		SUPPORTED = (LinkSpeed.LS2_5, LinkSpeed.LS5_0, LinkSpeed.LS8_0)
		EXCEPTION = PCIeUnsupportedLinkSpeed(REQUESTED, SUPPORTED)

		with self.assertRaisesRegex(
			PCIeUnsupportedLinkSpeed,
			r'^The link speed of 16 GT/s is not supported, only the following: 2\.5 GT/s, 5 GT/s, 8 GT/s.$'
		):
			try:
				raise EXCEPTION
			except Exception as e:
				self.assertIsInstance(e, PCIeGatewareError)
				self.assertIsInstance(e, PCIeUnsupportedLinkSpeed)
				self.assertEqual(e.requested_speed,  REQUESTED)
				self.assertEqual(e.supported_speeds, SUPPORTED)
				raise e


	def test_unsupported_link_width(self) -> None:
		REQUESTED = LinkWidth.X8
		SUPPORTED = (LinkWidth.X1, LinkWidth.X2, LinkWidth.X4)
		EXCEPTION = PCIeUnsupportedLinkWidth(REQUESTED, SUPPORTED)

		with self.assertRaisesRegex(
			PCIeUnsupportedLinkWidth,
			r'^The link width of x8 is not supported, only the following: x1, x2, x4.$'
		):
			try:
				raise EXCEPTION
			except Exception as e:
				self.assertIsInstance(e, PCIeGatewareError)
				self.assertIsInstance(e, PCIeUnsupportedLinkWidth)
				self.assertEqual(e.requested_width,  REQUESTED)
				self.assertEqual(e.supported_widths, SUPPORTED)
				raise e

	def test_unsupported_configuration(self) -> None:
		EXCEPTION = PCIeUnsupportedConfiguration(PCIeStandard.PCIE_2, LinkSpeed.LS64_0, LinkWidth.X12)

		with self.assertRaisesRegex(
			PCIeUnsupportedConfiguration,
			r'^PCIe standard v2\.1 with link speed of 64 GT/s and link width of x12 is an unsupported configuration.$'
		):
			try:
				raise EXCEPTION
			except Exception as e:
				self.assertIsInstance(e, PCIeGatewareError)
				self.assertIsInstance(e, PCIeUnsupportedConfiguration)
				self.assertEqual(e.pcie_standard, PCIeStandard.PCIE_2)
				self.assertEqual(e.link_speed,    LinkSpeed.LS64_0)
				self.assertEqual(e.link_width,    LinkWidth.X12)
				raise e
