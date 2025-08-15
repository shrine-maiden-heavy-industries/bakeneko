# SPDX-License-Identifier: BSD-3-Clause

from argparse                   import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib                    import Path
from typing                     import TypeAlias

from torii.hdl                  import Elaboratable, Module

from torii_boards.lattice.ecp5  import VersaECP5Platform, VersaECP55GPlatform

from bakeneko.support.resources import PCIeBusResources

VersaPlatform: TypeAlias = VersaECP5Platform | VersaECP55GPlatform

class BakenekoExample(Elaboratable):
	def __init__(self) -> None:
		pass

	def elaborate(self, platform: VersaPlatform) -> Module:
		m = Module()

		return m

def main() -> int:
	build_dir = Path.cwd() / 'build'

	parser = ArgumentParser(
		prog            = __name__,
		description     = 'Bakeneko example for Lattice Versa/Versa5G development boards',
		formatter_class = ArgumentDefaultsHelpFormatter
	)

	parser.add_argument(
		'--platform', '-p',
		choices = ('versa', 'versa5g'),
		default = 'versa5g',
		help    = 'Platform to target'
	)

	args = parser.parse_args()

	platform = VersaECP55GPlatform() if args.platform == 'versa5g' else VersaECP5Platform()

	# Add the DCU resources
	platform.add_resources([
		# See: Lattice FPGA-EB-02021-2.4; Figure A.4. SERDES; Pg. 26
		# We only care about DCU0 CH0
		*PCIeBusResources(
			0,
			perst_n = 'A6', refclk_p = 'Y11', refclk_n = 'Y12',
			pet0_p = 'Y5', pet0_n = 'Y6', per0_p = 'W4', per0_n = 'W5',
		)
	])

	example = BakenekoExample()

	platform.build(
		example,
		name              = 'bakeneko_example',
		build_dir         = str(build_dir),
		do_program        = True,
		debug_verilog     = True,
		synth_opts        = ['-abc9' ],
		script_after_read = 'scratchpad -copy abc9.script.flow3 abc9.script\n',
		ecppack_opts      = [ '--compress' ],
		nextpnr_opts      = [ '--write', f'{build_dir}/bakeneko_example.out.json'],
		verbose           = True,
	)

	return 0


if __name__ == '__main__':
	raise SystemExit(main())
