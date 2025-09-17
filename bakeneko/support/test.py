# SPDX-License-Identifier: BSD-3-Clause

'''
Helpers and utilities for various Bakeneko tests
'''

from inspect  import isfunction
from os       import getenv
from platform import system
from pathlib  import Path
from typing   import Any, cast
from unittest import TestCase, skip
from io       import IOBase

# Remote Test control
try:
	from fabric import Connection
	HAS_FABRIC = True
except ImportError:
	HAS_FABRIC = False

# DUT Test Communication
try:
	from serial import Serial
	HAS_PYSERIAL = True
except ImportError:
	HAS_PYSERIAL = False

from torii.test import ToriiTestCase

IN_CI       = getenv('GITHUB_WORKSPACE') is not None
SKIP_REMOTE = getenv('BAKENEKO_SKIP_TESTS_REMOTE') is not None
SKIP_SERIAL = getenv('BAKENEKO_SKIP_TESTS_SERIAL') is not None
IS_LINUX    = system() == 'Linux'

# Only allow remote tests if we have fabric, are not in CI, on Linux, and not explicitly skipping them
ALLOW_REMOTE_TESTS = all((HAS_FABRIC, IS_LINUX, not IN_CI, not SKIP_REMOTE))
# Only allow serial tests if we have pyserial, are not in CI, on linux, and not explicitly skipping them
ALLOW_SERIAL_TESTS = all((HAS_PYSERIAL, IS_LINUX, not IN_CI, not SKIP_SERIAL))

__all__ = (
	'BakenekoRemoteTestCase',
	'BakenekoSerialTestCase',
	'PCIeGatewareTestCase'
)

class BakenekoRemoteTestMeta(type):
	'''
	This metaclass is used to automatically annotate all tests within a :py:class:`BakenekoRemotelTest`
	test class with :py:meth:`unitest.skip` if we don't have remote test support capabilities.

	The check's are currently as follows:
		* We are not running in CI. (checks the existence of the ``GITHUB_WORKSPACE`` env var)
		* We can import :py:mod:`fabric` for talking to the remote host.
		* The ``BAKENEKO_SKIP_TESTS_REMOTE`` environment variable is not set.
		* We are running on Linux.

	If any of the above checks fail, all remote tests are disabled.

	'''

	def __new__(
		cls: type[type], name: str, bases: tuple[type, ...], namespace: dict[str, Any]
	) -> 'BakenekoRemoteTestMeta':
		for attr, val in namespace.items():
			if isfunction(val):
				if not ALLOW_REMOTE_TESTS and val.__name__.startswith('test_'):
					namespace[attr] = skip('Remote tests disabled')(val)
		return cast(BakenekoRemoteTestMeta, type.__new__(cls, name, bases, namespace))

class BakenekoSerialTestMeta(type):
	'''
	Like the :py:class:`BakenekoRemoteTestMeta` metaclass, this is used to automatically annotate all
	tests within a :py:class:`BakenekoSerialTest` test class with :py:meth:`unitest.skip` if we don't
	have serial test support capabilities.

	The check's are currently as follows:
		* We are not running in CI. (checks the existence of the ``GITHUB_WORKSPACE`` env var)
		* We can import :py:mod:`serial` for talking to the DUT.
		* The ``BAKENEKO_SKIP_TESTS_SERIAL`` environment variable is not set.
		* We are running on Linux.

	If any of the above checks fail, all serial tests are disabled.

	'''

	def __new__(
		cls: type[type], name: str, bases: tuple[type, ...], namespace: dict[str, Any]
	) -> 'BakenekoSerialTestMeta':
		for attr, val in namespace.items():
			if isfunction(val):
				if not ALLOW_REMOTE_TESTS and val.__name__.startswith('test_'):
					namespace[attr] = skip('Serial tests disabled')(val)
		return cast(BakenekoSerialTestMeta, type.__new__(cls, name, bases, namespace))

