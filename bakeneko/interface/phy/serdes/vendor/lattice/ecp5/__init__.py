# SPDX-License-Identifier: BSD-3-Clause

'''
Lattice Semiconductor ECP5/ECP5-5G SerDes Interfaces
'''

from .dcu  import DCU
from .pipe import ECP5SerDesPIPE
from .sci  import SCI, CHRegister, DCURegister

__all__ = (
	'DCU',
	'ECP5SerDesPIPE',
	'SCI',
	'CHRegister',
	'DCURegister',
)
