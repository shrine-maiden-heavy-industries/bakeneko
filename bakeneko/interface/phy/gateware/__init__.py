# SPDX-License-Identifier: BSD-3-Clause

'''
Gateware PCIe PHY that exposes a PIPE interface for Bakeneko.

Note
----

This PHY is not really viable for anything than running a **really** slow PCIe link if it is
absolutely needed, or for end-to-end testing where you need to test gateware that has a PCIe
interface, and as such can't use a SerDes based PHY.

You *might* be able to harden this gateware into an ASIC macrocell, but there is no good reason
to do so.

'''

from .phy import GatewarePhy

__all__ = (
	'GatewarePhy',
)
