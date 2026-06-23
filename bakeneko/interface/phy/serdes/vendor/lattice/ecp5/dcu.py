# SPDX-License-Identifier: BSD-3-Clause

'''
Lattice Semiconductor ECP5/ECP5-5G Dual-Channel Unit (DCU) Interface.
'''

from enum                   import IntFlag, IntEnum, auto, unique
from typing                 import Literal

from torii.build.plat       import Platform
from torii.hdl.ast          import Const, Signal
from torii.hdl.dsl          import Module
from torii.hdl.ir           import Elaboratable, Instance

from .sci                   import DCUInterface
from .......types.constants import LinkSpeed

__all__ = (
	'DCU',
)

@unique
class Channel(IntFlag):
	'''
	The specific channel(s) of the ECP5 DCU to use

	These can be or'd together in order to enable both channels for the
	target DCU
	'''

	CH0 = 0x01
	''' DCU Channel 0 '''
	CH1 = 0x02
	''' DCU Channel 1 '''

	def __str__(self) -> str:
		chans = []

		if Channel.CH0 in self:
			chans.append('CH0')

		if Channel.CH1 in self:
			chans.append('CH1')

		return ','.join(chans)


@unique
class DCUNumber(IntEnum):
	''' The specific DCU to use '''

	DCU0 = auto()
	''' The left-most DCU on devices with 2 DCUs '''
	DCU1 = auto()
	''' The right-most DCU on devices with 2 DCUs '''

	def __str__(self) -> str:
		match self:
			case DCUNumber.DCU0:
				return 'DCU0'
			case DCUNumber.DCU1:
				return 'DCU1'

