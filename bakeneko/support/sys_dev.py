# SPDX-License-Identifier: BSD-3-Clause

'''
A PCIe device wrapper for Linux PCIe devices.
'''

import logging  as log
from pathlib    import Path
from subprocess import run, PIPE
from functools  import cached_property

try:
	from fabric import Connection
	HAS_FABRIC = True
except ImportError:
	HAS_FABRIC = False

from ..types.constants import LinkSpeed, LinkWidth

SYS_PCI_PATH   = Path('/sys/bus/pci')
PCI_DEVS_PATH  = SYS_PCI_PATH / 'devices'
SYS_PCI_RESCAN = SYS_PCI_PATH / 'rescan'


__all__ = (
	'PCIDevice',
	'LinkStatus',
	'LinkCapabilities',
)

# TODO(aki): Replace once the proper PCIe register infra is set up
class LinkStatus:

	def __init__(self, value: int) -> None:
		self.value = value

		self.link_speed    = (value & 0b0000000000001111)
		self.link_width    = (value & 0b0000001111110000) >> 4
		self.link_training = bool((value & 0b0000100000000000) >> 11)
		self.slot_clock    = bool((value & 0b0001000000000000) >> 12)
		self.dll_active    = bool((value & 0b0010000000000000) >> 13)
		self._rsvd         = (value & 0b1100000000000000) >> 14

	def __repr__(self) -> str:
		return (
			'<LinkStatus '
			f'speed={self.link_speed} width={self.link_width} '
			f'training={self.link_training} slot_clock={self.slot_clock} '
			f'dll={self.dll_active}'
			'>'
		)

	def width(self) -> LinkWidth:
		return LinkWidth(self.link_width)

	def speed(self) -> LinkSpeed:
		return LinkSpeed(self.link_speed)

# TODO(aki): Same as above
class LinkCapabilities:

	def __init__(self, value: int) -> None:
		self.value = value

		self.max_speed        = (value & 0b00000000000000000000000000001111)
		self.max_width        = (value & 0b00000000000000000000001111110000) >> 4
		self.active_state_pm  = (value & 0b00000000000000000000110000000000) >> 10
		self.l0s_exit_latency = (value & 0b00000000000000000111000000000000) >> 12
		self.l1_exit_latency  = (value & 0b00000000000000111000000000000000) >> 15
		self.clock_pm         = bool((value & 0b00000000000001000000000000000000) >> 18)
		self.spde_reporting   = bool((value & 0b00000000000010000000000000000000) >> 19)
		self.dlla_reporting   = bool((value & 0b00000000000100000000000000000000) >> 20)
		self.lbwn_reporting   = bool((value & 0b00000000001000000000000000000000) >> 21)
		self.aspmop_compliant = bool((value & 0b00000000010000000000000000000000) >> 22)
		self._rsvd            = (value & 0b00000000100000000000000000000000) >> 23
		self.port_number      = (value & 0b11111111000000000000000000000000) >> 24

	def __repr__(self) -> str:
		return (
			'<LinkCapabilities '
			f'port_number={self.port_number} max_speed={self.max_speed} max_width={self.max_width} '
			f'l0s={self.l0s_exit_latency} l1={self.l1_exit_latency} clock_pm={self.clock_pm} '
			'>'
		)

	def width(self) -> LinkWidth:
		return LinkWidth(self.max_width)

	def speed(self) -> LinkSpeed:
		return LinkSpeed(self.max_speed)