class BakenekoRemoteTestCase(TestCase, metaclass = BakenekoRemoteTestMeta):
	'''
	Run :py:mod:`unitest` based test cases that interact with a remote host over SSH.

	Attributes
	----------
	REMOTE_HOST : str | None
		The remote host to connect to. If not overloaded it reads the value from
		the ``BAKENEKO_REMOTE_TEST_HOST`` environment variable if it exists, otherwise
		the value is ``None``.

	REMOTE_USER : str | None
		The user on the remote host to connect as. If not overloaded it reads the
		value from the ``BAKENEKO_REMOTE_TEST_USER`` environment variable if it
		exits, otherwise the value is ``None``.

	REMOTE_KEY : str | None
		The private key file to use for remote authentication. If not overloaded
		it reads the value from the ``BAKENEKO_REMOTE_TEST_KEY`` environment variable
		if it exits, otherwise the value is ``None``.

	LONG_LIVED : bool
		If the remote connection is long-lived. If set to true, the connection will be
		established on construction of the test class and live for every single test case
		run. Otherwise, the connection is established prior to each ``test_`` case and
		torn down after. (default: True)
	'''

	REMOTE_HOST = getenv('BAKENEKO_REMOTE_TEST_HOST')
	REMOTE_USER = getenv('BAKENEKO_REMOTE_TEST_USER')
	REMOTE_KEY  = getenv('BAKENEKO_REMOTE_TEST_KEY' )

	LONG_LIVED  = True

	_remote_connection: 'Connection | None' = None

	def _setup_connection(self) -> bool:
		''' Setup the Fabric SSH connection '''

		if ALLOW_REMOTE_TESTS:
			# NOTE(aki):
			# The `type: ignore` is due to the type checking not being able to see that if we
			# do end up in this branch of the if then `Connection` is not unbound.
			self._remote_connection = Connection( # type: ignore
				self.REMOTE_HOST, self.REMOTE_USER,
				connect_kwargs = {
					'key_filename': self.REMOTE_KEY
				}
			)
			return True
		return False

	def _close_connection(self) -> bool:
		''' Close the Fabric SSH connection '''

		if ALLOW_REMOTE_TESTS and self._remote_connection is not None:
			self._remote_connection.close()
			return True
		return False

	def remote_put_file(self, file: Path | IOBase, dest: str):
		'''
		Send a file to the remote system

		Parameters
		----------
		file : Path | IOBase
			The file to upload.

		dest : str
			The destination for the file.

		Returns
		-------
		fabric.transfer.Result
			If the connection is active and valid, the result of the file transfer.
		None
			If there is no remote connection.

		Raises
		------
		AssertionError
			If the `put` on the remote connection fails for any reason.
		'''

		if self._remote_connection is not None:
			try:
				return self._remote_connection.put(file, dest)
			except Exception as e:
				raise self.failureException(e)

		return None

	def remote_run_cmd(self, cmd: str, **kwargs):
		'''
		Run a command on the remote system.

		Parameters
		----------
		cmd : str
			The command to run on the remote system.

		Returns
		-------
		invoke.runners.Result
			If the connection is active and valid, the result of the command.
		None
			If there is no remote connection.

		Raises
		------
		AssertionError
			If the `run` on the remote connection fails for any reason.
		'''

		if self._remote_connection is not None:
			try:
				return self._remote_connection.run(cmd, **kwargs)
			except Exception as e:
				raise self.failureException(e)
		return None

	def assertRemoteConnected(self):
		''' Assert that we are connected to the remote session '''

		res = self.remote_run_cmd('uname -a')
		if res is None or not res.ok:
			raise self.failureException('Remote connection failed')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		if self.LONG_LIVED:
			self._setup_connection()

	def setUp(self) -> None:
		if not self.LONG_LIVED:
			self._setup_connection()

	def tearDown(self) -> None:
		if not self.LONG_LIVED:
			self._close_connection()

class BakenekoSerialTestCase(TestCase, metaclass = BakenekoSerialTestMeta):
	'''
	Run :py:mod:`unitest` based test cases that interact with a DUT over serial

	Attributes
	----------
	SERIAL_PORT : str | None
		The serial port to connect to. If not overloaded it reads the value from
		the ``BAKENEKO_SERIAL_TEST_PORT`` environment variable if it exists, otherwise
		the value is ``None``.

	REMOTE_USER : int
		The user on the remote host to connect as. If not overloaded it reads the
		value from the ``BAKENEKO_SERIAL_TEST_BAUD`` environment variable if it exists.
		(default: 115200)


	LONG_LIVED : bool
		If the serial connection is long-lived. If set to true, the connection will be
		established on construction of the test class and live for every single test case
		run. Otherwise, the connection is established prior to each ``test_`` case and
		torn down after. (default: True)
	'''

	SERIAL_PORT = getenv('BAKENEKO_SERIAL_TEST_PORT')
	SERIAL_BAUD = int(getenv('BAKENEKO_SERIAL_TEST_BAUD', '115200'))

	LONG_LIVED  = True

	_remote_connection: 'Serial | None' = None

	def _setup_connection(self) -> bool:
		''' Setup the serial connection '''

		if ALLOW_SERIAL_TESTS:
			# NOTE(aki):
			# The `type: ignore` is due to the type checking not being able to see that if we
			# do end up in this branch of the if then `Serial` is not unbound.
			self._remote_connection = Serial( # type: ignore
				port = self.SERIAL_PORT, baudrate = self.SERIAL_BAUD
			)
			return True
		return False

	def _close_connection(self) -> bool:
		''' Close the serial connection '''

		if ALLOW_SERIAL_TESTS and self._remote_connection is not None:
			self._remote_connection.close()
			return True
		return False

	def __init__(self, methodName: str = 'runTest', **kwargs) -> None:
		super().__init__(methodName, **kwargs)

		if self.LONG_LIVED:
			self._setup_connection()

	def setUp(self) -> None:
		'''
		Hook that runs prior to a test running

		Checks the value of :py:attr:`LONG_LIVED`, and if it is not set then
		it sets up the Serial connection to the remote DUT.

		NOTE
		----
		If your test needs specialized setup code and you overload this make sure you call
		`super().setUp()`!
		'''

		if not self.LONG_LIVED:
			self._setup_connection()

	def tearDown(self) -> None:
		'''
		Hook that runs when a test is completed.

		Checks the value of :py:attr:`LONG_LIVED`, and if it is not set then
		it cleans up the Serial connection to the remote DUT.

		NOTE
		----
		If your test needs specialized teardown code and you overload this make sure you call
		`super().tearDown()`!
		'''

		if not self.LONG_LIVED:
			self._close_connection()

class PCIeGatewareTestCase(ToriiTestCase):
	'''
	A specialization of the :py:class:`torii.test.ToriiTestCase` for the Bakeneko PCIe gateware.

	It primarily provides helper asserts for various things related to PCIe traffic and symbols.
	'''

	domains = (*ToriiTestCase.domains, ('pcie', 1e8),)
