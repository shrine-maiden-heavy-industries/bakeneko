#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
import sys
import logging    as log
from pathlib      import Path
from argparse     import ArgumentParser, ArgumentDefaultsHelpFormatter
from os           import getenv
from rich.logging import RichHandler

try:
	from bakeneko.support.sys_dev import PCIDevice, LinkStatus, LinkCapabilities
	from bakeneko.types.constants import LinkSpeed, LinkWidth
except ImportError:
	# Resolve $SRC_ROOT/contrib/scripts/../../
	BAKENEKO_PATH = Path(__file__).resolve().parent.parent.parent

	# Check to make sure we have the Bakeneko package dir
	if (BAKENEKO_PATH / 'bakeneko').is_dir():
		sys.path.append(str(BAKENEKO_PATH))

	# Second verse, same as the first
	from bakeneko.support.sys_dev import PCIDevice, LinkStatus, LinkCapabilities
	from bakeneko.types.constants import LinkSpeed, LinkWidth
try:
	from fabric import Connection
	_remote_connection: Connection | None = None
	HAS_FABRIC = True
except ImportError:
	_remote_connection: None = None
	HAS_FABRIC = False


def _setup_logging():
	log.basicConfig(
		force    = True,
		format   = '%(message)s',
		datefmt  = '[%X]',
		level    = log.INFO,
		handlers = [
			RichHandler(rich_tracebacks = True, show_path = False)
		]
	)

def _setup_args() -> ArgumentParser:
	parser = ArgumentParser(
		prog            = Path(__file__).name,
		description     = 'Bakeneko PCIe device utility',
		formatter_class = ArgumentDefaultsHelpFormatter
	)

	parser.add_argument(
		'--verbose', '-v',
		action = 'store_true',
		help   = 'Enable verbose/debug logging'
	)

	parser.add_argument(
		'--device', '-d',
		help     = 'The PCIe Device to interact with',
	)

	if HAS_FABRIC:
		parser.add_argument(
			'--host', '-H',
			type    = str,
			default = getenv('BAKENEKO_REMOTE_TEST_HOST'),
			help    = 'The remote host to connect to. (Uses $BAKENEKO_REMOTE_TEST_HOST as default)'
		)

		parser.add_argument(
			'--user', '-u',
			type    = str,
			default = getenv('BAKENEKO_REMOTE_TEST_USER'),
			help    = 'The remote user to connect as. (Uses $BAKENEKO_REMOTE_TEST_USER as default)'
		)

		parser.add_argument(
			'--key', '-k',
			type    = Path,
			default = getenv('BAKENEKO_REMOTE_TEST_KEY'),
			help    = 'The SSH key to use for authentication. (Uses $BAKENEKO_REMOTE_TEST_KEY as default)'
		)


	verb_parsers = parser.add_subparsers(
		dest = 'verb', required = True
	)

	verb_parsers.add_parser(
		'list'     , description = 'Enumerate and list all PCI(e) devices'
	).add_argument('--detailed', '-D', action = 'store_true', help = 'Display detailed information.')
	verb_parsers.add_parser(
		'info'     , description = 'Dump device information'
	).add_argument('--detailed', '-D', action = 'store_true', help = 'Display detailed information.')
	verb_parsers.add_parser('get-speed', description = 'Get the current link speed')
	verb_parsers.add_parser(
		'set-speed', description = 'Set the link speed for the device'
	).add_argument('speed', type = int)
	verb_parsers.add_parser('reset'    , description = 'Reset the device')
	verb_parsers.add_parser('re-enum'  , description = 'Try to force device re-enumerations')

	return parser


def _setup_connection(args):
	# No remote bits were specified
	if not all((args.user, args.host, args.key)):
		return

	global _remote_connection
	if HAS_FABRIC and _remote_connection is None:
		_remote_connection = Connection(
			args.host, args.user, connect_kwargs = {
				'key_filename': str(args.key)
			}
		)