class PCIDevice:
	'''
	A simple abstraction around PCI(e) devices on Linux.

	Attributes
	----------
	slot : str
		The device slot.

	node : Path
		The full sys path to the device node

	vendor : int
		Device Vendor ID

	device : int
		Device ID

	Parameters
	----------
	slot : str
		Device Slot
	vendor : int
		Vendor ID
	device : int
		Device ID
	'''

	@staticmethod
	def enumerate() -> list['PCIDevice']:
		'''
		Get a list of PCI(e) devices attached to the system

		Returns
		-------
		list[PCIDevice]
			All found PCI(e) devices
		'''
		devs: list[PCIDevice] = list()
		for d in PCI_DEVS_PATH.iterdir():
			devs.append(PCIDevice.from_path(d))
		return devs

	@staticmethod
	def get(slot: str) -> 'PCIDevice | None':
		'''
		Get a PCIDevice from the give device/slot IDs.

		Parameters
		----------
		slot : str
			The slot ID to use

		Returns
		-------
		PCIDevice
			The PCI(e) device, if found.
		None
			Otherwise
		'''
		# If we don't start with the appropriate prefix, prepend it
		if not slot.startswith('0000:'):
			slot = f'0000:{slot}'

		# We should be at `/sys/bus/pci/devices/0000:XX:YY.Z`
		DEV_PATH = PCI_DEVS_PATH / slot
		# If we don't exist, bail
		if not DEV_PATH.exists():
			return None

		# We do, yay
		return PCIDevice.from_path(DEV_PATH)

	@staticmethod
	def from_path(path: Path) -> 'PCIDevice':
		'''
		Construct a PCIDevice from a device node path

		Parameters
		----------
		path : Path
			The device node path in the `/sys/bus/pci/devices` tree.

		Returns
		-------
		PCIDevice
			A new PCI(e) device wrapper
		'''

		with (path / 'uevent').open('r') as f:
			info = dict(map(lambda s: s.strip().split('='), f.readlines()))
		vendor, device = info['PCI_ID'].split(':')
		slot = info['PCI_SLOT_NAME']

		return PCIDevice(slot, vendor, device)

	# All our remote device helpers and APIs
	if HAS_FABRIC:

		_remote_connection: Connection | None

		@staticmethod
		def enumerate_remote(conn: Connection) -> list['PCIDevice']:
			'''
			Get a list of PCI(e) devices attached to the remote system

			Parameters
			----------
			conn : fabric.Connection
				The connection to use.

			Returns
			-------
			list[PCIDevice]
				All found PCI(e) devices
			'''

			devs: list[PCIDevice] = list()

			# Due to interacting over a remote pipe, we need to invoke some shell gubbins
			# and do string parsing.

			res = conn.run(f'ls {PCI_DEVS_PATH!s}', hide = True)
			if not res.ok:
				return devs

			for d in res.stdout.split():
				devs.append(PCIDevice.from_remote_path(
					PCI_DEVS_PATH / d, conn
				))

			return devs

		@staticmethod
		def get_remote(slot: str, conn: Connection) -> 'PCIDevice | None':
			'''
			Get a PCIDevice from the give device/slot ID on the remote system.

			Parameters
			----------
			slot : str
				The slot ID to get.

			conn : fabric.Connection
				The connection to use.

			Returns
			-------
			PCIDevice
				The PCI(e) device, if found.
			None
				Otherwise
			'''
			# If we don't start with the appropriate prefix, prepend it
			if not slot.startswith('0000:'):
				slot = f'0000:{slot}'

			# We should be at `/sys/bus/pci/devices/0000:XX:YY.Z`
			DEV_PATH = PCI_DEVS_PATH / slot

			# Check if device node exists
			res = conn.run(f'[ -e {DEV_PATH!s} ]', hide = True)
			if not res.ok:
				return None

			# We do, yay
			return PCIDevice.from_remote_path(DEV_PATH, conn)

		@staticmethod
		def from_remote_path(path: Path, conn: Connection) -> 'PCIDevice':
			'''
			Construct a PCIDevice from a device node path

			Parameters
			----------
			path : Path
				The device node path in the `/sys/bus/pci/devices` tree.

			conn : fabric.Connection
				The connection to use.

			Returns
			-------
			PCIDevice
				A new PCI(e) device wrapper
			'''

			res = conn.run(f'cat {path / "uevent"!s}', hide = True)
			info = dict(map(lambda s: s.strip().split('='), res.stdout.split()))

			vendor, device = info['PCI_ID'].split(':')
			slot = info['PCI_SLOT_NAME']

			dev = PCIDevice(slot, vendor, device)
			dev._remote_connection = conn
			dev._post_setup()
			return dev

		def _remote_run(self, cmd: str, warn: bool = True, hide: bool = True):
			log.debug(f' ==> \'{cmd}\'')
			res = self._remote_connection.run(cmd, warn = warn, hide = hide)
			log.debug(f' <== {res}')

			return res

		def _remote_path_exists(self, path: Path) -> bool:
			res = self._remote_run(f'[ -e {path!s} ]')
			return res.ok

		def _remote_run_exists(self, path: Path, cmd: str):
			res = self._remote_run(f'[ -e {path!s} ] && {cmd}')
			return res

		def _get_capability_remote(self, cap: str, port: bool) -> str | None:
			target = self.port if port else self.slot
			res = self._remote_run(f'setpci -s {target} {cap}')
			if res.ok:
				return res.stdout.strip()
			log.debug(f'Get capability failed: {res.stderr.strip()}')
			return None

		def _max_speed_remote(self) -> str:
			res = self._remote_run_exists(self._max_ls, f'cat {self._max_ls!s}')
			if res.ok:
				return res.stdout.strip()
			return 'Unknown'

		def _max_width_remote(self) -> str:
			res = self._remote_run_exists(self._max_lw, f'cat {self._max_lw!r}')
			if res.ok:
				return res.stdout.strip()
			return 'Unknown'

		def _recycle_remote(self) -> bool:
			log.info('Removing this device')
			self._remote_run_exists(self._remove, f'echo 1 > {self._remove!s}')

			log.info('Re-scanning bus...')
			self._remote_run_exists(SYS_PCI_RESCAN, f'echo 1 > {SYS_PCI_RESCAN!s}')

			log.info('Checking to ensure we\'re a valid device again')
			if not self._remote_path_exists(self.node):
				log.error('Device didn\'t come back!')
				return False
			log.info('Looks like we\'re back, happy days')
			return True

		def _reset_remote(self) -> None:
			self._remote_run_exists(self._reset, f'echo 1 > {self._reset!s}')

		def _repr_remote(self) -> str:
			return (
				'<PCIDevice[Remote] '
				f'slot={self.slot} port={self.port} vendor={self.vendor} device={self.device} '
				f'host={self._remote_connection.host}'
				'>'
			)

		def _readlink_remote(self, path: Path) -> Path:
			res = self._remote_run(f'readlink {path!s}')
			if not res.ok:
				return path

			link_path = Path(res.stdout.strip())
			if link_path.is_relative_to(path):
				return (path / link_path)
			return link_path

	else:
		# Stub for remote type stuff
		_remote_connection: None

	def _get_capability_local(self, cap: str, port: bool) -> str | None:
		target = self.port if port else self.slot
		cmd = ['setpci', '-s', target, cap]
		log.debug(f'Running \'{" ".join(cmd)}\'')
		res = run(cmd, stdout = PIPE, stderr = PIPE)
		if res.returncode == 0:
			return res.stdout.decode()
		log.debug(f'Get capability failed: {res.stderr.decode()}')
		return None

	def _max_speed_local(self) -> str:
		with self._max_ls.open('r') as f:
			return f.readline().strip()

	def _max_width_local(self) -> str:
		with self._max_lw.open('r') as f:
			return f.readline().strip()

	def _recycle_local(self) -> bool:
		log.info('Removing this device')
		with self._remove.open('w') as f:
			f.write('1')

		log.info('Re-scanning bus...')
		with SYS_PCI_RESCAN.open('w') as f:
			f.write('1')

		log.info('Checking to ensure we\'re a valid device again')
		if not self.node.exists():
			log.error('Device didn\'t come back!')
			return False

		log.info('Looks like we\'re back, happy days')
		return True

	def _reset_local(self) -> None:
		with self._reset.open('w') as f:
			f.write('1')

	def _repr_local(self) -> str:
		return f'<PCIDevice slot={self.slot} port={self.port} vendor={self.vendor} device={self.device}>'

	def _readlink_local(self, path: Path) -> Path:
		return path.readlink()

	def _populate_paths(self) -> None:
		''' Setup the various device node paths we need '''

		self._remove = self.node / 'remove'
		self._reset  = self.node / 'reset'
		self._max_ls = self.node / 'max_link_speed'
		self._max_lw = self.node / 'max_link_width'
		self.port    = self._impl_readlink(self.node).parent.name

	def _setup_shims(self) -> None:
		''' Set up the internal shim calls used to dispatch to remote or local '''

		if self._remote_connection is None:
			# Local Shims
			self._impl_get_capability = self._get_capability_local
			self._impl_max_speed      = self._max_speed_local
			self._impl_max_width      = self._max_width_local
			self._impl_recycle        = self._recycle_local
			self._impl_reset          = self._reset_local
			self._impl_repr           = self._repr_local
			self._impl_readlink       = self._readlink_local
		else:
			# Remote Shims
			self._impl_get_capability = self._get_capability_remote
			self._impl_max_speed      = self._max_speed_remote
			self._impl_max_width      = self._max_width_remote
			self._impl_recycle        = self._recycle_remote
			self._impl_reset          = self._reset_remote
			self._impl_repr           = self._repr_remote
			self._impl_readlink       = self._readlink_remote

	def _use_port(self) -> bool | None:
		''' In some cases we need to address the port, not the device '''

		cap = self.get_capability('CAP_EXP+02.W')
		if cap is None:
			return None

		# Get the port type
		pt = (int(cap, base = 16) & 0xF0 >> 4)

		# If it's a PCIe Endpoint, PCI Endpoint, or Upstream Port of a PCIe switch, then yes
		if pt in (0, 1, 5):
			return True

		# Otherwise we should be fine
		return False

	def _clear_cached_props(self) -> None:
		''' Flush cached properties '''

		try:
			del self.link_status
			del self.link_capabilities
			del self.max_speed
			del self.max_width
			del self.link_speed
			del self.link_width
		except Exception:
			pass

	def _get_link_status(self) -> LinkStatus | None:
		''' Extract the Link Status register '''

		use_port = self._use_port()
		if use_port is None:
			return None

		if (link_status := self.get_capability('CAP_EXP+12.W', use_port)) is not None:
			return LinkStatus(int(link_status, base = 16))
		return None

	def _get_link_capabilities(self) -> LinkCapabilities | None:
		''' Extract the Link Capabilities 1 register '''

		use_port = self._use_port()
		if use_port is None:
			return None

		if (link_cap := self.get_capability('CAP_EXP+0c.L', use_port)) is not None:
			return LinkCapabilities(int(link_cap, base = 16))
		return None

	def _post_setup(self) -> None:
		''' This must be done **after** construction due to how we wiggle things '''
		self._setup_shims()
		self._populate_paths()

	def __init__(self, slot: str, vendor: int | str, device: int | str):
		self._remote_connection = None
		self.slot = slot
		self.node = PCI_DEVS_PATH / slot
		self.vendor = vendor
		self.device = device

	def set_speed(self, speed: LinkSpeed) -> bool:
		'''
		Set the device link speed.

		Note
		----
		This only works on PCIe gen2 or newer devices, as the LC2 register is not specified in PCIe v1
		which makes sense, as in PCIe v1 there was only one speed.

		Parameters
		----------
		speed : LinkSpeed
			The target device speed

		Returns
		-------
		bool
			True if speed was able to be set and `get_speed` reads it back, otherwise False
		'''

		use_port = self._use_port()
		if use_port is None:
			return False

		if (link_control2 := self.get_capability('CAP_EXP+30.W')) is not None:
			log.info(f'Setting link speed to {speed}')

			if speed > self.max_speed:
				log.warning(f'Requested link speed of {speed} is faster than maximum speed {self.max_speed}, clamping.')
				speed = self.max_speed

			lc2 = int(link_control2, base = 16)

			# BUG(aki): So, /technically/ we should check the Link Capabilities 2 Register
			#           and then match `speed` to if the bit in the speed vector is set, if
			#           so, then we can set this to the number of that bit.
			#
			#           HOWEVER, all the speeds are in-order (2.5/5/8/16/32/64), so rather than
			#           2 bugs here, we only really have one, but the check above if the speed we
			#           are setting is over the max link speed and then clamping means we *really*
			#           0 bugs:tm: but only in a really roundabout way.
			#
			#           However #2, we still have one potential bug, and that is relying that the
			#           int casting of LinkSpeed will always result in the proper value, I mean it
			#           **should** but it would be better to be 100% sure.

			# Mask of the existing values for the register and
			lc2 = (lc2 & 0xFFF0) | int(speed)

			# Set the new value
			self.get_capability(f'CAP_EXP+30.W={lc2:04x}', use_port)

			# We set a new speed, so we need to kick of link training to make sure it takes
			return self.retrain_link()
		else:
			log.warning('Unable to re-train link, can\'t access Link Control 2 Register')
			return False

	def get_capability(self, cap: str, port: bool = False) -> str | None:
		'''
		Use `setpci` to read a PCI device register and return the value.

		Parameters
		----------
		cap : str
			The `setpci` capability/register to read.

		port : bool
			If this capability request is direct at the port, rather than the slot. (default: False)

		Returns
		-------
		str
			The result from the `setpci -s` call on success.
		None
			Otherwise None
		'''

		log.debug(f'Getting device capability \'{cap}\' (targeting port? {port})')
		return self._impl_get_capability(cap, port)

	def retrain_link(self) -> bool:
		''' Try to force the device to re-train the link '''

		use_port = self._use_port()
		if use_port is None:
			return False

		# FIXME(aki): This, like much of the other register access is just hacked together
		#             It should really be fixed when we get proper register definitions written.

		if (link_control := self.get_capability('CAP_EXP+10.W')) is not None:
			log.info('Attempting to force link re-training...')

			lc = int(link_control, base = 16)

			# Set the `Retrain Link` bit (#5)
			lc |= 0x20

			# Write the new value back to the register
			self.get_capability(f'CAP_EXP+10.W={lc:04x}', use_port)

			# We did link re-training so things are different now, maybe
			self._clear_cached_props()
		else:
			log.warning('Unable to re-train link, can\'t access Link Control Register')
			return False
		return True

	@cached_property
	def link_status(self) -> LinkStatus | None:
		''' Get the link status '''

		return self._get_link_status()

	@cached_property
	def link_capabilities(self) -> LinkCapabilities | None:
		''' Get the link capabilities '''

		return self._get_link_capabilities()

	@cached_property
	def max_speed(self) -> LinkSpeed:
		''' Get the maximum link speed this PCIe device supports. '''

		if (lc := self.link_capabilities) is not None:
			return lc.speed()
		return LinkSpeed.from_str(self._impl_max_speed())

	@cached_property
	def max_width(self) -> LinkWidth:
		''' Get the maximum link width this PCIe device supports. '''

		if (lc := self.link_capabilities) is not None:
			return lc.width()
		return LinkWidth.from_str(self._impl_max_width())

	@cached_property
	def link_speed(self) -> LinkSpeed:
		''' Speed of the currently active PCIe link for this device. '''

		if (ls := self.link_status) is not None:
			return ls.speed()
		return LinkSpeed.UNKNOWN

	@cached_property
	def link_width(self) -> LinkWidth:
		''' Width of the currently active PCIe link for this device. '''

		if (ls := self.link_status) is not None:
			return ls.width()
		return LinkWidth.UNKNOWN

	def recycle(self) -> bool:
		'''
		Remove this PCI(e) device, and then force a bus re-scan to try to bring it back.

		Returns
		-------
		bool
			True if the device came back after a re-scan, otherwise False
		'''

		res = self._impl_recycle()
		self._clear_cached_props()
		return res

	def reset(self) -> None:
		''' Soft-reset this device '''

		log.info('Resetting this device')
		self._impl_reset()
		self._clear_cached_props()

	def __repr__(self) -> str:
		return self._impl_repr()
