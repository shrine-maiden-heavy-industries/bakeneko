# SPDX-License-Identifier: BSD-3-Clause

from argparse                        import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib                         import Path

from torii.hdl                       import Elaboratable, Module

from bakeneko.support.versa_platform import BakenekoVersa5GPlatform

class BakenekoExample(Elaboratable):
	def __init__(self) -> None:
		pass

	def elaborate(self, platform: BakenekoVersa5GPlatform) -> Module:
		m = Module()

		pcie_x1 = platform.request('pcie_x1')

		return m

def main() -> int:
	build_dir = Path.cwd() / 'build'

	parser = ArgumentParser(
		prog            = __name__,
		description     = 'Bakeneko example for Lattice Versa5G development boards',
		formatter_class = ArgumentDefaultsHelpFormatter
	)

	parser.add_argument(
		'--program', '-p',
		action  = 'set_true',
		default = False,
		help    = 'Program the attached Lattice Versa5G board'
	)

	parser.add_argument(
		'--verbose', '-v',
		action  = 'set_true',
		default = False,
		help    = 'Enable verbose output during build'
	)

	args = parser.parse_args()

	platform = BakenekoVersa5GPlatform()
	example  = BakenekoExample()

	platform.build(
		example,
		name              = 'bakeneko_example',
		build_dir         = str(build_dir),
		do_program        = args.program,
		debug_verilog     = True,
		synth_opts        = ['-abc9' ],
		script_after_read = 'scratchpad -copy abc9.script.flow3 abc9.script\n',
		ecppack_opts      = [ '--compress' ],
		nextpnr_opts      = [ '--write', f'{build_dir}/bakeneko_example.out.json'],
		verbose           = args.program,
	)

	return 0

if __name__ == '__main__':
	raise SystemExit(main())
