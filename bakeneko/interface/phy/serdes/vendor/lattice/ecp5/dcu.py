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

	refclk: Signal
		The input reference clock for this DCU

	tx0_p : Signal | None
		The positive side of the channel 0 transmitter pair

	tx0_n: Signal | None
		The negative side of the channel 0 transmitter pair

	rx0_p: Signal | None
		The positive side of the channel 0 receiver pair

	rx0_n: Signal | None
		The negative side of the channel 0 receiver pair

	tx1_p : Signal | None
		The positive side of the channel 0 transmitter pair

	tx1_n: Signal | None
		The negative side of the channel 0 transmitter pair

	rx1_p: Signal | None
		The positive side of the channel 0 receiver pair

	rx1_n: Signal | None
		The negative side of the channel 0 receiver pair

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
		self, *, dcu: DCUNumber, channel: Channel, link_speed: Literal[LinkSpeed.LS2_5, LinkSpeed.LS5_0],
		refclk: Signal,
		tx0_p: Signal | None = None, tx0_n: Signal | None = None,
		rx0_p: Signal | None = None, rx0_n: Signal | None = None,
		tx1_p: Signal | None = None, tx1_n: Signal | None = None,
		rx1_p: Signal | None = None, rx1_n: Signal | None = None,
	) -> None:
		# TODO(aki): Actually make this a viable diagnostic
		assert link_speed in (LinkSpeed.LS2_5, LinkSpeed.LS2_5), 'Invalid Link Speed'

		self.dcu_num = dcu
		self.chan    = channel
		self.speed   = link_speed

		self.ch0_invert_tx = False
		self.ch0_invert_rx = False
		self.ch1_invert_tx = False
		self.ch1_invert_rx = False

		# Validate to ensure we have the proper signals passed in
		if Channel.CH0 in self.chan and not all((tx0_p, tx0_n, rx0_p, rx0_n)):
			raise ValueError('Must specify channel 0 RX and TX signals when channel 0 is enabled')

		if Channel.CH1 in self.chan and not all((tx1_p, tx1_n, rx1_p, rx1_n)):
			raise ValueError('Must specify channel 1 RX and TX signals when channel 1 is enabled')

		# DCU SerDes Client Interface
		self.sci = DCUInterface()

		# DCU
		self.p_bus8bit_sel        = '0b0'   # 8-bit/10-bit bus selection
		self.p_dco_calib_time_sel = '0b0'   # 24 cycle DCO Calibration delay
		self.p_isetlos            = '0d0'   # Ios Curren setting
		self.p_req_iset           = '0b000' # 100% equalizer tail current

		if self.speed == LinkSpeed.LS2_5:
			self.p_pd_iset            = '0b00' # 100% PD current
			self.p_seticonst_aux      = '0b00' # 50uA Constant current reference (AUX)
			self.p_seticonst_ch       = '0b00' # 50uA Constant current reference (CHAN)
			self.p_setirpoly_aux      = '0b00' # 50uA Poly current reference (AUX)
			self.p_setirpoly_ch       = '0b00' # 50uA Poly current reference (CHAN)
		else:
			self.p_pd_iset            = '0b11' # 120% PD current
			self.p_seticonst_aux      = '0b01' # 60uA Constant current reference (AUX)
			self.p_seticonst_ch       = '0b10' # 65uA Constant current reference (CHAN)
			self.p_setirpoly_aux      = '0b10' # 65uA Poly current reference (AUX)
			self.p_setirpoly_ch       = '0b10' # 65uA Poly current reference (CHAN)


		# DCU - Power
		self.i_ffc_macropdb = Const(1) # Global macrocell power-down control (DCU + Aux + PLL)
		self.p_ib_pwdnb     = '0b1'    # RX power-down control
		self.p_macropdb     = '0b1'    # Default macrocell power-down (DCU + Aux + PLL)
		self.p_txpll_pwdnb  = '0b1'    # Default TX PLL power down control

		# DCU - Reset
		self.i_ffc_dual_rst    = Signal() # Async Global DCU reset
		self.i_ffc_macro_rst   = Signal() # Async DCU macrocell reset (gated by `FPGA_RESET_ENABLE`)
		self.i_ffc_sync_toggle = Signal() # Serializer reset (rising-edge)
		self.i_ffc_trst        = Signal() # Global DCU TX digital/PLL logic reset
		self.i_scan_reset      = Signal() # Boundary-scan reset?

		# DCU - Clocking
		self.i_refclki            = Signal()           # DCU Input Reference clock
		self.i_sync_nd            = Signal()           # Sync to/from neighbor DCU? (undocumented)
		self.i_txbit_clkn_from_nd = Signal()           # TX bitclk_n from neighbor DCU? (undocumented)
		self.i_txbit_clkp_from_nd = Signal()           # TX bitclk_p from neighbor DCU? (undocumented)
		self.i_txpll_lol_from_nd  = Signal()           # TX PLL Loss-of-Lock from neighbor? (undocumented)
		self.o_ffs_plol           = Signal()           # TX PLL(?) Loss-of-lock
		self.o_sync_pulse2nd      = Signal()           # Sync pulse? to/from neighbor DCU? (undocumented)
		self.o_txbit_clkn_to_nd   = Signal()           # TX bitclk_n to neighbor DCU? (undocumented)
		self.o_txbit_clkp_to_nd   = Signal()           # TX bitclk_p to neighbor DCU? (undocumented)
		self.o_txpll_lol_to_nd    = Signal()           # TX PLL Loss-of-Lock to neighbor? (undocumented)
		self.p_bitclk_from_nd_en  = '0b0'           # Enable bitclock buffer from neighbor DCU's TX PLL AUX
		self.p_bitclk_local_en    = '0b1'           # Enable TX PLL buffer in current AUX
		self.p_bitclk_nd_en       = '0b0'           # Enable bitclock buffer from TX PLL AUX to neighbor DCU
		self.p_cdr_lol_set        = Const(0)           # CDR Loss-of-lock setting (±1500;±2500;±7000;±450)

		self.p_cmusetbiasi        = '0b00'             # PLL/VCO Tuning (undocumented)
		self.p_cmuseti4cpz        = '0d3'              # PLL/VCO Tuning (undocumented)
		self.p_cmuseti4vco        = '0b00'             # PLL/VCO Tuning (undocumented)
		self.p_cmuseticp4p        = '0b01'             # PLL/VCO Tuning (undocumented)
		self.p_cmuseticp4z        = '0b101'            # PLL/VCO Tuning (undocumented)
		self.p_cmusetinitvct      = '0b00'             # PLL/VCO Tuning (undocumented)
		self.p_cmusetiscl4vco     = '0b000'            # PLL/VCO Tuning (undocumented)
		self.p_cmusetp1gm         = '0b000'            # PLL/VCO Tuning (undocumented)
		self.p_cmusetp2agm        = '0b000'            # PLL/VCO Tuning (undocumented)

		if self.speed == LinkSpeed.LS2_5:
			self.p_cmusetzgm          = '0b000'           # PLL/VCO Tuning (undocumented)
			self.p_cmuseti4cpp        = '0d3'            # PLL/VCO Tuning (undocumented)

		else:
			self.p_cmusetzgm          = '0b100'           # PLL/VCO Tuning (undocumented)
			self.p_cmuseti4cpp        = '0d4'            # PLL/VCO Tuning (undocumented)


		self.p_pll_lol_set        = Const(0)           #
		self.p_refck_mode         = '0b100'            # Bit clock multiplier
		self.p_rg_en              = Const(0)           #
		self.p_rg_set             = Const(0)           #
		self.p_setpllrc           = '0d1'              # TX PLL R-C filter configuration
		self.p_sync_local_en      = '0b1'              # Enable Sync for intra-DCU TX channels
		self.p_sync_nd_en         = '0b0'              # Enable TX sync buffer to neighbor DCU TX channels
		self.p_tx_max_rate        = f'{self.speed:1f}' # Max transmit datarate
		self.p_tx_vco_ck_div      = '0b000'            # TX VCO Diviser (1)
		# DCU - FIFO
		self.p_high_mark          = '0d4'        # Clock-compensation FIFO high watermark
		self.p_low_mark           = '0d12'       # Clock-compensation FIFO low watermark

		# DCU - Unknown
		self.i_cin                = Signal(12) # Undocumented "test"
		self.i_cyawstn            = Signal()   # Undocumented "test"
		self.i_scan_enable        = Signal()   # Undocumented "test"
		self.i_scan_in            = Signal(8)  # Undocumented "test"
		self.i_scan_mode          = Signal()   # Undocumented "test"
		self.o_cout               = Signal(20) # Undocumented "test"
		self.o_scan_out           = Signal(8)  # Undocumented "test"

		# DCU Channel 0
		self.i_ch0_ffc_ei_en          = Signal()   # Force rransciver electrical idle control
		self.i_ch0_ffc_enable_cgalign = Signal()   # Enable transciver comma aligner
		self.i_ch0_ffc_fb_loopback    = Signal()   # FPGA bridge RX-TX loopback
		self.i_ch0_ffc_pcie_ct        = Signal()   # Request treansciver to do far-side PCIe receiver detection
		self.i_ch0_ffc_pcie_det_en    = Signal()   # Enable transciver PCIe receiver detection
		self.i_ch0_ffc_pfifo_clr      = Signal()   # Clear SerDes bridge RX-TX parallel loopback FIFO
		self.i_ch0_ffc_sb_pfifo_lp    = Signal()   # SerDes bridge RX-TX parallel loopback
		self.i_ch0_ffc_signal_detect  = Signal()   # Signal detected
		self.i_ch0_hdinn              = Signal()   # Transciver RX input N
		self.i_ch0_hdinp              = Signal()   # Transciver RX input P
		self.o_ch0_ffs_ls_sync_status = Signal()   # Comma syncronization status
		self.o_ch0_ffs_pcie_con       = Signal()   # Result of far-end PCIe receivver detection
		self.o_ch0_ffs_pcie_done      = Signal()   # Far-end PCIe recevier detection completed
		self.o_ch0_ffs_skp_added      = Signal()   # Transciver CTC added a `SKP` character
		self.o_ch0_ffs_skp_deleted    = Signal()   # Transciver CTC removed a `SKP` character
		self.o_ch0_hdoutn             = Signal()   # Transciver TX output N
		self.o_ch0_hdoutp             = Signal()   # Transciver TX output P

		# TODO(aki): Do we want to fully recalibrate the CDR on loss-of-lock?
		self.p_ch0_auto_calib_en      = '0b0'   # (DCO?) Slow calibration - Full
		self.p_ch0_auto_facq_en       = '0b0'   # (DCO?) Fast calibration - Frequency only

		self.p_ch0_band_threshold     = '0d0' # Equalization band thresholding? (undocumented)

		if self.speed == LinkSpeed.LS2_5:
			self.p_ch0_calib_ck_mode      = '0b0' # DCO Calibration clock mode (div/2;bypass)
		else:
			self.p_ch0_calib_ck_mode      = '0b1' # DCO Calibration clock mode (div/2;bypass)


		self.p_ch0_cc_match_1         = '0x1BC'   # Skip character 1
		self.p_ch0_cc_match_2         = '0x11C'   # Skip character 2
		self.p_ch0_cc_match_3         = '0x11C'   # Skip character 3
		self.p_ch0_cc_match_4         = '0x11C'   # Skip character 4
		self.p_ch0_cdr_cnt4sel        = '0b0'   # CDR count(?) 4-bit selection?
		self.p_ch0_cdr_cnt8sel        = '0b0'   # CDR count(?) 8-bit selection?
		self.p_ch0_cdr_max_rate       = Const(0)   # Max input data rate for CDR? (undocumented)
		self.p_ch0_ctc_bypass         = '0b1'  # Bypass clock-tolerance compensation

		self.p_ch0_dcoatdcfg          = '0b0'   # DCO Tuning? (undocumented)
		self.p_ch0_dcoatddly          = '0b0'   # DCO Tuning? (undocumented)
		self.p_ch0_dcobypsatd         = '0b1'   # DCO Tuning? (undocumented)
		self.p_ch0_dcoitune           = '0b00'  # DCO Tuning? (undocumented)
		self.p_ch0_dcoiupdnx2         = '0b1'   # DCO Tuning? (undocumented)
		self.p_ch0_dconuoflsb         = '0b101' # DCO Tuning? (undocumented)

		if self.speed == LinkSpeed.LS2_5:
			self.p_ch0_dcocaldiv          = '0b001' # DCO Tuning? (undocumented)
			self.p_ch0_dcoctlgi           = '0b010' # DCO Tuning? (undocumented)
			self.p_ch0_dcodisbdavoid      = '0b0'   # DCO Tuning? (undocumented)
			self.p_ch0_dcofltdac          = '0b01'  # DCO Tuning? (undocumented)
			self.p_ch0_dcoftnrg           = '0b111' # DCO Tuning? (undocumented)
			self.p_ch0_dcoiostune         = '0b000' # DCO Tuning? (undocumented)
			self.p_ch0_dcoitune4lsb       = '0b111' # DCO Tuning? (undocumented)
			self.p_ch0_dcoscalei          = '0b00'  # DCO Tuning? (undocumented)
			self.p_ch0_dcostartval        = '0b000' # DCO Tuning? (undocumented)
			self.p_ch0_dcostep            = '0b00'  # DCO Tuning? (undocumented)
		else:
			self.p_ch0_dcocaldiv          = '0b010' # DCO Tuning? (undocumented)
			self.p_ch0_dcoctlgi           = '0b011' # DCO Tuning? (undocumented)
			self.p_ch0_dcodisbdavoid      = '0b1'   # DCO Tuning? (undocumented)
			self.p_ch0_dcofltdac          = '0b00'  # DCO Tuning? (undocumented)
			self.p_ch0_dcoftnrg           = '0b001' # DCO Tuning? (undocumented)
			self.p_ch0_dcoiostune         = '0b010' # DCO Tuning? (undocumented)
			self.p_ch0_dcoitune4lsb       = '0b010' # DCO Tuning? (undocumented)
			self.p_ch0_dcoscalei          = '0b01'  # DCO Tuning? (undocumented)
			self.p_ch0_dcostartval        = '0b010' # DCO Tuning? (undocumented)
			self.p_ch0_dcostep            = '0b11'  # DCO Tuning? (undocumented)


		self.p_ch0_dec_bypass         = '0b0'  # Bypass channel 8b10b decoder
		self.p_ch0_enable_cg_align    = '0b1'   # Continuous comma alignment (only if `UC_MODE` is enabled)
		self.p_ch0_enc_bypass         = '0b0'  # Bypass channel 8b10b endocer
		self.p_ch0_ge_an_enable       = '0b0'  # Gigabit Ethernet auto negotiation
		self.p_ch0_lsm_disable        = '0b0'   # Disable RX link state machine
		self.p_ch0_match_2_enable     = '0b0'   # Enable 2-character skip match (`CC_MATCH[4:3]`)
		self.p_ch0_match_4_enable     = '0b1'   # Enable 4-character skip match (`CC_MATCH[4:1]`)
		self.p_ch0_min_ipg_cnt        = '0b11'   # Minimum IPG (Inter-period gap?) to enforce
		# XXX(aki): The lattice tools set this to 0???
		self.p_ch0_pcie_ei_en         = '0b0'   # Enable PCIe electrical idle
		self.p_ch0_pcie_mode          = '0b1'   # PCIe mode
		self.p_ch0_pcs_det_time_sel   = '0b0'   # Connection detection time (8us;2us;4us;16us)
		self.p_ch0_pden_sel           = Const(0)   # Disable CDR phase-detector on electrical idle
		self.p_ch0_prbs_enable        = '0b0'   # PRBS Test machinery? (undocumented)
		self.p_ch0_prbs_lock          = '0b0'   # PRBS Test machinery? (undocumented)
		self.p_ch0_prbs_selection     = '0b0'    # PRBS Test machinery? (undocumented)
		self.p_ch0_protocol           = 'PCIE'   # Channel protocol

		self.p_ch0_reg_band_offset    = '0d0' # DCO band offset control
		self.p_ch0_reg_band_sel       = '0d0' # DCO bad selection (0-63 when `AUTO_CALIB_EN`)
		self.p_ch0_reg_idac_en        = '0b0' # Manual current DAC enable
		self.p_ch0_reg_idac_sel       = '0d0' # Manual current DAC selection (0-1023 when `REG_IDAC_EN`)

		self.p_ch0_rio_mode           = '0b0'   # Rapid-IO Mode
		self.p_ch0_rpwdnb             = '0b1'   # Channel RX power-down
		self.p_ch0_tpwdnb             = '0b1'   # Channel TX power-down
		self.p_ch0_uc_mode            = '0b0'   # User-configured mode
		self.p_ch0_udf_comma_a        = '0x283'   # 8b10b comma A
		self.p_ch0_udf_comma_b        = '0x17C'   # 8b10b comma B
		self.p_ch0_udf_comma_mask     = '0x3FF'   # 8b10b comma mask
		self.p_ch0_wa_bypass          = '0b0'   # Bypass word aligner
		self.p_ch0_wa_mode            = '0b0'   # Barell-shifter or Bitslip alignment mode

		# DCU Channle 0 - TX
		self.i_ch0_ff_tx_d            = Signal(24) # TX FIFO Data
		self.i_ch0_ff_txi_clk         = Signal()   # TX Rerfernce clock input from FPGA fabric
		self.i_ch0_ffc_div11_mode_tx  = Signal()   # Enable DIV/11 TX rate
		self.i_ch0_ffc_lane_tx_rst    = Signal()   # Async reset for DCU TX logic only
		self.i_ch0_ffc_ldr_core2tx_en = Signal()   # Enable low-data-rate TX serial path
		self.i_ch0_ffc_rate_mode_tx   = Signal()   # TX data-rate div/2
		self.i_ch0_ffc_tx_gear_mode   = Signal()   # 2:1 TX gearing mode
		self.i_ch0_ffc_txpwdnb        = Signal()   # TX power-down
		self.i_ch0_ldr_core2tx        = Signal()   # Single-ended low-data-rate input from FPGA fabric to TX
		self.o_ch0_ff_tx_f_clk        = Signal()   # TX clock
		self.o_ch0_ff_tx_h_clk        = Signal()   # DIV/2 TX clock
		self.o_ch0_ff_tx_pclk         = Signal()   # Primary TX clock (DIV/2 when 2:1 gearing)
		self.o_ch0_ffs_txfbfifo_error = Signal()   # TX FPGA bridge FIFO error
		self.p_ch0_ff_tx_f_clk_dis    = Const(0)   # Disable `FF_TX_F_CLK`
		self.p_ch0_ff_tx_h_clk_en     = Const(0)   # Enable `FF_TX_H_CLK`
		self.p_ch0_invert_tx          = '0b1' if self.ch0_invert_tx else '0b0'    # Invert channel TX P/N IO pair
		self.p_ch0_ldr_core2tx_sel    = Const(0)   # Enable low-speed TX out-of-bound signal to SerDes
		self.p_ch0_rate_mode_tx       = '0b0'   # Default TX data-rate div/2 mode
		self.p_ch0_rterm_tx           = '0d19'   # Output Termination  (0:5k;4:75;19:50; Disabled for PCIe)
		self.p_ch0_sb_bypass          = '0b0'  # Bypass SerDes TX bridge (actually neded to invert tx?)
		self.p_ch0_tdrv_dat_sel       = Const(0)   # TX driver output selection (seralizer;dr clock;loopback (data if `r2t_dat_en`, clk if `r2t_ck_en`);equalized-lb iff `eq2t_en`)
		self.p_ch0_tdrv_post_en       = Const(0)   # Enable TX post-emphasis
		self.p_ch0_tdrv_pre_en        = Const(0)   # Enable TX pre-emphasis
		self.p_ch0_tdrv_slice0_cur    = Const(0)   # TX driver slice 0 current (100uA;200uA;300uA;400uA;500uA;600uA;700uA;800uA) (100uA~=100mV swing)
		self.p_ch0_tdrv_slice0_sel    = Const(0)   # TX driver slice 0 select (power-down;main-data;pre-data;post-data)
		self.p_ch0_tdrv_slice1_cur    = Const(0)   # TX driver slice 1 current (100uA;200uA;300uA;400uA;500uA;600uA;700uA;800uA) (100uA~=100mV swing)
		self.p_ch0_tdrv_slice1_sel    = Const(0)   # TX driver slice 1 select (power-down;main-data;pre-data;post-data)
		self.p_ch0_tdrv_slice2_cur    = Const(0)   # TX driver slice 2 current (0uA;900uA;1800uA;2700uA) (100uA~=100mV swing)
		self.p_ch0_tdrv_slice2_sel    = Const(0)   # TX driver slice 2 select (power-down;main-data;pre-data;post-data)
		self.p_ch0_tdrv_slice3_cur    = Const(0)   # TX driver slice 3 current (0uA;900uA;1800uA;2700uA) (100uA~=100mV swing)
		self.p_ch0_tdrv_slice3_sel    = Const(0)   # TX driver slice 3 select (power-down;main-data;pre-data;post-data)
		self.p_ch0_tdrv_slice4_cur    = Const(0)   # TX driver slice 4 current (tbd)
		self.p_ch0_tdrv_slice4_sel    = Const(0)   # TX driver slice 4 select (power-down;main-data;pre-data;post-data)
		self.p_ch0_tdrv_slice5_cur    = Const(0)   # TX driver slice 5 current (tbd)
		self.p_ch0_tdrv_slice5_sel    = Const(0)   # TX driver slice 5 select (power-down;main-data;pre-data;post-data)
		self.p_ch0_tx_cm_sel          = '0b1'   # TX Common-mode voltage (pd;0v6;0v55;0v5)
		self.p_ch0_tx_div11_sel       = Const(0)   # Enable TX Divide-by-11 (standard SMPTE)
		self.p_ch0_tx_gear_bypass     = '0b0'   # Bypass TX gearbox
		# XXX(aki): Should be set to 1 in 16/20-bit bus mode
		self.p_ch0_tx_gear_mode       = '0b0'   # Default 2:1 TX gearing mode
		self.p_ch0_tx_post_sign       = Const(0)   # TX post-emphasis inversion
		self.p_ch0_tx_pre_sign        = Const(0)   # TX pre-emphasis inversion
		self.p_ch0_txamplitude        = Const(0)   # Power calibaration for TX Amplitude? (undocumented)
		self.p_ch0_txdepost           = Const(0)   # Power calibaration for TX pre-emphesis? (undocumented)
		self.p_ch0_txdepre            = Const(0)   # Power calibaration for TX post-emphesis? (undocumented)

		# DCU Channel 0 - RX
		self.i_ch0_ff_ebrd_clk        = Signal()   # RX CTC FIFO clock from FPGA fabric
		self.i_ch0_ff_rxi_clk         = Signal()   # RX Reference clock input from FPGA fabric
		self.i_ch0_ffc_cdr_en_bitslip = Signal()   # Enable CDR bitlip? (undocumented)
		self.i_ch0_ffc_div11_mode_rx  = Signal()   # Enable DIV/11 RX rate
		self.i_ch0_ffc_lane_rx_rst    = Signal()   # Async reset for DCU RX logic only
		self.i_ch0_ffc_rate_mode_rx   = Signal()   # RX data-rate div/2
		self.i_ch0_ffc_rrst           = Signal()   # RX Digital logic reset
		self.i_ch0_ffc_rx_gear_mode   = Signal()   # RX 2:1 gearing mode
		self.i_ch0_ffc_rxpwdnb        = Signal()   # RX power-down
		self.i_ch0_ffc_sb_inv_rx      = Signal()   # Invert recieived data
		self.i_ch0_rx_refclk          = Signal()   # RX CDR Reference clock input
		self.o_ch0_ff_rx_d            = Signal(24) # RX FIFO data
		self.o_ch0_ff_rx_f_clk        = Signal()   # Recovered clock from RX CDR
		self.o_ch0_ff_rx_h_clk        = Signal()   # DIV/2 recovered clock from RX CDR
		self.o_ch0_ff_rx_pclk         = Signal()   # Recovered RX primary clock (DIV/2 when 2:1 gearing)
		self.o_ch0_ffs_cc_overrun     = Signal()   # RX Clock compensator FIFO overrun error
		self.o_ch0_ffs_cc_underrun    = Signal()   # RX Clock compensator FIFO underrun error
		self.o_ch0_ffs_rlol           = Signal()   # RX CDR loss-of-lock
		self.o_ch0_ffs_rlos           = Signal()   # RX Loss-of-signal
		self.o_ch0_ffs_rxfbfifo_error = Signal()   # RX FPBA bridge FIFO error
		self.o_ch0_ldr_rx2core        = Signal()   # Single-ended low-data-rate output from RX to FPGA fabric
		self.p_ch0_ff_rx_f_clk_dis    = Const(0)   # Disable `FF_RX_F_CLK`
		self.p_ch0_ff_rx_h_clk_en     = Const(0)   # Enable `FF_RX_H_CLK`
		self.p_ch0_invert_rx          = '0b1' if self.ch0_invert_rx else '0b0' # Invert channel RX P/N IO pair
		self.p_ch0_ldr_rx2core_sel    = Const(0)   # Enable RX out-of-band input from SerDes boundary scan
		self.p_ch0_leq_offset_sel     = Const(0)   # RX common-mode DC voltage offset cancellation (n-side;p-side)
		self.p_ch0_leq_offset_trim    = Const(0)   # RX offset cancellation current trim (tbd)
		self.p_ch0_rate_mode_rx       = Const(0)   # Default RX data-rate div/2 mode
		self.p_ch0_rcv_dcc_en         = '0b0'   # RC DC coupling
		self.p_ch0_req_en             = Const(0)   # Enable RX equalization
		self.p_ch0_req_lvl_set        = Const(0)   # RX equalization level (6bB;9dB;12dB)
		self.p_ch0_rlos_sel           = Const(0)   # Set RX Loss-of-signal output to control the CDR phase-detector
		self.p_ch0_rterm_rx           = Const(0)   # Input Termination (0:5k;6:75;11:60;22:50)
		self.p_ch0_rx_dco_ck_div      = '0b000'   # RX VCO Divider (00x:1;01x:2;100:4;101:8;110:16;111:32)
		self.p_ch0_rx_div11_sel       = Const(0)   # Enable RX Divide-by-11 (standard SMPTE)
		self.p_ch0_rx_gear_bypass     = Const(0)   # Bypass RX gearbox
		# XXX(aki): Should be set to 1 in 16/20-bit bus mode
		self.p_ch0_rx_gear_mode       = '0b0'   # Default 2:1 RX gearing mode
		self.p_ch0_rx_los_ceq         = Const(0)   # RX equialization value at Loss-of-signal detector input
		self.p_ch0_rx_los_en          = Const(0)   # Enable RX Loss-of-signal detection
		self.p_ch0_rx_los_hyst_en     = Const(0)   # Enable RX Loss-of-signal hysterisis in threshold level
		self.p_ch0_rx_los_lvl         = Const(0)   # RX Loss-of-signal threshold in mV (30;50;70;90;120;140;160;180)
		self.p_ch0_rx_rate_sel        = '0d8'      # RX equalizer pole position (high;med;low)
		self.p_ch0_rx_sb_bypass       = '0b0'  # Bypass SerDes RX bridge (actually needed to invert RX?)
		self.p_ch0_rxin_cm            = Const(0)   # RX common-mode voltage for equalizer input in AC mode (0v8)
		self.p_ch0_rxterm_cm          = Const(0)   # RX common-mode voltage (supply;floating;0v;0v)
		self.p_ch0_sel_sd_rx_clk      = Const(0)   # RX fb_clk source CDR/FIFO clock selection ('0b1' iff usng CTC)

		# DCU Channel 1
		self.i_ch1_ffc_ei_en          = Signal()   # Force rransciver electrical idle control
		self.i_ch1_ffc_enable_cgalign = Signal()   # Enable transciver comma aligner
		self.i_ch1_ffc_fb_loopback    = Signal()   # FPGA bridge RX-TX loopback
		self.i_ch1_ffc_pcie_ct        = Signal()   # Request treansciver to do far-side PCIe receiver detection
		self.i_ch1_ffc_pcie_det_en    = Signal()   # Enable transciver PCIe receiver detection
		self.i_ch1_ffc_pfifo_clr      = Signal()   # Clear SerDes bridge RX-TX parallel loopback FIFO
		self.i_ch1_ffc_sb_pfifo_lp    = Signal()   # SerDes bridge RX-TX parallel loopback
		self.i_ch1_ffc_signal_detect  = Signal()   # Signal detected
		self.i_ch1_hdinn              = Signal()   # Transciver RX input N
		self.i_ch1_hdinp              = Signal()   # Transciver RX input P
		self.o_ch1_ffs_ls_sync_status = Signal()   # Comma syncronization status
		self.o_ch1_ffs_pcie_con       = Signal()   # Result of far-end PCIe receivver detection
		self.o_ch1_ffs_pcie_done      = Signal()   # Far-end PCIe recevier detection completed
		self.o_ch1_ffs_skp_added      = Signal()   # Transciver CTC added a `SKP` character
		self.o_ch1_ffs_skp_deleted    = Signal()   # Transciver CTC removed a `SKP` character
		self.o_ch1_hdoutn             = Signal()   # Transciver TX output N
		self.o_ch1_hdoutp             = Signal()   # Transciver TX output P
		self.p_ch1_auto_calib_en      = Const(0)   # (DCO?) Slow calibraiton - Full
		self.p_ch1_auto_facq_en       = Const(0)   # (DCO?) Fast calibration - Frquency only
		self.p_ch1_band_threshold     = Const(0)   # Equalization band thresholding? (undocumented)
		self.p_ch1_calib_ck_mode      = Const(0)   # DCO Calibration clock mode (div/2;bypass)
		self.p_ch1_cc_match_1         = Const(0)   # Skip character 1
		self.p_ch1_cc_match_2         = Const(0)   # Skip character 2
		self.p_ch1_cc_match_3         = Const(0)   # Skip character 3
		self.p_ch1_cc_match_4         = Const(0)   # Skip character 4
		self.p_ch1_cdr_cnt4sel        = Const(0)   # CDR count(?) 4-bit selection?
		self.p_ch1_cdr_cnt8sel        = Const(0)   # CDR count(?) 8-bit selection?
		self.p_ch1_cdr_max_rate       = Const(0)   # Max input data rate for CDR? (undocumented)
		self.p_ch1_ctc_bypass         = Const(0)   # Bypass clock-tolerance compensation
		self.p_ch1_dcoatdcfg          = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoatddly          = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcobypsatd         = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcocaldiv          = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoctlgi           = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcodisbdavoid      = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcofltdac          = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoftnrg           = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoiostune         = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoitune           = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoitune4lsb       = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoiupdnx2         = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dconuoflsb         = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcoscalei          = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcostartval        = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dcostep            = Const(0)   # DCO Tuning? (undocumented)
		self.p_ch1_dec_bypass         = Const(0)   # Bypass channel 8b10b decoder
		self.p_ch1_enable_cg_align    = Const(0)   # Continuous comma alignment (only if `UC_MODE` is enabled)
		self.p_ch1_enc_bypass         = Const(0)   # Bypass channel 8b10b endocer
		self.p_ch1_ge_an_enable       = Const(0)   # Gigabit Ethernet auto negotiation
		self.p_ch1_lsm_disable        = Const(0)   # Disable RX link state machine
		self.p_ch1_match_2_enable     = Const(0)   # Enable 2-character skip match (`CC_MATCH[4:3]`)
		self.p_ch1_match_4_enable     = Const(0)   # Enable 4-character skip match (`CC_MATCH[4:1]`)
		self.p_ch1_min_ipg_cnt        = Const(0)   # Minimum IPG (Inter-period gap?) to enforce
		self.p_ch1_pcie_ei_en         = Const(0)   # Enable PCIe electrical idle
		self.p_ch1_pcie_mode          = Const(0)   # PCIe mode
		self.p_ch1_pcs_det_time_sel   = Const(0)   # Connection detection time (8us;2us;4us;16us)
		self.p_ch1_pden_sel           = Const(0)   # Disable CDR phase-detector on electrical idle
		self.p_ch1_prbs_enable        = Const(0)   # PRBS Test machinery? (undocumented)
		self.p_ch1_prbs_lock          = Const(0)   # PRBS Test machinery? (undocumented)
		self.p_ch1_prbs_selection     = Const(0)   # PRBS Test machinery? (undocumented)
		self.p_ch1_protocol           = Const(0)   # Channel protocol
		self.p_ch1_reg_band_offset    = Const(0)   # DCO band offset control
		self.p_ch1_reg_band_sel       = Const(0)   # DCO bad selection (0-63 when `AUTO_CALIB_EN`)
		self.p_ch1_reg_idac_en        = Const(0)   # Manual current DAC enable
		self.p_ch1_reg_idac_sel       = Const(0)   # Manual current DAC selection (0-1023 when `REG_IDAC_EN`)
		self.p_ch1_rio_mode           = Const(0)   # Rapid-IO Mode
		self.p_ch1_rpwdnb             = Const(0)   # Channel RX power-down
		self.p_ch1_tpwdnb             = Const(0)   # Channel TX power-down
		self.p_ch1_uc_mode            = Const(0)   # User-configured mode
		self.p_ch1_udf_comma_a        = Const(0)   # 8b10b comma A
		self.p_ch1_udf_comma_b        = Const(0)   # 8b10b comma B
		self.p_ch1_udf_comma_mask     = Const(0)   # 8b10b comma mask
		self.p_ch1_wa_bypass          = Const(0)  # Bypass word aligner
		self.p_ch1_wa_mode            = Const(0)   # Barell-shifter or Bitslip alignment mode

		# DCU Channle 1 - TX
		self.i_ch1_ff_tx_d            = Signal(24) # TX FIFO Data
		self.i_ch1_ff_txi_clk         = Signal()   # TX Rerfernce clock input from FPGA fabric
		self.i_ch1_ffc_div11_mode_tx  = Signal()   # Enable DIV/11 TX rate
		self.i_ch1_ffc_lane_tx_rst    = Signal()   # Async reset for DCU TX logic only
		self.i_ch1_ffc_ldr_core2tx_en = Signal()   # Enable low-data-rate TX serial path
		self.i_ch1_ffc_rate_mode_tx   = Signal()   # TX data-rate div/2
		self.i_ch1_ffc_tx_gear_mode   = Signal()   # 2:1 TX gearing mode
		self.i_ch1_ffc_txpwdnb        = Signal()   # TX power-down
		self.i_ch1_ldr_core2tx        = Signal()   # Single-ended low-data-rate input from FPGA fabric to TX
		self.o_ch1_ff_tx_f_clk        = Signal()   # TX clock
		self.o_ch1_ff_tx_h_clk        = Signal()   # DIV/2 TX clock
		self.o_ch1_ff_tx_pclk         = Signal()   # Primary TX clock (DIV/2 when 2:1 gearing)
		self.o_ch1_ffs_txfbfifo_error = Signal()   # TX FPGA bridge FIFO error
		self.p_ch1_ff_tx_f_clk_dis    = Const(0)   # Disable `FF_TX_F_CLK`
		self.p_ch1_ff_tx_h_clk_en     = Const(0)   # Enable `FF_TX_H_CLK`
		self.p_ch1_invert_tx          = Const(0)   # Invert channel TX P/N IO pair
		self.p_ch1_ldr_core2tx_sel    = Const(0)   # Enable low-speed TX out-of-bound signal to SerDes
		self.p_ch1_rate_mode_tx       = Const(0)   # Default TX data-rate div/2 mode
		self.p_ch1_rterm_tx           = Const(0)   # Output Termination  (0:5k;4:75;19:50; Disabled for PCIe)
		self.p_ch1_sb_bypass          = Const(0)   # Bypass SerDes TX bridge (actually neded to invert tx?)
		self.p_ch1_tdrv_dat_sel       = Const(0)   # TX driver output selection (seralizer;dr clock;loopback (data if `r2t_dat_en`, clk if `r2t_ck_en`);equalized-lb iff `eq2t_en`)
		self.p_ch1_tdrv_post_en       = Const(0)   # Enable TX post-emphasis
		self.p_ch1_tdrv_pre_en        = Const(0)   # Enable TX pre-emphasis
		self.p_ch1_tdrv_slice0_cur    = Const(0)   # TX driver slice 0 current (100uA;200uA;300uA;400uA;500uA;600uA;700uA;800uA) (100uA~=100mV swing)
		self.p_ch1_tdrv_slice0_sel    = Const(0)   # TX driver slice 0 select (power-down;main-data;pre-data;post-data)
		self.p_ch1_tdrv_slice1_cur    = Const(0)   # TX driver slice 1 current (100uA;200uA;300uA;400uA;500uA;600uA;700uA;800uA) (100uA~=100mV swing)
		self.p_ch1_tdrv_slice1_sel    = Const(0)   # TX driver slice 1 select (power-down;main-data;pre-data;post-data)
		self.p_ch1_tdrv_slice2_cur    = Const(0)   # TX driver slice 2 current (0uA;900uA;1800uA;2700uA) (100uA~=100mV swing)
		self.p_ch1_tdrv_slice2_sel    = Const(0)   # TX driver slice 2 select (power-down;main-data;pre-data;post-data)
		self.p_ch1_tdrv_slice3_cur    = Const(0)   # TX driver slice 3 current (0uA;900uA;1800uA;2700uA) (100uA~=100mV swing)
		self.p_ch1_tdrv_slice3_sel    = Const(0)   # TX driver slice 3 select (power-down;main-data;pre-data;post-data)
		self.p_ch1_tdrv_slice4_cur    = Const(0)   # TX driver slice 4 current (tbd)
		self.p_ch1_tdrv_slice4_sel    = Const(0)   # TX driver slice 4 select (power-down;main-data;pre-data;post-data)
		self.p_ch1_tdrv_slice5_cur    = Const(0)   # TX driver slice 5 current (tbd)
		self.p_ch1_tdrv_slice5_sel    = Const(0)   # TX driver slice 5 select (power-down;main-data;pre-data;post-data)
		self.p_ch1_tx_cm_sel          = Const(0)   # TX Common-mode voltage (pd;0v6;0v55;0v5)
		self.p_ch1_tx_div11_sel       = Const(0)   # Enable TX Divide-by-11 (standard SMPTE)
		self.p_ch1_tx_gear_bypass     = Const(0)   # Bypass TX gearbox
		self.p_ch1_tx_gear_mode       = Const(0)   # Default 2:1 TX gearing mode
		self.p_ch1_tx_post_sign       = Const(0)   # TX post-emphasis inversion
		self.p_ch1_tx_pre_sign        = Const(0)   # TX pre-emphasis inversion
		self.p_ch1_txamplitude        = Const(0)   # Power calibaration for TX Amplitude? (undocumented)
		self.p_ch1_txdepost           = Const(0)   # Power calibaration for TX pre-emphesis? (undocumented)
		self.p_ch1_txdepre            = Const(0)   # Power calibaration for TX post-emphesis? (undocumented)

		# DCU Channel 1 - RX
		self.i_ch1_ff_ebrd_clk        = Signal()   # RX CTC FIFO clock from FPGA fabric
		self.i_ch1_ff_rxi_clk         = Signal()   # RX Reference clock input from FPGA fabric
		self.i_ch1_ffc_cdr_en_bitslip = Signal()   # Enable CDR bitlip? (undocumented)
		self.i_ch1_ffc_div11_mode_rx  = Signal()   # Enable DIV/11 RX rate
		self.i_ch1_ffc_lane_rx_rst    = Signal()   # Async reset for DCU RX logic only
		self.i_ch1_ffc_rate_mode_rx   = Signal()   # RX data-rate div/2
		self.i_ch1_ffc_rrst           = Signal()   # RX Digital logic reset
		self.i_ch1_ffc_rx_gear_mode   = Signal()   # RX 2:1 gearing mode
		self.i_ch1_ffc_rxpwdnb        = Signal()   # RX power-down
		self.i_ch1_ffc_sb_inv_rx      = Signal()   # Invert recieived data
		self.i_ch1_rx_refclk          = Signal()   # RX CDR Reference clock input
		self.o_ch1_ff_rx_d            = Signal(24) # RX FIFO data
		self.o_ch1_ff_rx_f_clk        = Signal()   # Recovered clock from RX CDR
		self.o_ch1_ff_rx_h_clk        = Signal()   # DIV/2 recovered clock from RX CDR
		self.o_ch1_ff_rx_pclk         = Signal()   # Recovered RX primary clock (DIV/2 when 2:1 gearing)
		self.o_ch1_ffs_cc_overrun     = Signal()   # RX Clock compensator FIFO overrun error
		self.o_ch1_ffs_cc_underrun    = Signal()   # RX Clock compensator FIFO underrun error
		self.o_ch1_ffs_rlol           = Signal()   # RX CDR loss-of-lock
		self.o_ch1_ffs_rlos           = Signal()   # RX Loss-of-signal
		self.o_ch1_ffs_rxfbfifo_error = Signal()   # RX FPBA bridge FIFO error
		self.o_ch1_ldr_rx2core        = Signal()   # Single-ended low-data-rate output from RX to FPGA fabric
		self.p_ch1_ff_rx_f_clk_dis    = Const(0)   # Disable `FF_RX_F_CLK`
		self.p_ch1_ff_rx_h_clk_en     = Const(0)   # Enable `FF_RX_H_CLK`
		self.p_ch1_invert_rx          = Const(0)   # Invert channel RX P/N IO pair
		self.p_ch1_ldr_rx2core_sel    = Const(0)   # Enable RX out-of-band input from SerDes boundary scan
		self.p_ch1_leq_offset_sel     = Const(0)   # RX common-mode DC voltage offset cancellation (n-side;p-side)
		self.p_ch1_leq_offset_trim    = Const(0)   # RX offset cancellation current trim (tbd)
		self.p_ch1_rate_mode_rx       = Const(0)   # Default RX data-rate div/2 mode
		self.p_ch1_rcv_dcc_en         = Const(0)   # RC DC coupling
		self.p_ch1_req_en             = Const(0)   # Enable RX equalization
		self.p_ch1_req_lvl_set        = Const(0)   # RX equalization level (6bB;9dB;12dB)
		self.p_ch1_rlos_sel           = Const(0)   # Set RX Loss-of-signal output to control the CDR phase-detector
		self.p_ch1_rterm_rx           = Const(0)   # Input Termination (0:5k;6:75;11:60;22:50)
		self.p_ch1_rx_dco_ck_div      = Const(0)   # RX VCO Divider (00x:1;01x:2;100:4;101:8;110:16;111:32)
		self.p_ch1_rx_div11_sel       = Const(0)   # Enable RX Divide-by-11 (standard SMPTE)
		self.p_ch1_rx_gear_bypass     = Const(0)   # Bypass RX gearbox
		self.p_ch1_rx_gear_mode       = Const(0)   # Default 2:1 RX gearing mode
		self.p_ch1_rx_los_ceq         = Const(0)   # RX equialization value at Loss-of-signal detector input
		self.p_ch1_rx_los_en          = Const(0)   # Enable RX Loss-of-signal detection
		self.p_ch1_rx_los_hyst_en     = Const(0)   # Enable RX Loss-of-signal hysterisis in threshold level
		self.p_ch1_rx_los_lvl         = Const(0)   # RX Loss-of-signal threshold in mV (30;50;70;90;120;140;160;180)
		self.p_ch1_rx_rate_sel        = Const(0)   # RX equalizer pole position (high;med;low)
		self.p_ch1_rx_sb_bypass       = Const(0)   # Bypass SerDes RX bridge (actually needed to invert RX?)
		self.p_ch1_rxin_cm            = Const(0)   # RX common-mode voltage for equalizer input in AC mode (0v8)
		self.p_ch1_rxterm_cm          = Const(0)   # RX common-mode voltage (supply;floating;0v;0v)
		self.p_ch1_sel_sd_rx_clk      = Const(0)   # RX fb_clk source CDR/FIFO clock selection ('0b1' iff usng CTC)


	def elaborate(self, platform: Platform | None) -> Module:
		m = Module()

		# XXX(aki):
		# There is a soft-reset bug in the ECP5 DCUs, see FPGA-PG-02001
		# https://www.latticesemi.com/view_document?document_id=53318
		# This only really effects the cores from the Lattice tools, but we should
		# ensure that we don't fall into the same trap

		m.submodules.dcu = dcu = Instance(
			'DCUA',
			src_loc    = None,
			src_loc_at = 0,
			# DCU
			p_BUS8BIT_SEL        = self.p_bus8bit_sel,
			p_DCO_CALIB_TIME_SEL = self.p_dco_calib_time_sel,
			p_ISETLOS            = self.p_isetlos,
			p_PD_ISET            = self.p_pd_iset,
			p_REQ_ISET           = self.p_req_iset,
			p_SETICONST_AUX      = self.p_seticonst_aux,
			p_SETICONST_CH       = self.p_seticonst_ch,
			p_SETIRPOLY_AUX      = self.p_setirpoly_aux,
			p_SETIRPOLY_CH       = self.p_setirpoly_ch,
			# DCU - Power
			i_FFC_MACROPDB = self.i_ffc_macropdb,
			p_IB_PWDNB     = self.p_ib_pwdnb,
			p_MACROPDB     = self.p_macropdb,
			p_TXPLL_PWDNB  = self.p_txpll_pwdnb,
			# DCU - Reset
			i_FFC_DUAL_RST    = self.i_ffc_dual_rst,
			i_FFC_MACRO_RST   = self.i_ffc_macro_rst,
			i_FFC_SYNC_TOGGLE = self.i_ffc_sync_toggle,
			i_FFC_TRST        = self.i_ffc_trst,
			i_SCAN_RESET      = self.i_scan_reset,
			# DCU - Clocking
			i_REFCLKI            = self.i_refclki,
			i_SYNC_ND            = self.i_sync_nd,
			i_TXBIT_CLKN_FROM_ND = self.i_txbit_clkn_from_nd,
			i_TXBIT_CLKP_FROM_ND = self.i_txbit_clkp_from_nd,
			i_TXPLL_LOL_FROM_ND  = self.i_txpll_lol_from_nd,
			o_FFS_PLOL           = self.o_ffs_plol,
			o_SYNC_PULSE2ND      = self.o_sync_pulse2nd,
			o_TXBIT_CLKN_TO_ND   = self.o_txbit_clkn_to_nd,
			o_TXBIT_CLKP_TO_ND   = self.o_txbit_clkp_to_nd,
			o_TXPLL_LOL_TO_ND    = self.o_txpll_lol_to_nd,
			p_BITCLK_FROM_ND_EN  = self.p_bitclk_from_nd_en,
			p_BITCLK_LOCAL_EN    = self.p_bitclk_local_en,
			p_BITCLK_ND_EN       = self.p_bitclk_nd_en,
			p_CDR_LOL_SET        = self.p_cdr_lol_set,
			p_CMUSETBIASI        = self.p_cmusetbiasi,
			p_CMUSETI4CPP        = self.p_cmuseti4cpp,
			p_CMUSETI4CPZ        = self.p_cmuseti4cpz,
			p_CMUSETI4VCO        = self.p_cmuseti4vco,
			p_CMUSETICP4P        = self.p_cmuseticp4p,
			p_CMUSETICP4Z        = self.p_cmuseticp4z,
			p_CMUSETINITVCT      = self.p_cmusetinitvct,
			p_CMUSETISCL4VCO     = self.p_cmusetiscl4vco,
			p_CMUSETP1GM         = self.p_cmusetp1gm,
			p_CMUSETP2AGM        = self.p_cmusetp2agm,
			p_CMUSETZGM          = self.p_cmusetzgm,
			p_PLL_LOL_SET        = self.p_pll_lol_set,
			p_REFCK_MODE         = self.p_refck_mode,
			p_RG_EN              = self.p_rg_en,
			p_RG_SET             = self.p_rg_set,
			p_SETPLLRC           = self.p_setpllrc,
			p_SYNC_LOCAL_EN      = self.p_sync_local_en,
			p_SYNC_ND_EN         = self.p_sync_nd_en,
			p_TX_MAX_RATE        = self.p_tx_max_rate,
			p_TX_VCO_CK_DIV      = self.p_tx_vco_ck_div,
			# DCU - FIFO
			p_HIGH_MARK = self.p_high_mark,
			p_LOW_MARK = self.p_low_mark,
			# DCU - SerDes Client Interface
			i_D_SCISELAUX = self.sci.sci_sel,
			i_D_SCIENAUX  = self.sci.sci_en,
			i_CH0_SCIEN   = self.sci.sci_en_ch0,
			i_CH0_SCISEL  = self.sci.sci_sel_ch0,
			i_CH1_SCIEN   = self.sci.sci_en_ch1,
			i_CH1_SCISEL  = self.sci.sci_sel_ch1,
			o_D_SCIINT    = self.sci.sci_int,
			i_D_SCIWSTN   = self.sci.sci_wrn,
			i_D_SCIRD     = self.sci.sci_rd,
			**{ f'i_D_SCIWDATA{bit}': self.sci.sci_wdata[bit] for bit in range(self.sci.sci_wdata.width) },
			**{ f'o_D_SCIRDATA{bit}': self.sci.sci_rdata[bit] for bit in range(self.sci.sci_rdata.width) },
			**{ f'i_D_SCIADDR{bit}': self.sci.sci_addr[bit] for bit in range(self.sci.sci_addr.width) },
			# DCU - Unknown
			**{ f'i_D_CIN{bit}': self.i_cin[bit] for bit in range(self.i_cin.width) },
			i_CYAWSTN     = self.i_cyawstn,
			i_SCAN_ENABLE = self.i_scan_enable,
			**{ f'i_D_SCAN_IN_{bit}': self.i_scan_in[bit] for bit in range(self.i_scan_in.width) },
			i_SCAN_MODE = self.i_scan_mode,
			**{ f'o_D_COUT{bit}': self.o_cout[bit] for bit in range(self.o_cout.width) },
			**{ f'o_D_SCAN_OUT_{bit}': self.o_scan_out[bit] for bit in range(self.o_scan_out.width) },
			# DCU Channel 0
			i_CH0_FFC_EI_EN          = self.i_ch0_ffc_ei_en,
			i_CH0_FFC_ENABLE_CGALIGN = self.i_ch0_ffc_enable_cgalign,
			i_CH0_FFC_FB_LOOPBACK    = self.i_ch0_ffc_fb_loopback,
			i_CH0_FFC_PCIE_CT        = self.i_ch0_ffc_pcie_ct,
			i_CH0_FFC_PCIE_DET_EN    = self.i_ch0_ffc_pcie_det_en,
			i_CH0_FFC_PFIFO_CLR      = self.i_ch0_ffc_pfifo_clr,
			i_CH0_FFC_SB_PFIFO_LP    = self.i_ch0_ffc_sb_pfifo_lp,
			i_CH0_FFC_SIGNAL_DETECT  = self.i_ch0_ffc_signal_detect,
			i_CH0_HDINN              = self.i_ch0_hdinn,
			i_CH0_HDINP              = self.i_ch0_hdinp,
			o_CH0_FFS_LS_SYNC_STATUS = self.o_ch0_ffs_ls_sync_status,
			o_CH0_FFS_PCIE_CON       = self.o_ch0_ffs_pcie_con,
			o_CH0_FFS_PCIE_DONE      = self.o_ch0_ffs_pcie_done,
			o_CH0_FFS_SKP_ADDED      = self.o_ch0_ffs_skp_added,
			o_CH0_FFS_SKP_DELETED    = self.o_ch0_ffs_skp_deleted,
			o_CH0_HDOUTN             = self.o_ch0_hdoutn,
			o_CH0_HDOUTP             = self.o_ch0_hdoutp,
			p_CH0_AUTO_CALIB_EN      = self.p_ch0_auto_calib_en,
			p_CH0_AUTO_FACQ_EN       = self.p_ch0_auto_facq_en,
			p_CH0_BAND_THRESHOLD     = self.p_ch0_band_threshold,
			p_CH0_CALIB_CK_MODE      = self.p_ch0_calib_ck_mode,
			p_CH0_CC_MATCH_1         = self.p_ch0_cc_match_1,
			p_CH0_CC_MATCH_2         = self.p_ch0_cc_match_2,
			p_CH0_CC_MATCH_3         = self.p_ch0_cc_match_3,
			p_CH0_CC_MATCH_4         = self.p_ch0_cc_match_4,
			p_CH0_CDR_CNT4SEL        = self.p_ch0_cdr_cnt4sel,
			p_CH0_CDR_CNT8SEL        = self.p_ch0_cdr_cnt8sel,
			p_CH0_CDR_MAX_RATE       = self.p_ch0_cdr_max_rate,
			p_CH0_CTC_BYPASS         = self.p_ch0_ctc_bypass,
			p_CH0_DCOATDCFG          = self.p_ch0_dcoatdcfg,
			p_CH0_DCOATDDLY          = self.p_ch0_dcoatddly,
			p_CH0_DCOBYPSATD         = self.p_ch0_dcobypsatd,
			p_CH0_DCOCALDIV          = self.p_ch0_dcocaldiv,
			p_CH0_DCOCTLGI           = self.p_ch0_dcoctlgi,
			p_CH0_DCODISBDAVOID      = self.p_ch0_dcodisbdavoid,
			p_CH0_DCOFLTDAC          = self.p_ch0_dcofltdac,
			p_CH0_DCOFTNRG           = self.p_ch0_dcoftnrg,
			p_CH0_DCOIOSTUNE         = self.p_ch0_dcoiostune,
			p_CH0_DCOITUNE           = self.p_ch0_dcoitune,
			p_CH0_DCOITUNE4LSB       = self.p_ch0_dcoitune4lsb,
			p_CH0_DCOIUPDNX2         = self.p_ch0_dcoiupdnx2,
			p_CH0_DCONUOFLSB         = self.p_ch0_dconuoflsb,
			p_CH0_DCOSCALEI          = self.p_ch0_dcoscalei,
			p_CH0_DCOSTARTVAL        = self.p_ch0_dcostartval,
			p_CH0_DCOSTEP            = self.p_ch0_dcostep,
			p_CH0_DEC_BYPASS         = self.p_ch0_dec_bypass,
			p_CH0_ENABLE_CG_ALIGN    = self.p_ch0_enable_cg_align,
			p_CH0_ENC_BYPASS         = self.p_ch0_enc_bypass,
			p_CH0_GE_AN_ENABLE       = self.p_ch0_ge_an_enable,
			p_CH0_LSM_DISABLE        = self.p_ch0_lsm_disable,
			p_CH0_MATCH_2_ENABLE     = self.p_ch0_match_2_enable,
			p_CH0_MATCH_4_ENABLE     = self.p_ch0_match_4_enable,
			p_CH0_MIN_IPG_CNT        = self.p_ch0_min_ipg_cnt,
			p_CH0_PCIE_EI_EN         = self.p_ch0_pcie_ei_en,
			p_CH0_PCIE_MODE          = self.p_ch0_pcie_mode,
			p_CH0_PCS_DET_TIME_SEL   = self.p_ch0_pcs_det_time_sel,
			p_CH0_PDEN_SEL           = self.p_ch0_pden_sel,
			p_CH0_PRBS_ENABLE        = self.p_ch0_prbs_enable,
			p_CH0_PRBS_LOCK          = self.p_ch0_prbs_lock,
			p_CH0_PRBS_SELECTION     = self.p_ch0_prbs_selection,
			p_CH0_PROTOCOL           = self.p_ch0_protocol,
			p_CH0_REG_BAND_OFFSET    = self.p_ch0_reg_band_offset,
			p_CH0_REG_BAND_SEL       = self.p_ch0_reg_band_sel,
			p_CH0_REG_IDAC_EN        = self.p_ch0_reg_idac_en,
			p_CH0_REG_IDAC_SEL       = self.p_ch0_reg_idac_sel,
			p_CH0_RIO_MODE           = self.p_ch0_rio_mode,
			p_CH0_RPWDNB             = self.p_ch0_rpwdnb,
			p_CH0_TPWDNB             = self.p_ch0_tpwdnb,
			p_CH0_UC_MODE            = self.p_ch0_uc_mode,
			p_CH0_UDF_COMMA_A        = self.p_ch0_udf_comma_a,
			p_CH0_UDF_COMMA_B        = self.p_ch0_udf_comma_b,
			p_CH0_UDF_COMMA_MASK     = self.p_ch0_udf_comma_mask,
			p_CH0_WA_BYPASS          = self.p_ch0_wa_bypass,
			p_CH0_WA_MODE            = self.p_ch0_wa_mode,
			# DCU Channel 0 - TX
			**{ f'i_CH0_FF_TX_D_{bit}': self.i_ch0_ff_tx_d[bit] for bit in range(self.i_ch0_ff_tx_d.width) },
			i_CH0_FF_TXI_CLK         = self.i_ch0_ff_txi_clk,
			i_CH0_FFC_DIV11_MODE_TX  = self.i_ch0_ffc_div11_mode_tx,
			i_CH0_FFC_LANE_TX_RST    = self.i_ch0_ffc_lane_tx_rst,
			i_CH0_FFC_LDR_CORE2TX_EN = self.i_ch0_ffc_ldr_core2tx_en,
			i_CH0_FFC_RATE_MODE_TX   = self.i_ch0_ffc_rate_mode_tx,
			i_CH0_FFC_TX_GEAR_MODE   = self.i_ch0_ffc_tx_gear_mode,
			i_CH0_FFC_TXPWDNB        = self.i_ch0_ffc_txpwdnb,
			i_CH0_LDR_CORE2TX        = self.i_ch0_ldr_core2tx,
			o_CH0_FF_TX_F_CLK        = self.o_ch0_ff_tx_f_clk,
			o_CH0_FF_TX_H_CLK        = self.o_ch0_ff_tx_h_clk,
			o_CH0_FF_TX_PCLK         = self.o_ch0_ff_tx_pclk,
			o_CH0_FFS_TXFBFIFO_ERROR = self.o_ch0_ffs_txfbfifo_error,
			p_CH0_FF_TX_F_CLK_DIS    = self.p_ch0_ff_tx_f_clk_dis,
			p_CH0_FF_TX_H_CLK_EN     = self.p_ch0_ff_tx_h_clk_en,
			p_CH0_INVERT_TX          = self.p_ch0_invert_tx,
			p_CH0_LDR_CORE2TX_SEL    = self.p_ch0_ldr_core2tx_sel,
			p_CH0_RATE_MODE_TX       = self.p_ch0_rate_mode_tx,
			p_CH0_RTERM_TX           = self.p_ch0_rterm_tx,
			p_CH0_SB_BYPASS          = self.p_ch0_sb_bypass,
			p_CH0_TDRV_DAT_SEL       = self.p_ch0_tdrv_dat_sel,
			p_CH0_TDRV_POST_EN       = self.p_ch0_tdrv_post_en,
			p_CH0_TDRV_PRE_EN        = self.p_ch0_tdrv_pre_en,
			p_CH0_TDRV_SLICE0_CUR    = self.p_ch0_tdrv_slice0_cur,
			p_CH0_TDRV_SLICE0_SEL    = self.p_ch0_tdrv_slice0_sel,
			p_CH0_TDRV_SLICE1_CUR    = self.p_ch0_tdrv_slice1_cur,
			p_CH0_TDRV_SLICE1_SEL    = self.p_ch0_tdrv_slice1_sel,
			p_CH0_TDRV_SLICE2_CUR    = self.p_ch0_tdrv_slice2_cur,
			p_CH0_TDRV_SLICE2_SEL    = self.p_ch0_tdrv_slice2_sel,
			p_CH0_TDRV_SLICE3_CUR    = self.p_ch0_tdrv_slice3_cur,
			p_CH0_TDRV_SLICE3_SEL    = self.p_ch0_tdrv_slice3_sel,
			p_CH0_TDRV_SLICE4_CUR    = self.p_ch0_tdrv_slice4_cur,
			p_CH0_TDRV_SLICE4_SEL    = self.p_ch0_tdrv_slice4_sel,
			p_CH0_TDRV_SLICE5_CUR    = self.p_ch0_tdrv_slice5_cur,
			p_CH0_TDRV_SLICE5_SEL    = self.p_ch0_tdrv_slice5_sel,
			p_CH0_TX_CM_SEL          = self.p_ch0_tx_cm_sel,
			p_CH0_TX_DIV11_SEL       = self.p_ch0_tx_div11_sel,
			p_CH0_TX_GEAR_BYPASS     = self.p_ch0_tx_gear_bypass,
			p_CH0_TX_GEAR_MODE       = self.p_ch0_tx_gear_mode,
			p_CH0_TX_POST_SIGN       = self.p_ch0_tx_post_sign,
			p_CH0_TX_PRE_SIGN        = self.p_ch0_tx_pre_sign,
			p_CH0_TXAMPLITUDE        = self.p_ch0_txamplitude,
			p_CH0_TXDEPOST           = self.p_ch0_txdepost,
			p_CH0_TXDEPRE            = self.p_ch0_txdepre,
			# DCU Channel 0 - RX
			i_CH0_FF_EBRD_CLK        = self.i_ch0_ff_ebrd_clk,
			i_CH0_FF_RXI_CLK         = self.i_ch0_ff_rxi_clk,
			i_CH0_FFC_CDR_EN_BITSLIP = self.i_ch0_ffc_cdr_en_bitslip,
			i_CH0_FFC_DIV11_MODE_RX  = self.i_ch0_ffc_div11_mode_rx,
			i_CH0_FFC_LANE_RX_RST    = self.i_ch0_ffc_lane_rx_rst,
			i_CH0_FFC_RATE_MODE_RX   = self.i_ch0_ffc_rate_mode_rx,
			i_CH0_FFC_RRST           = self.i_ch0_ffc_rrst,
			i_CH0_FFC_RX_GEAR_MODE   = self.i_ch0_ffc_rx_gear_mode,
			i_CH0_FFC_RXPWDNB        = self.i_ch0_ffc_rxpwdnb,
			i_CH0_FFC_SB_INV_RX      = self.i_ch0_ffc_sb_inv_rx,
			i_CH0_RX_REFCLK          = self.i_ch0_rx_refclk,
			**{ f'o_CH0_FF_RX_D_{bit}': self.o_ch0_ff_rx_d[bit] for bit in range(self.o_ch0_ff_rx_d.width) },
			o_CH0_FF_RX_F_CLK        = self.o_ch0_ff_rx_f_clk,
			o_CH0_FF_RX_H_CLK        = self.o_ch0_ff_rx_h_clk,
			o_CH0_FF_RX_PCLK         = self.o_ch0_ff_rx_pclk,
			o_CH0_FFS_CC_OVERRUN     = self.o_ch0_ffs_cc_overrun,
			o_CH0_FFS_CC_UNDERRUN    = self.o_ch0_ffs_cc_underrun,
			o_CH0_FFS_RLOL           = self.o_ch0_ffs_rlol,
			o_CH0_FFS_RLOS           = self.o_ch0_ffs_rlos,
			o_CH0_FFS_RXFBFIFO_ERROR = self.o_ch0_ffs_rxfbfifo_error,
			o_CH0_LDR_RX2CORE        = self.o_ch0_ldr_rx2core,
			p_CH0_FF_RX_F_CLK_DIS    = self.p_ch0_ff_rx_f_clk_dis,
			p_CH0_FF_RX_H_CLK_EN     = self.p_ch0_ff_rx_h_clk_en,
			p_CH0_INVERT_RX          = self.p_ch0_invert_rx,
			p_CH0_LDR_RX2CORE_SEL    = self.p_ch0_ldr_rx2core_sel,
			p_CH0_LEQ_OFFSET_SEL     = self.p_ch0_leq_offset_sel,
			p_CH0_LEQ_OFFSET_TRIM    = self.p_ch0_leq_offset_trim,
			p_CH0_RATE_MODE_RX       = self.p_ch0_rate_mode_rx,
			p_CH0_RCV_DCC_EN         = self.p_ch0_rcv_dcc_en,
			p_CH0_REQ_EN             = self.p_ch0_req_en,
			p_CH0_REQ_LVL_SET        = self.p_ch0_req_lvl_set,
			p_CH0_RLOS_SEL           = self.p_ch0_rlos_sel,
			p_CH0_RTERM_RX           = self.p_ch0_rterm_rx,
			p_CH0_RX_DCO_CK_DIV      = self.p_ch0_rx_dco_ck_div,
			p_CH0_RX_DIV11_SEL       = self.p_ch0_rx_div11_sel,
			p_CH0_RX_GEAR_BYPASS     = self.p_ch0_rx_gear_bypass,
			p_CH0_RX_GEAR_MODE       = self.p_ch0_rx_gear_mode,
			p_CH0_RX_LOS_CEQ         = self.p_ch0_rx_los_ceq,
			p_CH0_RX_LOS_EN          = self.p_ch0_rx_los_en,
			p_CH0_RX_LOS_HYST_EN     = self.p_ch0_rx_los_hyst_en,
			p_CH0_RX_LOS_LVL         = self.p_ch0_rx_los_lvl,
			p_CH0_RX_RATE_SEL        = self.p_ch0_rx_rate_sel,
			p_CH0_RX_SB_BYPASS       = self.p_ch0_rx_sb_bypass,
			p_CH0_RXIN_CM            = self.p_ch0_rxin_cm,
			p_CH0_RXTERM_CM          = self.p_ch0_rxterm_cm,
			p_CH0_SEL_SD_RX_CLK      = self.p_ch0_sel_sd_rx_clk,
						# DCU Channel 1
			i_CH1_FFC_EI_EN          = self.i_ch1_ffc_ei_en,
			i_CH1_FFC_ENABLE_CGALIGN = self.i_ch1_ffc_enable_cgalign,
			i_CH1_FFC_FB_LOOPBACK    = self.i_ch1_ffc_fb_loopback,
			i_CH1_FFC_PCIE_CT        = self.i_ch1_ffc_pcie_ct,
			i_CH1_FFC_PCIE_DET_EN    = self.i_ch1_ffc_pcie_det_en,
			i_CH1_FFC_PFIFO_CLR      = self.i_ch1_ffc_pfifo_clr,
			i_CH1_FFC_SB_PFIFO_LP    = self.i_ch1_ffc_sb_pfifo_lp,
			i_CH1_FFC_SIGNAL_DETECT  = self.i_ch1_ffc_signal_detect,
			i_CH1_HDINN              = self.i_ch1_hdinn,
			i_CH1_HDINP              = self.i_ch1_hdinp,
			o_CH1_FFS_LS_SYNC_STATUS = self.o_ch1_ffs_ls_sync_status,
			o_CH1_FFS_PCIE_CON       = self.o_ch1_ffs_pcie_con,
			o_CH1_FFS_PCIE_DONE      = self.o_ch1_ffs_pcie_done,
			o_CH1_FFS_SKP_ADDED      = self.o_ch1_ffs_skp_added,
			o_CH1_FFS_SKP_DELETED    = self.o_ch1_ffs_skp_deleted,
			o_CH1_HDOUTN             = self.o_ch1_hdoutn,
			o_CH1_HDOUTP             = self.o_ch1_hdoutp,
			p_CH1_AUTO_CALIB_EN      = self.p_ch1_auto_calib_en,
			p_CH1_AUTO_FACQ_EN       = self.p_ch1_auto_facq_en,
			p_CH1_BAND_THRESHOLD     = self.p_ch1_band_threshold,
			p_CH1_CALIB_CK_MODE      = self.p_ch1_calib_ck_mode,
			p_CH1_CC_MATCH_1         = self.p_ch1_cc_match_1,
			p_CH1_CC_MATCH_2         = self.p_ch1_cc_match_2,
			p_CH1_CC_MATCH_3         = self.p_ch1_cc_match_3,
			p_CH1_CC_MATCH_4         = self.p_ch1_cc_match_4,
			p_CH1_CDR_CNT4SEL        = self.p_ch1_cdr_cnt4sel,
			p_CH1_CDR_CNT8SEL        = self.p_ch1_cdr_cnt8sel,
			p_CH1_CDR_MAX_RATE       = self.p_ch1_cdr_max_rate,
			p_CH1_CTC_BYPASS         = self.p_ch1_ctc_bypass,
			p_CH1_DCOATDCFG          = self.p_ch1_dcoatdcfg,
			p_CH1_DCOATDDLY          = self.p_ch1_dcoatddly,
			p_CH1_DCOBYPSATD         = self.p_ch1_dcobypsatd,
			p_CH1_DCOCALDIV          = self.p_ch1_dcocaldiv,
			p_CH1_DCOCTLGI           = self.p_ch1_dcoctlgi,
			p_CH1_DCODISBDAVOID      = self.p_ch1_dcodisbdavoid,
			p_CH1_DCOFLTDAC          = self.p_ch1_dcofltdac,
			p_CH1_DCOFTNRG           = self.p_ch1_dcoftnrg,
			p_CH1_DCOIOSTUNE         = self.p_ch1_dcoiostune,
			p_CH1_DCOITUNE           = self.p_ch1_dcoitune,
			p_CH1_DCOITUNE4LSB       = self.p_ch1_dcoitune4lsb,
			p_CH1_DCOIUPDNX2         = self.p_ch1_dcoiupdnx2,
			p_CH1_DCONUOFLSB         = self.p_ch1_dconuoflsb,
			p_CH1_DCOSCALEI          = self.p_ch1_dcoscalei,
			p_CH1_DCOSTARTVAL        = self.p_ch1_dcostartval,
			p_CH1_DCOSTEP            = self.p_ch1_dcostep,
			p_CH1_DEC_BYPASS         = self.p_ch1_dec_bypass,
			p_CH1_ENABLE_CG_ALIGN    = self.p_ch1_enable_cg_align,
			p_CH1_ENC_BYPASS         = self.p_ch1_enc_bypass,
			p_CH1_GE_AN_ENABLE       = self.p_ch1_ge_an_enable,
			p_CH1_LSM_DISABLE        = self.p_ch1_lsm_disable,
			p_CH1_MATCH_2_ENABLE     = self.p_ch1_match_2_enable,
			p_CH1_MATCH_4_ENABLE     = self.p_ch1_match_4_enable,
			p_CH1_MIN_IPG_CNT        = self.p_ch1_min_ipg_cnt,
			p_CH1_PCIE_EI_EN         = self.p_ch1_pcie_ei_en,
			p_CH1_PCIE_MODE          = self.p_ch1_pcie_mode,
			p_CH1_PCS_DET_TIME_SEL   = self.p_ch1_pcs_det_time_sel,
			p_CH1_PDEN_SEL           = self.p_ch1_pden_sel,
			p_CH1_PRBS_ENABLE        = self.p_ch1_prbs_enable,
			p_CH1_PRBS_LOCK          = self.p_ch1_prbs_lock,
			p_CH1_PRBS_SELECTION     = self.p_ch1_prbs_selection,
			p_CH1_PROTOCOL           = self.p_ch1_protocol,
			p_CH1_REG_BAND_OFFSET    = self.p_ch1_reg_band_offset,
			p_CH1_REG_BAND_SEL       = self.p_ch1_reg_band_sel,
			p_CH1_REG_IDAC_EN        = self.p_ch1_reg_idac_en,
			p_CH1_REG_IDAC_SEL       = self.p_ch1_reg_idac_sel,
			p_CH1_RIO_MODE           = self.p_ch1_rio_mode,
			p_CH1_RPWDNB             = self.p_ch1_rpwdnb,
			p_CH1_TPWDNB             = self.p_ch1_tpwdnb,
			p_CH1_UC_MODE            = self.p_ch1_uc_mode,
			p_CH1_UDF_COMMA_A        = self.p_ch1_udf_comma_a,
			p_CH1_UDF_COMMA_B        = self.p_ch1_udf_comma_b,
			p_CH1_UDF_COMMA_MASK     = self.p_ch1_udf_comma_mask,
			p_CH1_WA_BYPASS          = self.p_ch1_wa_bypass,
			p_CH1_WA_MODE            = self.p_ch1_wa_mode,
			# DCU Channel 1 - TX
			**{ f'i_CH1_FF_TX_D_{bit}': self.i_ch1_ff_tx_d[bit] for bit in range(self.i_ch1_ff_tx_d.width) },
			i_CH1_FF_TXI_CLK         = self.i_ch1_ff_txi_clk,
			i_CH1_FFC_DIV11_MODE_TX  = self.i_ch1_ffc_div11_mode_tx,
			i_CH1_FFC_LANE_TX_RST    = self.i_ch1_ffc_lane_tx_rst,
			i_CH1_FFC_LDR_CORE2TX_EN = self.i_ch1_ffc_ldr_core2tx_en,
			i_CH1_FFC_RATE_MODE_TX   = self.i_ch1_ffc_rate_mode_tx,
			i_CH1_FFC_TX_GEAR_MODE   = self.i_ch1_ffc_tx_gear_mode,
			i_CH1_FFC_TXPWDNB        = self.i_ch1_ffc_txpwdnb,
			i_CH1_LDR_CORE2TX        = self.i_ch1_ldr_core2tx,
			o_CH1_FF_TX_F_CLK        = self.o_ch1_ff_tx_f_clk,
			o_CH1_FF_TX_H_CLK        = self.o_ch1_ff_tx_h_clk,
			o_CH1_FF_TX_PCLK         = self.o_ch1_ff_tx_pclk,
			o_CH1_FFS_TXFBFIFO_ERROR = self.o_ch1_ffs_txfbfifo_error,
			p_CH1_FF_TX_F_CLK_DIS    = self.p_ch1_ff_tx_f_clk_dis,
			p_CH1_FF_TX_H_CLK_EN     = self.p_ch1_ff_tx_h_clk_en,
			p_CH1_INVERT_TX          = self.p_ch1_invert_tx,
			p_CH1_LDR_CORE2TX_SEL    = self.p_ch1_ldr_core2tx_sel,
			p_CH1_RATE_MODE_TX       = self.p_ch1_rate_mode_tx,
			p_CH1_RTERM_TX           = self.p_ch1_rterm_tx,
			p_CH1_SB_BYPASS          = self.p_ch1_sb_bypass,
			p_CH1_TDRV_DAT_SEL       = self.p_ch1_tdrv_dat_sel,
			p_CH1_TDRV_POST_EN       = self.p_ch1_tdrv_post_en,
			p_CH1_TDRV_PRE_EN        = self.p_ch1_tdrv_pre_en,
			p_CH1_TDRV_SLICE0_CUR    = self.p_ch1_tdrv_slice0_cur,
			p_CH1_TDRV_SLICE0_SEL    = self.p_ch1_tdrv_slice0_sel,
			p_CH1_TDRV_SLICE1_CUR    = self.p_ch1_tdrv_slice1_cur,
			p_CH1_TDRV_SLICE1_SEL    = self.p_ch1_tdrv_slice1_sel,
			p_CH1_TDRV_SLICE2_CUR    = self.p_ch1_tdrv_slice2_cur,
			p_CH1_TDRV_SLICE2_SEL    = self.p_ch1_tdrv_slice2_sel,
			p_CH1_TDRV_SLICE3_CUR    = self.p_ch1_tdrv_slice3_cur,
			p_CH1_TDRV_SLICE3_SEL    = self.p_ch1_tdrv_slice3_sel,
			p_CH1_TDRV_SLICE4_CUR    = self.p_ch1_tdrv_slice4_cur,
			p_CH1_TDRV_SLICE4_SEL    = self.p_ch1_tdrv_slice4_sel,
			p_CH1_TDRV_SLICE5_CUR    = self.p_ch1_tdrv_slice5_cur,
			p_CH1_TDRV_SLICE5_SEL    = self.p_ch1_tdrv_slice5_sel,
			p_CH1_TX_CM_SEL          = self.p_ch1_tx_cm_sel,
			p_CH1_TX_DIV11_SEL       = self.p_ch1_tx_div11_sel,
			p_CH1_TX_GEAR_BYPASS     = self.p_ch1_tx_gear_bypass,
			p_CH1_TX_GEAR_MODE       = self.p_ch1_tx_gear_mode,
			p_CH1_TX_POST_SIGN       = self.p_ch1_tx_post_sign,
			p_CH1_TX_PRE_SIGN        = self.p_ch1_tx_pre_sign,
			p_CH1_TXAMPLITUDE        = self.p_ch1_txamplitude,
			p_CH1_TXDEPOST           = self.p_ch1_txdepost,
			p_CH1_TXDEPRE            = self.p_ch1_txdepre,
			# DCU Channel 1 - RX
			i_CH1_FF_EBRD_CLK        = self.i_ch1_ff_ebrd_clk,
			i_CH1_FF_RXI_CLK         = self.i_ch1_ff_rxi_clk,
			i_CH1_FFC_CDR_EN_BITSLIP = self.i_ch1_ffc_cdr_en_bitslip,
			i_CH1_FFC_DIV11_MODE_RX  = self.i_ch1_ffc_div11_mode_rx,
			i_CH1_FFC_LANE_RX_RST    = self.i_ch1_ffc_lane_rx_rst,
			i_CH1_FFC_RATE_MODE_RX   = self.i_ch1_ffc_rate_mode_rx,
			i_CH1_FFC_RRST           = self.i_ch1_ffc_rrst,
			i_CH1_FFC_RX_GEAR_MODE   = self.i_ch1_ffc_rx_gear_mode,
			i_CH1_FFC_RXPWDNB        = self.i_ch1_ffc_rxpwdnb,
			i_CH1_FFC_SB_INV_RX      = self.i_ch1_ffc_sb_inv_rx,
			i_CH1_RX_REFCLK          = self.i_ch1_rx_refclk,
			**{ f'o_CH1_FF_RX_D_{bit}': self.o_ch1_ff_rx_d[bit] for bit in range(self.o_ch1_ff_rx_d.width) },
			o_CH1_FF_RX_F_CLK        = self.o_ch1_ff_rx_f_clk,
			o_CH1_FF_RX_H_CLK        = self.o_ch1_ff_rx_h_clk,
			o_CH1_FF_RX_PCLK         = self.o_ch1_ff_rx_pclk,
			o_CH1_FFS_CC_OVERRUN     = self.o_ch1_ffs_cc_overrun,
			o_CH1_FFS_CC_UNDERRUN    = self.o_ch1_ffs_cc_underrun,
			o_CH1_FFS_RLOL           = self.o_ch1_ffs_rlol,
			o_CH1_FFS_RLOS           = self.o_ch1_ffs_rlos,
			o_CH1_FFS_RXFBFIFO_ERROR = self.o_ch1_ffs_rxfbfifo_error,
			o_CH1_LDR_RX2CORE        = self.o_ch1_ldr_rx2core,
			p_CH1_FF_RX_F_CLK_DIS    = self.p_ch1_ff_rx_f_clk_dis,
			p_CH1_FF_RX_H_CLK_EN     = self.p_ch1_ff_rx_h_clk_en,
			p_CH1_INVERT_RX          = self.p_ch1_invert_rx,
			p_CH1_LDR_RX2CORE_SEL    = self.p_ch1_ldr_rx2core_sel,
			p_CH1_LEQ_OFFSET_SEL     = self.p_ch1_leq_offset_sel,
			p_CH1_LEQ_OFFSET_TRIM    = self.p_ch1_leq_offset_trim,
			p_CH1_RATE_MODE_RX       = self.p_ch1_rate_mode_rx,
			p_CH1_RCV_DCC_EN         = self.p_ch1_rcv_dcc_en,
			p_CH1_REQ_EN             = self.p_ch1_req_en,
			p_CH1_REQ_LVL_SET        = self.p_ch1_req_lvl_set,
			p_CH1_RLOS_SEL           = self.p_ch1_rlos_sel,
			p_CH1_RTERM_RX           = self.p_ch1_rterm_rx,
			p_CH1_RX_DCO_CK_DIV      = self.p_ch1_rx_dco_ck_div,
			p_CH1_RX_DIV11_SEL       = self.p_ch1_rx_div11_sel,
			p_CH1_RX_GEAR_BYPASS     = self.p_ch1_rx_gear_bypass,
			p_CH1_RX_GEAR_MODE       = self.p_ch1_rx_gear_mode,
			p_CH1_RX_LOS_CEQ         = self.p_ch1_rx_los_ceq,
			p_CH1_RX_LOS_EN          = self.p_ch1_rx_los_en,
			p_CH1_RX_LOS_HYST_EN     = self.p_ch1_rx_los_hyst_en,
			p_CH1_RX_LOS_LVL         = self.p_ch1_rx_los_lvl,
			p_CH1_RX_RATE_SEL        = self.p_ch1_rx_rate_sel,
			p_CH1_RX_SB_BYPASS       = self.p_ch1_rx_sb_bypass,
			p_CH1_RXIN_CM            = self.p_ch1_rxin_cm,
			p_CH1_RXTERM_CM          = self.p_ch1_rxterm_cm,
			p_CH1_SEL_SD_RX_CLK      = self.p_ch1_sel_sd_rx_clk,
		)

		return m
