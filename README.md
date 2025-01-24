<!-- markdownlint-disable MD033 MD010 -->
# Bakeneko

> [!WARNING]
> Bakeneko is in early development, it may not be stable, or even functional at all, use at your own risk.

Bakeneko is a [Torii] gateware library for adding PCIe support to designs.

It does this by abstracting away the hardware [SerDes] blocks of the various [FPGAs] into a
[PIPE] interface, which then the rest of the gateware core is built against.

The lane abstraction also happens behind the PIPE interface boundary, as it is also dependant on implementation details of the given FPGA SerDes blocks.

## Support

The following tables lay out the current and planned support for PCIe standards / Lane Widths.

> [!IMPORTANT]
> Not all combinations of PCIe versions and lane widths are available for every FPGA/SerDes back-end.
> For instance, you can't use PCIe v3 on Lattice [ECP5-5G] parts, and can only do up to x4 lane widths of PCIe v2 on them.

### PCIe Configurations

<table>
	<tbody>
	<tr>
		<td></td>
		<td colspan="9">Link Width</td>
	</tr>
	<tr>
		<td>PCIe Version</td>
		<td>x1</td>
		<td>x2</td>
		<td>x4</td>
		<td>x6*</td>
		<td>x8</td>
		<td>x12*</td>
		<td>x16</td>
		<td>x24*</td>
		<td>x32*</td>
	</tr>
	<tr>
		<td>v1.0/v1.1</td>
		<td>🚧</td>
		<td>📋</td>
		<td>📋</td>
		<td>🚫</td>
		<td>⏳</td>
		<td>🚫</td>
		<td>⏳</td>
		<td>🚫</td>
		<td>🚫</td>
	</tr>
	<tr>
		<td>v2.0/v2.1</td>
		<td>📋</td>
		<td>📋</td>
		<td>📋</td>
		<td>🚫</td>
		<td>⏳</td>
		<td>🚫</td>
		<td>⏳</td>
		<td>🚫</td>
		<td>🚫</td>
	</tr>
	<tr>
		<td>v3.0</td>
		<td>⏳</td>
		<td>⏳</td>
		<td>⏳</td>
		<td>🚫</td>
		<td>⏳</td>
		<td>🚫</td>
		<td>⏳</td>
		<td>🚫</td>
		<td>🚫</td>
	</tr>
	<tr>
		<td>v4.0</td>
		<td>📑</td>
		<td>📑</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>🚫</td>
	</tr>
	<tr>
		<td>v5.0</td>
		<td>📑</td>
		<td>📑</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>🚫</td>
	</tr>
	<tr>
		<td>v6.0</td>
		<td>📑</td>
		<td>📑</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>🚫</td>
	</tr>
	<tr>
		<td>v7.0</td>
		<td>📑</td>
		<td>📑</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>📑</td>
		<td>🚫</td>
		<td>🚫</td>
	</tr>
	</tbody>
</table>

*: Non-standard PCIe link width

### FPGA SerDes

| SerDes Block | Status |
|--------------|:------:|
| Lattice DCU† | 🚧     |
| XC7-GTP      | 📋     |
| XC7-GTX      | 📋     |
| XC7-GTH      | ⏳     |
| XC7-GTZ      | 📑     |

†: Specifically the DCU in the Lattice ECP5 and [ECP5-5G].

### Table Legend

| Symbol | Meaning           |
|:------:|-------------------|
| ✅     | Completed/Working |
| 📊     | In-Testing        |
| 🚧     | In-Progress       |
| 📋     | Planned/Next      |
| ⏳     | Future            |
| 📑     | Wishlist          |
| 🚫     | Unplanned         |

## License

Bakeneko is released under the [BSD-3-Clause], the full text of which can be found in the [`LICENSE`] file in the root of the [git repository].

The Bakeneko documentation is licensed under the [CC-BY-SA 4.0], the full text of which can be found in the [`LICENSE.docs`] file in the root of the [git repository].

[Torii]: https://torii.shmdn.link/
[SerDes]: https://en.wikipedia.org/wiki/SerDes
[FPGAs]: #fpga-serdes
[PIPE]: https://web.archive.org/web/20250123234132/https://cdrdv2-public.intel.com/643108/PIPE7_0_releasecandidate_2024July11-1.pdf
[ECP5-5G]: https://www.latticesemi.com/Products/FPGAandCPLD/ECP5
[BSD-3-Clause]: https://spdx.org/licenses/BSD-3-Clause.html
[`LICENSE`]: https://github.com/shrine-maiden-heavy-industries/bakeneko/blob/main/LICENSE
[CC-BY-SA 4.0]: https://creativecommons.org/licenses/by/4.0/
[`LICENSE.docs`]: https://github.com/shrine-maiden-heavy-industries/bakeneko/blob/main/LICENSE.docs
[git repository]: https://github.com/shrine-maiden-heavy-industries/bakeneko
