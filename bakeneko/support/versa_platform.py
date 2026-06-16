# SPDX-License-Identifier: BSD-3-Clause

'''
An extension of the Torii Lattice Versa 5G platform for use with the Bakeneko tests and examples
'''

try:
	from torii.hdl.time             import MHz

	from torii_boards.lattice.ecp5  import VersaECP55GPlatform

	# XXX(aki): Replace with Torii resource when torii-hdl/#145 and torii-hdl/!146 are dealt with
	from .resources                 import PCIeBusResources

	# TODO(aki):
	# We likely want to switch from using the `OpenOCD` base programming that the base
	# Versa platform uses for `bmda`, as that now supports the ECP5 in upstream.
	# There is a pending issue with multi-chain flashing still, primarily with SPI Erase
	# that i've not been able to figure out, but once I fix that then we can also do
	# ispCLOCK flashing for the versa to ensure that it's running at the proper speed
	# for the given PCIe gen we want (100MHz for Gen1, 200MHz for Gen2)
	class BakenekoVersa5GPlatform(VersaECP55GPlatform):
		resources = [
			*VersaECP55GPlatform.resources,
			# See: Lattice FPGA-EB-02021-2.4; Figure A.4. SERDES; Pg. 26
			# We only care about DCU0 CH0
			*PCIeBusResources(
				0,
				perst_n = 'A6', refclk_p = 'Y11', refclk_n = 'Y12',
				per0_p = 'Y5', per0_n = 'Y6', pet0_p = 'W4', pet0_n = 'W5',
				refclk_freq = 200 * MHz
			)
		]

except ImportError:
	pass
