# SPDX-License-Identifier: BSD-3-Clause

from construct import Int8ul, Int16ul

from .         import PCIOnlyField, Register, RegisterField, RegisterType, ReservedField

__all__ = ()

VendorID = Register(Int16ul)
''' '''

DeviceID = Register(Int16ul)
''' '''

Command = Register(
	ReservedField(length = 2),
	'BusMasterEn'           / RegisterField(RegisterType.RW, '', default = 0, length = 1),
	'SpecialCycleEn'        / PCIOnlyField(),
	'MemoryWriteInvalidate' / PCIOnlyField(),
	'VGAPaletteSnoop'       / PCIOnlyField(),
	'ParityErrorResp'       / RegisterField(RegisterType.RW, '', default = 0, length = 1),
	'IDSELStepWaitCtrl'     / PCIOnlyField(),
	'SERREnable'            / RegisterField(RegisterType.RW, '', default = 0, length = 1),
	'FastB2BEnabled'        / PCIOnlyField(),
	'InterruptDisabled'     / RegisterField(RegisterType.RW, '', default = 0, length = 1),
	ReservedField(length = 5),
)
'''  '''

Status = Register(
	ReservedField(length = 3),
	'InterruptStatus'     / RegisterField(RegisterType.RO, '', default = 0, length = 1),
	'CapabilityList'      / RegisterField(RegisterType.RO, '', default = 1, length = 1),
	'MHz66Capable'        / PCIOnlyField(),
	'FastB2BCapable'      / PCIOnlyField(),
	'MasterDPE'           / RegisterField(RegisterType.RW1C, '', default = 0, length = 1),
	'DEVSELTiming'        / PCIOnlyField(length = 2),
	'SignaledTargetAbort' / RegisterField(RegisterType.RW1C, '', default = 0, length = 1),
	'ReceivedTargetAbort' / RegisterField(RegisterType.RW1C, '', default = 0, length = 1),
	'ReceivedMasterAbort' / RegisterField(RegisterType.RW1C, '', default = 0, length = 1),
	'SignaledSystemError' / RegisterField(RegisterType.RW1C, '', default = 0, length = 1),
	'DetectedParityError' / RegisterField(RegisterType.RW1C, '', default = 0, length = 1)
)
''' '''

RevisionID = Register(Int8ul)
''' '''

ClassCode  = Register(Int8ul)
''' '''

CacheLineSize = Register(Int16ul)
''' '''

LatencyTimer = Register('' / PCIOnlyField(length = 8))
''' '''

HeaderType = Register(Int8ul)
''' '''

BIST = Register(Int8ul)
''' '''

CapabilitiesPointer = Register(Int8ul)
''' '''

InterruptLine = Register(Int8ul)
''' '''

InterruptPin = Register(Int8ul)
''' '''