def _get_device(args) -> PCIDevice | None:
	if _remote_connection is not None:
		dev = PCIDevice.get_remote(args.device, _remote_connection)
	else:
		dev = PCIDevice.get(args.device)

	if dev is None:
		log.error(f'Invalid PCIe device {args.device}')

	return dev

def _get_devices() -> list[PCIDevice]:
	if _remote_connection is not None:
		return PCIDevice.enumerate_remote(_remote_connection)
	return PCIDevice.enumerate()

def _print_link_status(ls: LinkStatus) -> None:
	log.info(f'   => Speed:            {ls.link_speed}')
	log.info(f'   => Width:            {ls.link_width}')
	log.info(f'   => Is Training:      {ls.link_training}')
	log.info(f'   => Using Slot Clock: {ls.slot_clock}')
	log.info(f'   => DLL Active:       {ls.dll_active}')

def _print_link_capabilities(lc: LinkCapabilities) -> None:
	log.info(f'   => Max Speed:          {lc.max_speed}')
	log.info(f'   => Max Width:          {lc.max_width}')
	log.info(f'   => Port Number:        {lc.port_number}')
	log.info(f'   => Active State PM:    {lc.active_state_pm}')
	log.info(f'   => L0S Exit Latency:   {lc.l0s_exit_latency}')
	log.info(f'   => L1 Exit Latency:    {lc.l1_exit_latency}')
	log.info(f'   => SPDE Reporting:     {lc.spde_reporting}')
	log.info(f'   => DLLA Reporting:     {lc.dlla_reporting}')
	log.info(f'   => LBWN Reporting:     {lc.lbwn_reporting}')
	log.info(f'   => ASPM Opt Complaint: {lc.aspmop_compliant}')


def _print_info(dev: PCIDevice, args) -> None:
	log.info(str(dev))
	if args.detailed:
		if (link_cap := dev.link_capabilities) is not None:
			log.info(' => Link Capabilities:')
			_print_link_capabilities(link_cap)
		if (link_status := dev.link_status) is not None:
			log.info(' => Link Status:')
			_print_link_status(link_status)
	else:
		if (max_speed := dev.max_speed) != LinkSpeed.UNKNOWN:
			log.info(f' => Max Link Speed: {max_speed}')
		if (max_width := dev.max_width) != LinkWidth.UNKNOWN:
			log.info(f' => Max Link Width: {max_width}')
		if (curr_speed := dev.link_speed) != LinkSpeed.UNKNOWN:
			log.info(f' => Current Speed: {curr_speed}')
		if (curr_width := dev.link_width) != LinkWidth.UNKNOWN:
			log.info(f' => Current Width: {curr_width}')

def main() -> int:
	_setup_logging()

	parser = _setup_args()

	args = parser.parse_args()

	if args.verbose:
		log.getLogger().setLevel(log.DEBUG)

	# Set up the remote connection if we are doing so
	_setup_connection(args)

	match args.verb:
		case 'get-speed':
			if (dev := _get_device(args)) is not None:
				print(f'Current device speed: {dev.link_speed}')
			else:
				return 1
		case 'set-speed':
			if (dev := _get_device(args)) is not None:
				requested_speed: int = args.speed

				if requested_speed > dev.max_speed:
					log.error(f'Device supports a maximum speed of {dev.max_speed}')
					return 1

				if not dev.set_speed(LinkSpeed(requested_speed)):
					return 1
			else:
				return 1
		case 'reset':
			if (dev := _get_device(args)) is not None:
				dev.reset()
			else:
				return 1
		case 'info':
			if (dev := _get_device(args)) is not None:
				_print_info(dev, args)
			else:
				return 1
		case 're-enum':
			if (dev := _get_device(args)) is not None:
				if not dev.recycle():
					return 1
			else:
				return 1
		case 'list':
			for dev in _get_devices():
				_print_info(dev, args)

	return 0

if __name__ == '__main__':
	raise SystemExit(main())
