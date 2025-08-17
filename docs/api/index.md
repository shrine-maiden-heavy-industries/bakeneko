# API Reference

```{toctree}
:hidden:

interface/index
link/index
physical/index
protocol/index
support/index
types/index
devices/index
```

```{warning}
The Bakeneko API reference is a work in progress and we are actively working on improving it,
however it may be deficient or missing in places.
```

The Bakeneko API is broken up into 7 main parts:

* [`devices`] - Pre-baked PCIe devices for quickly adding PCIe to a gateware project.
* [`interface`] - All the machinery for interfacing with PCIe from an electrical standpoint, including SerDes PHYs and also a pure gateware PHY for simulation and testing.
* [`link`] - All PCIe link management details.
* [`physical`] - Everything to do with the physical aspects such as scrambling and link training.
* [`protocol`] - PCIe protocol level machinery and interfaces.
* [`support`] - Support elements needed for all of the above sections.
* [`types`] - Bakeneko specific types used for the gateware and system API.

[`devices`]: ./devices/index.md
[`interface`]: ./interface/index.md
[`link`]: ./link/index.md
[`physical`]: ./physical/index.md
[`protocol`]: ./protocol/index.md
[`support`]: ./support/index.md
[`types`]: ./types/index.md