class DCU(Elaboratable):
	'''
	Lattice Semiconductor ECP5/ECP5-5G devices have a concept called a Dual-Channel Unit (DCU), it represents
	an encapsulation of 2 SerDes channels.

	Each ECP5/ECP5-5G device has 2 DCUs on the larger 45k an 85k variants, and a single DCU on the smaller 25k variants
	with no DCUs the non-UM devices.

	The overall structure of a DCU looks like this:

	.. code-block::

		╭───────────╮
		│    DCU    │
		├─────┬─────┤
		│ CH0 │ CH1 │
		╰─────┴─────╯

	Within each DCU, there is also an ``EXTREF`` block, which deals with internal reference clock generation
	from the DCU, as well as an auxiliary control channel.

	A more detailed block diagram of a DCU would be as follows:

	.. code-block::

		╭───────────────────────────────╮
		│              DCU              │
		│ ╭─────────╮ ╭─────────╮ ╭───╮ │
		│ │         │ │         │ │ A │ │
		│ │   CH0   │ │   CH1   │ │ U │ │
		│ │         │ │         │ │ X │ │
		│ ├─────────┤ ├─────────┤ ╰───╯ │
		│ │         │ │         │ ╭───╮ │
		│ │   PCS   │ │   PCS   │ │ E │ │
		│ │         │ │         │ │ X │ │
		│ ├─────────┤ ├─────────┤ │ T │ │
		│ │ SERDES0 │ │ SERDES1 │ │ R │ │
		│ ├────┬────┤ ├────┬────┤ │ E │ │
		│ │ RX │ TX │ │ RX │ TX │ │ F │ │
		│ ╰────┴────╯ ╰────┴────╯ ╰───╯ │
		╰───────────────────────────────╯

	For more details on the ECP5 DCUs see the Lattice Technical Note
	`FPGA-TN-02206 <https://www.latticesemi.com/view_document?document_id=50463>`_.

	Note
	----
	Many of the DCU and channel properties are set at elaboration time for the synthesis and
	place-and-route tools, however, many, if not most of them are able to be modified via the
	SerDes Client Interface (``SCI``) for the DCU.

	Parameters
	----------
	dcu: DCUNumber
		The specific DCU on the device to use.

	channel: Channel
		The specific channel or channels to use for the given DCU.

	link_speed: LinkSpeed
		The link speed for the DCUs channels.

	Attributes
	----------
	dcu_num: DCUNumber
		The DCU on the device this module is configured for

	chan: Channel
		The DCU channel(s) this module is configured for

	sci: DCUInterface
		The SerDes Client Interface for this DCU.

	'''

	def __init__(
		self, dcu: DCUNumber, channel: Channel, link_speed: Literal[LinkSpeed.LS2_5, LinkSpeed.LS5_0]
	) -> None:
		# TODO(aki): Actually make this a viable diagnostic
		assert link_speed in (LinkSpeed.LS2_5, LinkSpeed.LS2_5), 'Invalid Link Speed'

		self.dcu_num = dcu
		self.chan    = channel
		self.speed   = link_speed

		# DCU SerDes Client Interface
		self.sci = DCUInterface()

		# DCU Power
		self.p_macropdb     = Const(1) # Macrocell power down?    # p_D_MACROPDB: "DONTCARE" "0b0" "0b1"
		self.p_ib_pwdnb     = Const(1) # Input Buffer power down? # p_D_IB_PWDNB: "DONTCARE" "0b0" "0b1"
		self.p_txpll_pwrnb  = Const(1) # Transmit PLL power down  # p_D_TXPLL_PWDNB: "DONTCARE" "0b0" "0b1"
		self.i_ffc_macropdb = Const(1) # ? # i_D_FFC_MACROPDB

		# DCU Reset
		self.i_ffc_macro_rst = Signal() # Macrocell Reset? # i_D_FFC_MACRO_RST
		self.i_ffc_dual_rst  = Signal() # DCU Reset ?      # i_D_FFC_DUAL_RST
		self.i_ffc_trst      = Signal() # Transmit Reset?  # i_D_FFC_TRST

		# DCU Clocking
		self.i_refclki            = Signal()     # DCU Input Reference clock # i_D_REFCLKI
		self.i_txbit_clkn_from_nd = Signal()     # i_D_TXBIT_CLKN_FROM_ND
		self.i_txbit_clkp_from_nd = Signal()     # i_D_TXBIT_CLKP_FROM_ND
		self.o_ffs_plol           = Signal()     # TX PLL Loss-of-lock # o_FFS_PLOL
		self.o_txbit_clkn_to_nd   = Signal()     # o_D_TXBIT_CLKN_TO_ND
		self.o_txbit_clkp_to_nd   = Signal()     # o_D_TXBIT_CLKP_TO_ND
		self.p_bitclk_from_nd_en  = Signal()     # p_D_BITCLK_FROM_ND_EN: "DONTCARE" "0b0" "0b1"
		self.p_bitclk_local_en    = Const(0)     # p_D_BITCLK_LOCAL_EN: "DONTCARE" "0b0" "0b1"
		self.p_bitclk_nd_en       = Const(0)     # p_D_BITCLK_ND_EN: "DONTCARE" "0b0" "0b1"
		self.p_refck_mode         = Const(0b100) # Bit clock mode - (x25 multiplier) See DL_0B control register for details
		self.p_cdr_lol_set        = Const(0)     # p_D_CDR_LOL_SET: "DONTCARE" "0b00"-"0b11"

		# DCU Clocking - PLL
		self.i_txpll_lol_from_nd  = Signal()     # i_D_TXPLL_LOL_FROM_ND
		self.o_txpll_lol_to_nd    = Signal()     # o_D_TXPLL_LOL_TO_ND
		self.p_cmusetbiasi        = Const(0)     # p_D_CMUSETBIASI: "DONTCARE" "0b00" "0b11"
		self.p_cmuseti4cpp        = Const(0)     # p_D_CMUSETI4CPP: "DONTCARE" "0d0" "0d15"
		self.p_cmuseti4cpz        = Const(0)     # p_D_CMUSETI4CPZ: "DONTCARE" "0d0" "0d15"
		self.p_cmuseti4vco        = Const(0)     # p_D_CMUSETI4VCO: "DONTCARE" "0b00"-"0b11"
		self.p_cmuseticp4p        = Const(0)     # p_D_CMUSETICP4P: "DONTCARE" "0b00"-"0b11"
		self.p_cmuseticp4z        = Const(0)     # p_D_CMUSETICP4Z: "DONTCARE" "0b000"-"0b111"
		self.p_cmusetinitvct      = Const(0)     # p_D_CMUSETINITVCT: "DONTCARE" "0b00"-"0b11"
		self.p_cmusetiscl4vco     = Const(0)     # p_D_CMUSETISCL4VCO: "DONTCARE" "0b000"-"0b111"
		self.p_cmusetp1gm         = Const(0)     # p_D_CMUSETP1GM: "DONTCARE" "0b000"-"0b111"
		self.p_cmusetp2agm        = Const(0)     # p_D_CMUSETP2AGM: "DONTCARE" "0b000"-"0b111"
		self.p_cmusetzgm          = Const(0)     # p_D_CMUSETZGM: "DONTCARE" "0b000"-"0b111"
		self.p_pll_lol_set        = Const(0)     # p_D_PLL_LOL_SET: "DONTCARE" "0b00"-"0b11"
		self.p_refck_mode         = Const(0)     # p_D_REFCK_MODE: "DONTCARE" "0b000"-"0b100"
		self.p_rg_en              = Const(0)     # p_D_RG_EN: "DONTCARE" "0b0" "0b1"
		self.p_rg_set             = Const(0)     # p_D_RG_SET: "DONTCARE" "0b00"-"0b11"
		self.p_setpllrc           = Const(0)     # p_D_SETPLLRC: "DONTCARE" "0d0"-"0d63"
		self.p_tx_vco_ck_div      = Const(0)     # p_D_TX_VCO_CK_DIV: "DONTCARE" "0b000"-"0b111"

		# XXXX
		self.i_cin                = Signal(12) # i_D_CIN0-i_D_CIN11
		self.o_cout               = Signal(20) # o_D_COUT0-o_D_COUT19
		self.i_cyawstn            = Signal()   # i_D_CYAWSTN

		self.i_scan_enable        = Signal()   # i_D_SCAN_ENABLE
		self.i_scan_in            = Signal(8)  # i_D_SCAN_IN_0-i_D_SCAN_IN_7
		self.o_scan_out           = Signal(8)  # o_D_SCAN_OUT_0-o_D_SCAN_OUT_7
		self.i_scan_mode          = Signal()   # i_D_SCAN_MODE
		self.i_scan_reset         = Signal()   # i_D_SCAN_RESET

		self.o_sync_pulse2nd      = Signal()   # o_D_SYNC_PULSE2ND
		self.i_sync_nd            = Signal()   # i_D_SYNC_ND
		self.i_ffc_sync_toggle    = Signal()   # i_D_FFC_SYNC_TOGGLE
		self.p_sync_local_en      = Const(0)   # p_D_SYNC_LOCAL_EN: "DONTCARE" "0b0" "0b1"
		self.p_sync_nd_en         = Const(0)   # p_D_SYNC_ND_EN: "DONTCARE" "0b0" "0b1"

		self.p_bus8bit_sel        = Const(0)   # p_D_BUS8BIT_SEL: "DONTCARE" "0b0" "0b1"

		self.p_high_mark          = Const(0)   # p_D_HIGH_MARK: "DONTCARE" "0d0"-"0d15"
		self.p_low_mark           = Const(0)   # p_D_LOW_MARK: "DONTCARE" "0d0"-"0d15"

		self.p_tx_max_rate        = Const(0)   # p_D_TX_MAX_RATE: "DONTCARE" "0.27"-"3.125"
		self.p_xge_mode           = Const(0)   # p_D_XGE_MODE: "DONTCARE" "0b0" "0b1"

		## Analog
		self.p_dco_calib_time_sel = Const(0)   # p_D_DCO_CALIB_TIME_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_isetlos            = Const(0)   # p_D_ISETLOS: "DONTCARE" "0d0"-"0d255"
		self.p_pd_iset            = Const(0)   # p_D_PD_ISET: "DONTCARE" "0b00"-"0b11"
		self.p_req_iset           = Const(0)   # p_D_REQ_ISET: "DONTCARE" "0b000"-"0b111"
		self.p_seticonst_aux      = Const(0)   # p_D_SETICONST_AUX: "DONTCARE" "0b00"-"0b11"
		self.p_seticonst_ch       = Const(0)   # p_D_SETICONST_CH: "DONTCARE" "0b00"-"0b11"
		self.p_setirpoly_aux      = Const(0)   # p_D_SETIRPOLY_AUX: "DONTCARE" "0b00"-"0b11"
		self.p_setirpoly_ch       = Const(0)   # p_D_SETIRPOLY_CH: "DONTCARE" "0b00"-"0b11"

		# DCU Channel 0
		self.i_ch0_ff_ebrd_clk        = Signal()   # i_CH0_FF_EBRD_CLK
		self.i_ch0_ff_rxi_clk         = Signal()   # i_CH0_FF_RXI_CLK
		self.i_ch0_ff_tx_d            = Signal(24) # i_CH0_FF_TX_D_0-i_CH0_FF_TX_D_23
		self.i_ch0_ff_txi_clk         = Signal()   # i_CH0_FF_TXI_CLK
		self.i_ch0_ffc_cdr_en_bitslip = Signal()   # i_CH0_FFC_CDR_EN_BITSLIP
		self.i_ch0_ffc_div11_mode_rx  = Signal()   # i_CH0_FFC_DIV11_MODE_RX
		self.i_ch0_ffc_div11_mode_tx  = Signal()   # i_CH0_FFC_DIV11_MODE_TX
		self.i_ch0_ffc_ei_en          = Signal()   # i_CH0_FFC_EI_EN
		self.i_ch0_ffc_enable_cgalign = Signal()   # i_CH0_FFC_ENABLE_CGALIGN
		self.i_ch0_ffc_fb_loopback    = Signal()   # i_CH0_FFC_FB_LOOPBACK
		self.i_ch0_ffc_lane_rx_rst    = Signal()   # i_CH0_FFC_LANE_RX_RST
		self.i_ch0_ffc_lane_tx_rst    = Signal()   # i_CH0_FFC_LANE_TX_RST
		self.i_ch0_ffc_ldr_core2tx_en = Signal()   # i_CH0_FFC_LDR_CORE2TX_EN
		self.i_ch0_ffc_pcie_ct        = Signal()   # i_CH0_FFC_PCIE_CT
		self.i_ch0_ffc_pcie_det_en    = Signal()   # i_CH0_FFC_PCIE_DET_EN
		self.i_ch0_ffc_pfifo_clr      = Signal()   # i_CH0_FFC_PFIFO_CLR
		self.i_ch0_ffc_rate_mode_rx   = Signal()   # i_CH0_FFC_RATE_MODE_RX
		self.i_ch0_ffc_rate_mode_tx   = Signal()   # i_CH0_FFC_RATE_MODE_TX
		self.i_ch0_ffc_rrst           = Signal()   # i_CH0_FFC_RRST
		self.i_ch0_ffc_rx_gear_mode   = Signal()   # i_CH0_FFC_RX_GEAR_MODE
		self.i_ch0_ffc_rxpwdnb        = Signal()   # i_CH0_FFC_RXPWDNB
		self.i_ch0_ffc_sb_inv_rx      = Signal()   # i_CH0_FFC_SB_INV_RX
		self.i_ch0_ffc_sb_pfifo_lp    = Signal()   # i_CH0_FFC_SB_PFIFO_LP
		self.i_ch0_ffc_signal_detect  = Signal()   # i_CH0_FFC_SIGNAL_DETECT
		self.i_ch0_ffc_tx_gear_mode   = Signal()   # i_CH0_FFC_TX_GEAR_MODE
		self.i_ch0_ffc_txpwdnb        = Signal()   # i_CH0_FFC_TXPWDNB
		self.i_ch0_hdinn              = Signal()   # i_CH0_HDINN
		self.i_ch0_hdinp              = Signal()   # i_CH0_HDINP
		self.i_ch0_ldr_core2tx        = Signal()   # i_CH0_LDR_CORE2TX
		self.i_ch0_rx_refclk          = Signal()   # i_CH0_RX_REFCLK
		self.o_ch0_ff_rx_d            = Signal(24) # o_CH0_FF_RX_D_0-o_CH0_FF_RX_D_23
		self.o_ch0_ff_rx_f_clk        = Signal()   # o_CH0_FF_RX_F_CLK
		self.o_ch0_ff_rx_h_clk        = Signal()   # o_CH0_FF_RX_H_CLK
		self.o_ch0_ff_rx_pclk         = Signal()   # o_CH0_FF_RX_PCLK
		self.o_ch0_ff_tx_f_clk        = Signal()   # o_CH0_FF_TX_F_CLK
		self.o_ch0_ff_tx_h_clk        = Signal()   # o_CH0_FF_TX_H_CLK
		self.o_ch0_ff_tx_pclk         = Signal()   # o_CH0_FF_TX_PCLK
		self.o_ch0_ffs_cc_overrun     = Signal()   # o_CH0_FFS_CC_OVERRUN
		self.o_ch0_ffs_cc_underrun    = Signal()   # o_CH0_FFS_CC_UNDERRUN
		self.o_ch0_ffs_ls_sync_status = Signal()   # o_CH0_FFS_LS_SYNC_STATUS
		self.o_ch0_ffs_pcie_con       = Signal()   # o_CH0_FFS_PCIE_CON
		self.o_ch0_ffs_pcie_done      = Signal()   # o_CH0_FFS_PCIE_DONE
		self.o_ch0_ffs_rlol           = Signal()   # o_CH0_FFS_RLOL
		self.o_ch0_ffs_rlos           = Signal()   # o_CH0_FFS_RLOS
		self.o_ch0_ffs_rxfbfifo_error = Signal()   # o_CH0_FFS_RXFBFIFO_ERROR
		self.o_ch0_ffs_skp_added      = Signal()   # o_CH0_FFS_SKP_ADDED
		self.o_ch0_ffs_skp_deleted    = Signal()   # o_CH0_FFS_SKP_DELETED
		self.o_ch0_ffs_txfbfifo_error = Signal()   # o_CH0_FFS_TXFBFIFO_ERROR
		self.o_ch0_hdoutn             = Signal()   # o_CH0_HDOUTN
		self.o_ch0_hdoutp             = Signal()   # o_CH0_HDOUTP
		self.o_ch0_ldr_rx2core        = Signal()   # o_CH0_LDR_RX2CORE
		self.p_ch0_cc_match_1         = Const(0)   # p_CH0_CC_MATCH_1: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch0_cc_match_2         = Const(0)   # p_CH0_CC_MATCH_2: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch0_cc_match_3         = Const(0)   # p_CH0_CC_MATCH_3: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch0_cc_match_4         = Const(0)   # p_CH0_CC_MATCH_4: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch0_cdr_max_rate       = Const(0)   # p_CH0_CDR_MAX_RATE: "DONTCARE" "0.27"-"3.125"
		self.p_ch0_ctc_bypass         = Const(0)   # p_CH0_CTC_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_dec_bypass         = Const(0)   # p_CH0_DEC_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_enable_cg_align    = Const(0)   # p_CH0_ENABLE_CG_ALIGN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_enc_bypass         = Const(0)   # p_CH0_ENC_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_ff_rx_f_clk_dis    = Const(0)   # p_CH0_FF_RX_F_CLK_DIS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_ff_rx_h_clk_en     = Const(0)   # p_CH0_FF_RX_H_CLK_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_ff_tx_f_clk_dis    = Const(0)   # p_CH0_FF_TX_F_CLK_DIS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_ff_tx_h_clk_en     = Const(0) # p_CH0_FF_TX_H_CLK_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_ge_an_enable       = Const(0) # p_CH0_GE_AN_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_invert_rx          = Const(0) # p_CH0_INVERT_RX: "DONTCARE" "0b0" "0b1"
		self.p_ch0_invert_tx          = Const(0) # p_CH0_INVERT_TX: "DONTCARE" "0b0" "0b1"
		self.p_ch0_ldr_core2tx_sel    = Const(0) # p_CH0_LDR_CORE2TX_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch0_ldr_rx2core_sel    = Const(0) # p_CH0_LDR_RX2CORE_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch0_leq_offset_sel     = Const(0) # p_CH0_LEQ_OFFSET_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch0_leq_offset_trim    = Const(0) # p_CH0_LEQ_OFFSET_TRIM: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_lsm_disable        = Const(0) # p_CH0_LSM_DISABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_match_2_enable     = Const(0) # p_CH0_MATCH_2_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_match_4_enable     = Const(0) # p_CH0_MATCH_4_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_min_ipg_cnt        = Const(0) # p_CH0_MIN_IPG_CNT: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_pcie_ei_en         = Const(0) # p_CH0_PCIE_EI_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_pcie_mode          = Const(0) # p_CH0_PCIE_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_pcs_det_time_sel   = Const(0) # p_CH0_PCS_DET_TIME_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_pden_sel           = Const(0) # p_CH0_PDEN_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch0_prbs_enable        = Const(0) # p_CH0_PRBS_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_prbs_lock          = Const(0) # p_CH0_PRBS_LOCK: "DONTCARE" "0b0" "0b1"
		self.p_ch0_prbs_selection     = Const(0) # p_CH0_PRBS_SELECTION: "DONTCARE" "0b0" "0b1"
		self.p_ch0_protocol           = Const(0) # p_CH0_PROTOCOL: "DONTCARE" "PCIE" "GBE" "SGMII" "XAUI" "SDI" "CPRI" "JESD204" "EDP" "G8B10B" "8BSER" "10BSER" "0d0"-"0d9"
		self.p_ch0_rate_mode_rx       = Const(0) # p_CH0_RATE_MODE_RX: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rate_mode_tx       = Const(0) # p_CH0_RATE_MODE_TX: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rcv_dcc_en         = Const(0) # p_CH0_RCV_DCC_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_req_en             = Const(0) # p_CH0_REQ_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_req_lvl_set        = Const(0) # p_CH0_REQ_LVL_SET: "DONTCARE" "0b00" "0b11"
		self.p_ch0_rio_mode           = Const(0) # p_CH0_RIO_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rlos_sel           = Const(0) # p_CH0_RLOS_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rpwdnb             = Const(0) # p_CH0_RPWDNB: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rterm_rx           = Const(0) # p_CH0_RTERM_RX: "DONTCARE" "0d0"-"0d31"
		self.p_ch0_rterm_tx           = Const(0) # p_CH0_RTERM_TX: "DONTCARE" "0d0"-"0d31
		self.p_ch0_rx_dco_ck_div      = Const(0) # p_CH0_RX_DCO_CK_DIV: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_rx_div11_sel       = Const(0) # p_CH0_RX_DIV11_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rx_gear_bypass     = Const(0) # p_CH0_RX_GEAR_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rx_gear_mode       = Const(0) # p_CH0_RX_GEAR_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rx_los_ceq         = Const(0) # p_CH0_RX_LOS_CEQ: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_rx_los_en          = Const(0) # p_CH0_RX_LOS_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rx_los_hyst_en     = Const(0) # p_CH0_RX_LOS_HYST_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rx_los_lvl         = Const(0) # p_CH0_RX_LOS_LVL: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_rx_rate_sel        = Const(0) # p_CH0_RX_RATE_SEL: "DONTCARE" "0d0"-"0d15"
		self.p_ch0_rx_sb_bypass       = Const(0) # p_CH0_RX_SB_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_rxin_cm            = Const(0) # p_CH0_RXIN_CM: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_rxterm_cm          = Const(0) # p_CH0_RXTERM_CM: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_sb_bypass          = Const(0) # p_CH0_SB_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_sel_sd_rx_clk      = Const(0) # p_CH0_SEL_SD_RX_CLK: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tdrv_dat_sel       = Const(0) # p_CH0_TDRV_DAT_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_post_en       = Const(0) # p_CH0_TDRV_POST_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tdrv_pre_en        = Const(0) # p_CH0_TDRV_PRE_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tdrv_slice0_cur    = Const(0) # p_CH0_TDRV_SLICE0_CUR: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_tdrv_slice0_sel    = Const(0) # p_CH0_TDRV_SLICE0_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice1_cur    = Const(0) # p_CH0_TDRV_SLICE1_CUR: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_tdrv_slice1_sel    = Const(0) # p_CH0_TDRV_SLICE1_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice2_cur    = Const(0) # p_CH0_TDRV_SLICE2_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice2_sel    = Const(0) # p_CH0_TDRV_SLICE2_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice3_cur    = Const(0) # p_CH0_TDRV_SLICE3_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice3_sel    = Const(0) # p_CH0_TDRV_SLICE3_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice4_cur    = Const(0) # p_CH0_TDRV_SLICE4_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice4_sel    = Const(0) # p_CH0_TDRV_SLICE4_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice5_cur    = Const(0) # p_CH0_TDRV_SLICE5_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tdrv_slice5_sel    = Const(0) # p_CH0_TDRV_SLICE5_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tpwdnb             = Const(0) # p_CH0_TPWDNB: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tx_cm_sel          = Const(0) # p_CH0_TX_CM_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_tx_div11_sel       = Const(0) # p_CH0_TX_DIV11_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tx_gear_bypass     = Const(0) # p_CH0_TX_GEAR_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tx_gear_mode       = Const(0) # p_CH0_TX_GEAR_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tx_post_sign       = Const(0) # p_CH0_TX_POST_SIGN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_tx_pre_sign        = Const(0) # p_CH0_TX_PRE_SIGN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_txamplitude        = Const(0) # p_CH0_TXAMPLITUDE: "DONTCARE" "0d0"-"0d9"
		self.p_ch0_txdepost           = Const(0) # p_CH0_TXDEPOST: "DONTCARE" "0d0"-"0d9"
		self.p_ch0_txdepre            = Const(0) # p_CH0_TXDEPRE: "DONTCARE" "0d0"-"0d9"
		self.p_ch0_uc_mode            = Const(0) # p_CH0_UC_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_udf_comma_a        = Const(0) # p_CH0_UDF_COMMA_A: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch0_udf_comma_b        = Const(0) # p_CH0_UDF_COMMA_B: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch0_udf_comma_mask     = Const(0) # p_CH0_UDF_COMMA_MASK: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch0_wa_bypass          = Const(0) # p_CH0_WA_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch0_wa_mode            = Const(0) # p_CH0_WA_MODE: "DONTCARE" "0b0" "0b1"
		## Analog
		self.p_ch0_auto_calib_en      = Const(0) # p_CH0_AUTO_CALIB_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_auto_facq_en       = Const(0) # p_CH0_AUTO_FACQ_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_band_threshold     = Const(0) # p_CH0_BAND_THRESHOLD: "DONTCARE" "0d0"-"0d63"
		self.p_ch0_calib_ck_mode      = Const(0) # p_CH0_CALIB_CK_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch0_cdr_cnt4sel        = Const(0) # p_CH0_CDR_CNT4SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_cdr_cnt8sel        = Const(0) # p_CH0_CDR_CNT8SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_dcoatdcfg          = Const(0) # p_CH0_DCOATDCFG: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_dcoatddly          = Const(0) # p_CH0_DCOATDDLY: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_dcobypsatd         = Const(0) # p_CH0_DCOBYPSATD: "DONTCARE" "0b0" "0b1"
		self.p_ch0_dcocaldiv          = Const(0) # p_CH0_DCOCALDIV: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_dcoctlgi           = Const(0) # p_CH0_DCOCTLGI: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_dcodisbdavoid      = Const(0) # p_CH0_DCODISBDAVOID: "DONTCARE" "0b0" "0b1"
		self.p_ch0_dcofltdac          = Const(0) # p_CH0_DCOFLTDAC: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_dcoftnrg           = Const(0) # p_CH0_DCOFTNRG: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_dcoiostune         = Const(0) # p_CH0_DCOIOSTUNE: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_dcoitune           = Const(0) # p_CH0_DCOITUNE: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_dcoitune4lsb       = Const(0) # p_CH0_DCOITUNE4LSB: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_dcoiupdnx2         = Const(0) # p_CH0_DCOIUPDNX2: "DONTCARE" "0b0" "0b1"
		self.p_ch0_dconuoflsb         = Const(0) # p_CH0_DCONUOFLSB: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_dcoscalei          = Const(0) # p_CH0_DCOSCALEI: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_dcostartval        = Const(0) # p_CH0_DCOSTARTVAL: "DONTCARE" "0b000"-"0b111"
		self.p_ch0_dcostep            = Const(0) # p_CH0_DCOSTEP: "DONTCARE" "0b00"-"0b11"
		self.p_ch0_reg_band_offset    = Const(0) # p_CH0_REG_BAND_OFFSET: "DONTCARE" "0d0"-"0d15"
		self.p_ch0_reg_band_sel       = Const(0) # p_CH0_REG_BAND_SEL: "DONTCARE" "0d0"-"0d63"
		self.p_ch0_reg_idac_en        = Const(0) # p_CH0_REG_IDAC_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch0_reg_idac_sel       = Const(0) # p_CH0_REG_IDAC_SEL: "DONTCARE" "0d0"-"0d1023"

		# DCU Channel 1
		self.i_ch1_ff_ebrd_clk        = Signal()   # i_CH1_FF_EBRD_CLK
		self.i_ch1_ff_rxi_clk         = Signal()   # i_CH1_FF_RXI_CLK
		self.i_ch1_ff_tx_d            = Signal(24) # i_CH1_FF_TX_D_0-i_CH1_FF_TX_D_23
		self.i_ch1_ff_txi_clk         = Signal()   # i_CH1_FF_TXI_CLK
		self.i_ch1_ffc_cdr_en_bitslip = Signal()   # i_CH1_FFC_CDR_EN_BITSLIP
		self.i_ch1_ffc_div11_mode_rx  = Signal()   # i_CH1_FFC_DIV11_MODE_RX
		self.i_ch1_ffc_div11_mode_tx  = Signal()   # i_CH1_FFC_DIV11_MODE_TX
		self.i_ch1_ffc_ei_en          = Signal()   # i_CH1_FFC_EI_EN
		self.i_ch1_ffc_enable_cgalign = Signal()   # i_CH1_FFC_ENABLE_CGALIGN
		self.i_ch1_ffc_fb_loopback    = Signal()   # i_CH1_FFC_FB_LOOPBACK
		self.i_ch1_ffc_lane_rx_rst    = Signal()   # i_CH1_FFC_LANE_RX_RST
		self.i_ch1_ffc_lane_tx_rst    = Signal()   # i_CH1_FFC_LANE_TX_RST
		self.i_ch1_ffc_ldr_core2tx_en = Signal()   # i_CH1_FFC_LDR_CORE2TX_EN
		self.i_ch1_ffc_pcie_ct        = Signal()   # i_CH1_FFC_PCIE_CT
		self.i_ch1_ffc_pcie_det_en    = Signal()   # i_CH1_FFC_PCIE_DET_EN
		self.i_ch1_ffc_pfifo_clr      = Signal()   # i_CH1_FFC_PFIFO_CLR
		self.i_ch1_ffc_rate_mode_rx   = Signal()   # i_CH1_FFC_RATE_MODE_RX
		self.i_ch1_ffc_rate_mode_tx   = Signal()   # i_CH1_FFC_RATE_MODE_TX
		self.i_ch1_ffc_rrst           = Signal()   # i_CH1_FFC_RRST
		self.i_ch1_ffc_rx_gear_mode   = Signal()   # i_CH1_FFC_RX_GEAR_MODE
		self.i_ch1_ffc_rxpwdnb        = Signal()   # i_CH1_FFC_RXPWDNB
		self.i_ch1_ffc_sb_inv_rx      = Signal()   # i_CH1_FFC_SB_INV_RX
		self.i_ch1_ffc_sb_pfifo_lp    = Signal()   # i_CH1_FFC_SB_PFIFO_LP
		self.i_ch1_ffc_signal_detect  = Signal()   # i_CH1_FFC_SIGNAL_DETECT
		self.i_ch1_ffc_tx_gear_mode   = Signal()   # i_CH1_FFC_TX_GEAR_MODE
		self.i_ch1_ffc_txpwdnb        = Signal()   # i_CH1_FFC_TXPWDNB
		self.i_ch1_hdinn              = Signal()   # i_CH1_HDINN
		self.i_ch1_hdinp              = Signal()   # i_CH1_HDINP
		self.i_ch1_ldr_core2tx        = Signal()   # i_CH1_LDR_CORE2TX
		self.i_ch1_rx_refclk          = Signal()   # i_CH1_RX_REFCLK
		self.o_ch1_ff_rx_d            = Signal(24) # o_CH1_FF_RX_D_0-o_CH1_FF_RX_D_23
		self.o_ch1_ff_rx_f_clk        = Signal()   # o_CH1_FF_RX_F_CLK
		self.o_ch1_ff_rx_h_clk        = Signal()   # o_CH1_FF_RX_H_CLK
		self.o_ch1_ff_rx_pclk         = Signal()   # o_CH1_FF_RX_PCLK
		self.o_ch1_ff_tx_f_clk        = Signal()   # o_CH1_FF_TX_F_CLK
		self.o_ch1_ff_tx_h_clk        = Signal()   # o_CH1_FF_TX_H_CLK
		self.o_ch1_ff_tx_pclk         = Signal()   # o_CH1_FF_TX_PCLK
		self.o_ch1_ffs_cc_overrun     = Signal()   # o_CH1_FFS_CC_OVERRUN
		self.o_ch1_ffs_cc_underrun    = Signal()   # o_CH1_FFS_CC_UNDERRUN
		self.o_ch1_ffs_ls_sync_status = Signal()   # o_CH1_FFS_LS_SYNC_STATUS
		self.o_ch1_ffs_pcie_con       = Signal()   # o_CH1_FFS_PCIE_CON
		self.o_ch1_ffs_pcie_done      = Signal()   # o_CH1_FFS_PCIE_DONE
		self.o_ch1_ffs_rlol           = Signal()   # o_CH1_FFS_RLOL
		self.o_ch1_ffs_rlos           = Signal()   # o_CH1_FFS_RLOS
		self.o_ch1_ffs_rxfbfifo_error = Signal()   # o_CH1_FFS_RXFBFIFO_ERROR
		self.o_ch1_ffs_skp_added      = Signal()   # o_CH1_FFS_SKP_ADDED
		self.o_ch1_ffs_skp_deleted    = Signal()   # o_CH1_FFS_SKP_DELETED
		self.o_ch1_ffs_txfbfifo_error = Signal()   # o_CH1_FFS_TXFBFIFO_ERROR
		self.o_ch1_hdoutn             = Signal()   # o_CH1_HDOUTN
		self.o_ch1_hdoutp             = Signal()   # o_CH1_HDOUTP
		self.o_ch1_ldr_rx2core        = Signal()   # o_CH1_LDR_RX2CORE
		self.p_ch1_cc_match_1         = Const(0)   # p_CH1_CC_MATCH_1: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch1_cc_match_2         = Const(0)   # p_CH1_CC_MATCH_2: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch1_cc_match_3         = Const(0)   # p_CH1_CC_MATCH_3: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch1_cc_match_4         = Const(0)   # p_CH1_CC_MATCH_4: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch1_cdr_max_rate       = Const(0)   # p_CH1_CDR_MAX_RATE: "DONTCARE" "0.27"-"3.125"
		self.p_ch1_ctc_bypass         = Const(0)   # p_CH1_CTC_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_dec_bypass         = Const(0)   # p_CH1_DEC_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_enable_cg_align    = Const(0)   # p_CH1_ENABLE_CG_ALIGN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_enc_bypass         = Const(0)   # p_CH1_ENC_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_ff_rx_f_clk_dis    = Const(0)   # p_CH1_FF_RX_F_CLK_DIS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_ff_rx_h_clk_en     = Const(0)   # p_CH1_FF_RX_H_CLK_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_ff_tx_f_clk_dis    = Const(0)   # p_CH1_FF_TX_F_CLK_DIS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_ff_tx_h_clk_en     = Const(0)   # p_CH1_FF_TX_H_CLK_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_ge_an_enable       = Const(0)   # p_CH1_GE_AN_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_invert_rx          = Const(0)   # p_CH1_INVERT_RX: "DONTCARE" "0b0" "0b1"
		self.p_ch1_invert_tx          = Const(0)   # p_CH1_INVERT_TX: "DONTCARE" "0b0" "0b1"
		self.p_ch1_ldr_core2tx_sel    = Const(0)   # p_CH1_LDR_CORE2TX_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch1_ldr_rx2core_sel    = Const(0)   # p_CH1_LDR_RX2CORE_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch1_leq_offset_sel     = Const(0)   # p_CH1_LEQ_OFFSET_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch1_leq_offset_trim    = Const(0)   # p_CH1_LEQ_OFFSET_TRIM: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_lsm_disable        = Const(0)   # p_CH1_LSM_DISABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_match_2_enable     = Const(0)   # p_CH1_MATCH_2_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_match_4_enable     = Const(0)   # p_CH1_MATCH_4_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_min_ipg_cnt        = Const(0)   # p_CH1_MIN_IPG_CNT: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_pcie_ei_en         = Const(0)   # p_CH1_PCIE_EI_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_pcie_mode          = Const(0)   # p_CH1_PCIE_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_pcs_det_time_sel   = Const(0)   # p_CH1_PCS_DET_TIME_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_pden_sel           = Const(0)   # p_CH1_PDEN_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch1_prbs_enable        = Const(0)   # p_CH1_PRBS_ENABLE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_prbs_lock          = Const(0)   # p_CH1_PRBS_LOCK: "DONTCARE" "0b0" "0b1"
		self.p_ch1_prbs_selection     = Const(0)   # p_CH1_PRBS_SELECTION: "DONTCARE" "0b0" "0b1"
		self.p_ch1_protocol           = Const(0)   # p_CH1_PROTOCOL: "DONTCARE" "PCIE" "GBE" "SGMII" "XAUI" "SDI" "CPRI" "JESD204" "EDP" "G8B10B" "8BSER" "10BSER" "0d0"-"0d9"
		self.p_ch1_rate_mode_rx       = Const(0)   # p_CH1_RATE_MODE_RX: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rate_mode_tx       = Const(0)   # p_CH1_RATE_MODE_TX: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rcv_dcc_en         = Const(0)   # p_CH1_RCV_DCC_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_req_en             = Const(0)   # p_CH1_REQ_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_req_lvl_set        = Const(0)   # p_CH1_REQ_LVL_SET: "DONTCARE" "0b00" "0b11"
		self.p_ch1_rio_mode           = Const(0)   # p_CH1_RIO_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rlos_sel           = Const(0)   # p_CH1_RLOS_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rpwdnb             = Const(0)   # p_CH1_RPWDNB: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rterm_rx           = Const(0)   # p_CH1_RTERM_RX: "DONTCARE" "0d0"-"0d31"
		self.p_ch1_rterm_tx           = Const(0)   # p_CH1_RTERM_TX: "DONTCARE" "0d0"-"0d31"
		self.p_ch1_rx_dco_ck_div      = Const(0)   # p_CH1_RX_DCO_CK_DIV: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_rx_div11_sel       = Const(0)   # p_CH1_RX_DIV11_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rx_gear_bypass     = Const(0)   # p_CH1_RX_GEAR_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rx_gear_mode       = Const(0)   # p_CH1_RX_GEAR_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rx_los_ceq         = Const(0)   # p_CH1_RX_LOS_CEQ: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_rx_los_en          = Const(0)   # p_CH1_RX_LOS_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rx_los_hyst_en     = Const(0)   # p_CH1_RX_LOS_HYST_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rx_los_lvl         = Const(0)   # p_CH1_RX_LOS_LVL: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_rx_rate_sel        = Const(0)   # p_CH1_RX_RATE_SEL: "DONTCARE" "0d0"-"0d15"
		self.p_ch1_rx_sb_bypass       = Const(0)   # p_CH1_RX_SB_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_rxin_cm            = Const(0)   # p_CH1_RXIN_CM: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_rxterm_cm          = Const(0)   # p_CH1_RXTERM_CM: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_sb_bypass          = Const(0)   # p_CH1_SB_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_sel_sd_rx_clk      = Const(0)   # p_CH1_SEL_SD_RX_CLK: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tdrv_dat_sel       = Const(0)   # p_CH1_TDRV_DAT_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_post_en       = Const(0)   # p_CH1_TDRV_POST_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tdrv_pre_en        = Const(0)   # p_CH1_TDRV_PRE_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tdrv_slice0_cur    = Const(0)   # p_CH1_TDRV_SLICE0_CUR: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_tdrv_slice0_sel    = Const(0)   # p_CH1_TDRV_SLICE0_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice1_cur    = Const(0)   # p_CH1_TDRV_SLICE1_CUR: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_tdrv_slice1_sel    = Const(0)   # p_CH1_TDRV_SLICE1_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice2_cur    = Const(0)   # p_CH1_TDRV_SLICE2_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice2_sel    = Const(0)   # p_CH1_TDRV_SLICE2_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice3_cur    = Const(0)   # p_CH1_TDRV_SLICE3_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice3_sel    = Const(0)   # p_CH1_TDRV_SLICE3_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice4_cur    = Const(0)   # p_CH1_TDRV_SLICE4_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice4_sel    = Const(0)   # p_CH1_TDRV_SLICE4_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice5_cur    = Const(0)   # p_CH1_TDRV_SLICE5_CUR: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tdrv_slice5_sel    = Const(0)   # p_CH1_TDRV_SLICE5_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tpwdnb             = Const(0)   # p_CH1_TPWDNB: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tx_cm_sel          = Const(0)   # p_CH1_TX_CM_SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_tx_div11_sel       = Const(0)   # p_CH1_TX_DIV11_SEL: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tx_gear_bypass     = Const(0)   # p_CH1_TX_GEAR_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tx_gear_mode       = Const(0)   # p_CH1_TX_GEAR_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tx_post_sign       = Const(0)   # p_CH1_TX_POST_SIGN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_tx_pre_sign        = Const(0)   # p_CH1_TX_PRE_SIGN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_txamplitude        = Const(0)   # p_CH1_TXAMPLITUDE: "DONTCARE" "0d0"-"0d9"
		self.p_ch1_txdepost           = Const(0)   # p_CH1_TXDEPOST: "DONTCARE" "0d0"-"0d9"
		self.p_ch1_txdepre            = Const(0)   # p_CH1_TXDEPRE: "DONTCARE" "0d0"-"0d9"
		self.p_ch1_uc_mode            = Const(0)   # p_CH1_UC_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_udf_comma_a        = Const(0)   # p_CH1_UDF_COMMA_A: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch1_udf_comma_b        = Const(0)   # p_CH1_UDF_COMMA_B: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch1_udf_comma_mask     = Const(0)   # p_CH1_UDF_COMMA_MASK: "DONTCARE" "0x000"-"0x3ff"
		self.p_ch1_wa_bypass          = Const(0)   # p_CH1_WA_BYPASS: "DONTCARE" "0b0" "0b1"
		self.p_ch1_wa_mode            = Const(0)   # p_CH1_WA_MODE: "DONTCARE" "0b0" "0b1"
		## Analog attrs
		self.p_ch1_auto_calib_en      = Const(0) # p_CH1_AUTO_CALIB_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_auto_facq_en       = Const(0) # p_CH1_AUTO_FACQ_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_band_threshold     = Const(0) # p_CH1_BAND_THRESHOLD: "DONTCARE" "0d0"-"0d63"
		self.p_ch1_calib_ck_mode      = Const(0) # p_CH1_CALIB_CK_MODE: "DONTCARE" "0b0" "0b1"
		self.p_ch1_cdr_cnt4sel        = Const(0) # p_CH1_CDR_CNT4SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_cdr_cnt8sel        = Const(0) # p_CH1_CDR_CNT8SEL: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_dcoatdcfg          = Const(0) # p_CH1_DCOATDCFG: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_dcoatddly          = Const(0) # p_CH1_DCOATDDLY: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_dcobypsatd         = Const(0) # p_CH1_DCOBYPSATD: "DONTCARE" "0b0" "0b1"
		self.p_ch1_dcocaldiv          = Const(0) # p_CH1_DCOCALDIV: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_dcoctlgi           = Const(0) # p_CH1_DCOCTLGI: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_dcodisbdavoid      = Const(0) # p_CH1_DCODISBDAVOID: "DONTCARE" "0b0" "0b1"
		self.p_ch1_dcofltdac          = Const(0) # p_CH1_DCOFLTDAC: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_dcoftnrg           = Const(0) # p_CH1_DCOFTNRG: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_dcoiostune         = Const(0) # p_CH1_DCOIOSTUNE: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_dcoitune           = Const(0) # p_CH1_DCOITUNE: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_dcoitune4lsb       = Const(0) # p_CH1_DCOITUNE4LSB: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_dcoiupdnx2         = Const(0) # p_CH1_DCOIUPDNX2: "DONTCARE" "0b0" "0b1"
		self.p_ch1_dconuoflsb         = Const(0) # p_CH1_DCONUOFLSB: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_dcoscalei          = Const(0) # p_CH1_DCOSCALEI: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_dcostartval        = Const(0) # p_CH1_DCOSTARTVAL: "DONTCARE" "0b000"-"0b111"
		self.p_ch1_dcostep            = Const(0) # p_CH1_DCOSTEP: "DONTCARE" "0b00"-"0b11"
		self.p_ch1_reg_band_offset    = Const(0) # p_CH1_REG_BAND_OFFSET: "DONTCARE" "0d0"-"0d15"
		self.p_ch1_reg_band_sel       = Const(0) # p_CH1_REG_BAND_SEL: "DONTCARE" "0d0"-"0d63"
		self.p_ch1_reg_idac_en        = Const(0) # p_CH1_REG_IDAC_EN: "DONTCARE" "0b0" "0b1"
		self.p_ch1_reg_idac_sel       = Const(0) # p_CH1_REG_IDAC_SEL: "DONTCARE" "0d0"-"0d1023"

	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		m.submodules.dcu = dcu = Instance(
			'DCUA',
			src_loc    = None,
			src_loc_at = 0,
			# SerDes Client Interface
			i_D_SCISELAUX = self.sci.sci_sel,
			i_D_SCIENAUX  = self.sci.sci_en,
			i_CH0_SCIEN   = self.sci.sci_en_ch0,
			i_CH0_SCISEL  = self.sci.sci_sel_ch0,
			i_CH1_SCIEN   = self.sci.sci_en_ch1,
			i_CH1_SCISEL  = self.sci.sci_sel_ch1,
			o_D_SCIINT    = self.sci.sci_int,
			i_D_SCIWSTN   = self.sci.sci_wrn,
			i_D_SCIRD     = self.sci.sci_rd,
			**{ f'i_D_SCIWDATA{bit}': self.sci.sci_wdata[bit] for bit in range(8) },
			**{ f'o_D_SCIRDATA{bit}': self.sci.sci_rdata[bit] for bit in range(8) },
			**{ f'i_D_SCIADDR{bit}': self.sci.sci_addr[bit] for bit in range(6) },

		)

		return m
