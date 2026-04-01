"""
Magnetic Bridge Protocol — executable specification extracted from Magnetic-bridge.md

Implements the read/write protocol state machine, command/response structures,
error codes, calibration logic, and physical constants for the magnetic bridge
between binary/octal values and octahedral tensor states in silicon.

Dependencies: stdlib + numpy only.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

MU_BOHR = 5.7883818012e-5  # eV/T  (Bohr magneton)
G_FACTOR = 2.0023193        # electron g-factor
HBAR_EV_S = 6.582119569e-16  # eV*s  (reduced Planck constant)

# Core angle from project spec (tetrahedral, silicon sp3)
TETRAHEDRAL_ANGLE_DEG = 109.47

# ---------------------------------------------------------------------------
# Coordinate system — tetrahedral vertex directions in lab frame
# ---------------------------------------------------------------------------

V1 = np.array([1, 1, 1], dtype=np.float64) / np.sqrt(3)
V2 = np.array([1, -1, -1], dtype=np.float64) / np.sqrt(3)
V3 = np.array([-1, 1, -1], dtype=np.float64) / np.sqrt(3)
V4 = np.array([-1, -1, 1], dtype=np.float64) / np.sqrt(3)

TETRAHEDRAL_DIRECTIONS = (V1, V2, V3, V4)

# Measurement field orientations: z, x, y, [111]
MEASUREMENT_AXES = [
    np.array([0, 0, 1], dtype=np.float64),  # z-hat
    np.array([1, 0, 0], dtype=np.float64),  # x-hat
    np.array([0, 1, 0], dtype=np.float64),  # y-hat
    V1,                                       # [111] diagonal
]

# ---------------------------------------------------------------------------
# Field generator specs (from hardware requirements)
# ---------------------------------------------------------------------------

STATIC_FIELD_MAX_T = 2.0           # Tesla
CALIBRATION_FIELD_T = 0.5          # Tesla (z-axis, Phase 1)
MEASUREMENT_FIELD_T = 1.0          # Tesla (per-axis probe)
RF_FREQ_MIN_GHZ = 1.0
RF_FREQ_MAX_GHZ = 100.0
RF_PROBE_FREQ_GHZ = 10.0          # default probe frequency
RF_POWER_MIN_W = 0.1
RF_POWER_MAX_W = 10.0
GRADIENT_MAX_T_PER_M = 1000.0
SPATIAL_RESOLUTION_NM = 5.0

# ---------------------------------------------------------------------------
# Timing constants (nanoseconds unless noted)
# ---------------------------------------------------------------------------

READ_INIT_NS = 10.0
READ_PER_MEASUREMENT_NS = 10.0
READ_STABILIZATION_NS = 5.0
RF_PROBE_PULSE_PS = 100.0         # picoseconds
READ_ACQUISITION_NS = 4.9
READ_DECODE_NS = 1.0              # < 1 ns
TOTAL_READ_NS = 50.0

WRITE_TRANSITION_PS = 10.0        # picoseconds (adiabatic pulse)
ADIABATIC_DURATION_PS = 10.0      # 100x safety margin over 0.1 ps
RABI_PULSE_PS = 0.54              # single pi-pulse
COMPOSITE_PULSE_PS = 1.6          # X(pi/2)-Y(pi)-X(pi/2)
WRITE_RAMP_NS = 5.0
TOTAL_WRITE_NS = 70.0             # approximate single-cell write

# Parallel block (8-cell frequency-multiplexed)
PARALLEL_BLOCK_CELLS = 8
PARALLEL_BLOCK_NS = 116.0
FREQ_MUX_BASE_GHZ = 10.0
FREQ_MUX_SPACING_GHZ = 1.0

# Calibration
MAX_RETRIES = 3
CALIBRATION_PER_CELL_NS = 1000.0  # ~1 us
RECALIBRATION_OPS = 1_000_000     # lower bound on recal interval

# Confidence
CONFIDENCE_THRESHOLD = 0.7
CONFIDENCE_UNCERTAIN_BYTE = 180   # < 180/255 means uncertain

# ---------------------------------------------------------------------------
# Canonical eigenvalue table — 8 octahedral states
# Eigenvalues (lambda_1 >= lambda_2 >= lambda_3), trace = 1
# ---------------------------------------------------------------------------

CANONICAL_EIGENVALUES = np.array([
    [0.333, 0.333, 0.333],  # state 0: isotropic
    [0.500, 0.300, 0.200],  # state 1: mild anisotropy
    [0.450, 0.350, 0.200],  # state 2: moderate spread
    [0.400, 0.350, 0.250],  # state 3: slight spread
    [0.600, 0.250, 0.150],  # state 4: moderate uniaxial
    [0.700, 0.200, 0.100],  # state 5: strong uniaxial (spec example)
    [0.500, 0.500, 0.000],  # state 6: planar
    [1.000, 0.000, 0.000],  # state 7: fully aligned
], dtype=np.float64)

# ---------------------------------------------------------------------------
# Transition table (example entries from spec)
# transition_table[n_current][n_target] -> TransitionParams
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TransitionParams:
    """Pre-computed parameters for a specific state-to-state transition."""
    frequency_ghz: float        # resonance frequency (Delta-E / hbar)
    orientation_deg: Tuple[float, float]  # (theta, phi) in degrees
    pulse_duration_ps: float    # pi-pulse or adiabatic duration
    field_amplitude_t: float    # RF field strength (Tesla)


def _build_default_transition_table() -> Dict[Tuple[int, int], TransitionParams]:
    """Build a sparse transition table with the example entry from spec
    and identity (no-op) entries on the diagonal."""
    table: Dict[Tuple[int, int], TransitionParams] = {}

    # Explicit example from spec: 0 -> 5
    table[(0, 5)] = TransitionParams(
        frequency_ghz=15.2,
        orientation_deg=(125.0, 45.0),
        field_amplitude_t=0.05,
        pulse_duration_ps=8.5,
    )

    # Identity transitions (no-ops)
    for i in range(8):
        table[(i, i)] = TransitionParams(
            frequency_ghz=0.0,
            orientation_deg=(0.0, 0.0),
            field_amplitude_t=0.0,
            pulse_duration_ps=0.0,
        )

    return table


TRANSITION_TABLE: Dict[Tuple[int, int], TransitionParams] = (
    _build_default_transition_table()
)

# ---------------------------------------------------------------------------
# Frequency multiplexing table for parallel 8-cell blocks
# ---------------------------------------------------------------------------

FREQ_MUX_TABLE_GHZ: List[float] = [
    FREQ_MUX_BASE_GHZ + i * FREQ_MUX_SPACING_GHZ
    for i in range(PARALLEL_BLOCK_CELLS)
]  # [10, 11, 12, 13, 14, 15, 16, 17] GHz

# ---------------------------------------------------------------------------
# Phase sequences (read and write)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhaseStep:
    """One step in a read or write phase sequence."""
    name: str
    duration_ns: float
    description: str


READ_PHASE_SEQUENCE: List[PhaseStep] = [
    PhaseStep("INIT", READ_INIT_NS,
              "Ramp static field to 0.5T z-hat; wait for eddy current decay"),
    PhaseStep("MEASURE_Z", READ_PER_MEASUREMENT_NS,
              "B = 1.0T z-hat; RF probe; measure E1 ~ T_zz"),
    PhaseStep("MEASURE_X", READ_PER_MEASUREMENT_NS,
              "B = 1.0T x-hat; RF probe; measure E2 ~ T_xx"),
    PhaseStep("MEASURE_Y", READ_PER_MEASUREMENT_NS,
              "B = 1.0T y-hat; RF probe; measure E3 ~ T_yy"),
    PhaseStep("MEASURE_111", READ_PER_MEASUREMENT_NS,
              "B = 1.0T [111]/sqrt3; RF probe; measure E4 ~ v1.T.v1"),
    PhaseStep("DECODE", READ_DECODE_NS,
              "Tensor reconstruction + eigenvalue decode + confidence"),
]

WRITE_PHASE_SEQUENCE: List[PhaseStep] = [
    PhaseStep("READ_CURRENT", TOTAL_READ_NS,
              "Full read protocol to determine current state"),
    PhaseStep("COMPUTE_PATH", 1.0,
              "Lookup transition_table[current][target]"),
    PhaseStep("RAMP_ORIENTATION", WRITE_RAMP_NS,
              "Rotate static field to target orientation"),
    PhaseStep("RF_TRANSITION", ADIABATIC_DURATION_PS / 1000.0,
              "Adiabatic rapid passage or resonant pi-pulse"),
    PhaseStep("VERIFICATION", TOTAL_READ_NS,
              "Full read protocol to verify written state"),
]

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

class ErrorCode(enum.IntEnum):
    SUCCESS = 0x00
    TIMEOUT = 0x01
    TRACE_ERROR = 0x02
    EIGENVALUE_ERROR = 0x03
    VERIFY_FAILED = 0x04
    DEFECTIVE_CELL = 0x05
    FIELD_ERROR = 0x10
    RF_ERROR = 0x11
    UNKNOWN_ERROR = 0xFF


# ---------------------------------------------------------------------------
# Command / Response dataclasses
# ---------------------------------------------------------------------------

class CommandType(enum.IntEnum):
    READ = 0x01
    WRITE = 0x02
    INIT = 0x10


class CommandFlag(enum.IntFlag):
    NONE = 0x00
    VERIFY = 0x01
    PARALLEL = 0x02


@dataclass
class BridgeCommand:
    """Command sent *to* the bridge (mirrors the C struct in spec)."""
    command: CommandType
    cell_id: int                    # uint16
    data: int = 0                   # 3-bit octal value (0-7), used for WRITE
    flags: CommandFlag = CommandFlag.NONE

    def __post_init__(self) -> None:
        if not 0 <= self.cell_id <= 0xFFFF:
            raise ValueError(f"cell_id must be 0..65535, got {self.cell_id}")
        if not 0 <= self.data <= 7:
            raise ValueError(f"data must be 0..7, got {self.data}")


@dataclass
class BridgeResponse:
    """Response returned *from* the bridge (mirrors the C struct in spec)."""
    status: ErrorCode = ErrorCode.SUCCESS
    data: int = 0                   # 3-bit octal value
    confidence: int = 255           # 0-255, 255 = certain
    timestamp_ns: int = 0           # ns since init

    @property
    def is_uncertain(self) -> bool:
        return self.confidence < CONFIDENCE_UNCERTAIN_BYTE


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class BridgeState(enum.Enum):
    IDLE = "STATE_IDLE"
    READ_INIT = "STATE_READ_INIT"
    READ_MEASURE = "STATE_READ_MEASURE"
    READ_DECODE = "STATE_READ_DECODE"
    READ_COMPLETE = "STATE_READ_COMPLETE"
    WRITE_READ_CURRENT = "STATE_WRITE_READ_CURRENT"
    WRITE_PLAN = "STATE_WRITE_PLAN"
    WRITE_TRANSITION = "STATE_WRITE_TRANSITION"
    WRITE_VERIFY = "STATE_WRITE_VERIFY"
    WRITE_COMPLETE = "STATE_WRITE_COMPLETE"
    WRITE_FAILED = "STATE_WRITE_FAILED"
    ERROR_CORRECTION = "STATE_ERROR_CORRECTION"


# Legal transitions (source -> set of destinations)
STATE_TRANSITIONS: Dict[BridgeState, Tuple[BridgeState, ...]] = {
    BridgeState.IDLE: (BridgeState.READ_INIT, BridgeState.WRITE_READ_CURRENT),
    BridgeState.READ_INIT: (BridgeState.READ_MEASURE,),
    BridgeState.READ_MEASURE: (BridgeState.READ_DECODE,),
    BridgeState.READ_DECODE: (BridgeState.READ_COMPLETE, BridgeState.ERROR_CORRECTION),
    BridgeState.READ_COMPLETE: (BridgeState.IDLE,),
    BridgeState.WRITE_READ_CURRENT: (BridgeState.WRITE_PLAN,),
    BridgeState.WRITE_PLAN: (BridgeState.WRITE_TRANSITION,),
    BridgeState.WRITE_TRANSITION: (BridgeState.WRITE_VERIFY,),
    BridgeState.WRITE_VERIFY: (
        BridgeState.WRITE_COMPLETE,
        BridgeState.WRITE_TRANSITION,
        BridgeState.WRITE_FAILED,
    ),
    BridgeState.WRITE_COMPLETE: (BridgeState.IDLE,),
    BridgeState.WRITE_FAILED: (BridgeState.IDLE,),
    BridgeState.ERROR_CORRECTION: (BridgeState.READ_DECODE,),
}


class MagneticBridgeProtocol:
    """
    Software model of the magnetic bridge control sequencer.

    Simulates the full read/write state machine described in the spec,
    including tensor reconstruction, state decoding, calibration, and
    retry logic.  Cell states are held in a numpy array (one 3-bit
    value per cell).
    """

    def __init__(self, num_cells: int = 1024) -> None:
        self.num_cells = num_cells
        self.state = BridgeState.IDLE
        self._sim_time_ns: float = 0.0

        # Simulated cell memory: each cell stores a state index 0-7
        self._cells = np.zeros(num_cells, dtype=np.uint8)

        # Per-cell calibration correction factors: shape (num_cells, 8)
        self._calibration: np.ndarray = np.ones((num_cells, 8), dtype=np.float64)
        self._calibrated: np.ndarray = np.zeros(num_cells, dtype=bool)

        # Write retry state
        self._retry_count: int = 0
        self._current_state: int = 0
        self._target_state: int = 0
        self._active_cell: int = 0

        # Defective cell registry
        self.defective_cells: set = set()

    # ---- time bookkeeping -------------------------------------------------

    def _advance(self, ns: float) -> None:
        self._sim_time_ns += ns

    @property
    def sim_time_ns(self) -> float:
        return self._sim_time_ns

    # ---- state machine helpers --------------------------------------------

    def _transition_to(self, target: BridgeState) -> None:
        allowed = STATE_TRANSITIONS.get(self.state, ())
        if target not in allowed:
            raise RuntimeError(
                f"Illegal transition {self.state.value} -> {target.value}"
            )
        self.state = target

    # ---- tensor / decode math ---------------------------------------------

    @staticmethod
    def reconstruct_tensor(
        energies: Tuple[float, float, float, float],
        b_field: float = MEASUREMENT_FIELD_T,
        epsilon: float = 0.05,
    ) -> Tuple[np.ndarray, Optional[ErrorCode]]:
        """
        Phase 3: Tensor reconstruction from four energy measurements.

        Returns (diagonal tensor [T_xx, T_yy, T_zz], error_or_None).
        """
        e1, e2, e3, e4 = energies
        denom = MU_BOHR * G_FACTOR * b_field ** 2

        t_zz = -e1 / denom
        t_xx = -e2 / denom
        t_yy = -e3 / denom

        tensor_diag = np.array([t_xx, t_yy, t_zz], dtype=np.float64)

        # Cross-check with [111] measurement
        t_111_expected = tensor_diag.sum() / 3.0
        t_111_measured = -e4 / denom
        if abs(t_111_expected - t_111_measured) > epsilon:
            return tensor_diag, ErrorCode.TRACE_ERROR

        return tensor_diag, None

    @staticmethod
    def decode_state(
        tensor_diag: np.ndarray,
    ) -> Tuple[int, float, Optional[ErrorCode]]:
        """
        Phase 4: Eigenvalue-based state decode.

        Returns (state_index, confidence, error_or_None).
        """
        lambdas = np.sort(tensor_diag)[::-1]  # descending

        distances = np.linalg.norm(
            CANONICAL_EIGENVALUES - lambdas[np.newaxis, :], axis=1
        )
        order = np.argsort(distances)
        best = order[0]
        second = order[1]

        d_best = distances[best]
        d_second = distances[second]

        if d_second == 0:
            confidence = 0.0
        else:
            confidence = 1.0 - d_best / d_second

        error = None
        if confidence < CONFIDENCE_THRESHOLD:
            error = ErrorCode.EIGENVALUE_ERROR

        return int(best), float(confidence), error

    # ---- high-level protocol methods --------------------------------------

    def execute(self, cmd: BridgeCommand) -> BridgeResponse:
        """
        Execute a BridgeCommand through the full state machine.
        """
        if cmd.cell_id >= self.num_cells:
            return BridgeResponse(
                status=ErrorCode.UNKNOWN_ERROR,
                timestamp_ns=int(self._sim_time_ns),
            )

        if cmd.cell_id in self.defective_cells:
            return BridgeResponse(
                status=ErrorCode.DEFECTIVE_CELL,
                timestamp_ns=int(self._sim_time_ns),
            )

        if cmd.command == CommandType.READ:
            return self._execute_read(cmd.cell_id)
        elif cmd.command == CommandType.WRITE:
            return self._execute_write(cmd.cell_id, cmd.data)
        elif cmd.command == CommandType.INIT:
            return self._execute_calibration(cmd.cell_id)
        else:
            return BridgeResponse(
                status=ErrorCode.UNKNOWN_ERROR,
                timestamp_ns=int(self._sim_time_ns),
            )

    # ---- read protocol ----------------------------------------------------

    def _execute_read(self, cell_id: int) -> BridgeResponse:
        # IDLE -> READ_INIT
        self._transition_to(BridgeState.READ_INIT)
        self._advance(READ_INIT_NS)

        # READ_INIT -> READ_MEASURE
        self._transition_to(BridgeState.READ_MEASURE)
        self._advance(READ_PER_MEASUREMENT_NS * 4)

        # READ_MEASURE -> READ_DECODE
        self._transition_to(BridgeState.READ_DECODE)
        self._advance(READ_DECODE_NS)

        # Simulate measurement: produce energies from stored state
        true_state = int(self._cells[cell_id])
        energies = self._simulate_energies(cell_id, true_state)

        tensor_diag, recon_error = self.reconstruct_tensor(energies)

        if recon_error is not None:
            # READ_DECODE -> ERROR_CORRECTION -> READ_DECODE
            self._transition_to(BridgeState.ERROR_CORRECTION)
            self._advance(5.0)  # correction overhead
            self._transition_to(BridgeState.READ_DECODE)
            # On second pass, just proceed (simulation always succeeds)

        state_idx, confidence, decode_error = self.decode_state(tensor_diag)
        conf_byte = min(255, max(0, int(confidence * 255)))

        # READ_DECODE -> READ_COMPLETE -> IDLE
        self._transition_to(BridgeState.READ_COMPLETE)
        self._transition_to(BridgeState.IDLE)

        status = ErrorCode.SUCCESS
        if decode_error is not None:
            status = decode_error

        return BridgeResponse(
            status=status,
            data=state_idx,
            confidence=conf_byte,
            timestamp_ns=int(self._sim_time_ns),
        )

    def _simulate_energies(
        self, cell_id: int, state_idx: int
    ) -> Tuple[float, float, float, float]:
        """
        Produce synthetic energy measurements for a known state,
        applying calibration corrections.
        """
        eigs = CANONICAL_EIGENVALUES[state_idx]
        denom = MU_BOHR * G_FACTOR * MEASUREMENT_FIELD_T ** 2
        cal = self._calibration[cell_id, state_idx]

        # E_i = -T_ii * denom (inverted in reconstruct_tensor)
        e_z = -eigs[2] * denom * cal  # T_zz
        e_x = -eigs[0] * denom * cal  # T_xx
        e_y = -eigs[1] * denom * cal  # T_yy
        e_111 = -(eigs.sum() / 3.0) * denom * cal

        return (e_z, e_x, e_y, e_111)

    # ---- write protocol ---------------------------------------------------

    def _execute_write(self, cell_id: int, target: int) -> BridgeResponse:
        self._active_cell = cell_id
        self._target_state = target
        self._retry_count = 0

        # Phase 1: Read current state
        # IDLE -> WRITE_READ_CURRENT
        self._transition_to(BridgeState.WRITE_READ_CURRENT)
        self._advance(TOTAL_READ_NS)
        self._current_state = int(self._cells[cell_id])

        # Phase 2: Compute transition path
        # WRITE_READ_CURRENT -> WRITE_PLAN
        self._transition_to(BridgeState.WRITE_PLAN)
        self._advance(1.0)

        # Lookup transition params (may be absent for non-example pairs)
        _params = TRANSITION_TABLE.get(
            (self._current_state, self._target_state)
        )

        # Phase 3: Apply transition
        return self._write_transition_loop()

    def _write_transition_loop(self) -> BridgeResponse:
        while True:
            # WRITE_PLAN or WRITE_VERIFY -> WRITE_TRANSITION
            self._transition_to(BridgeState.WRITE_TRANSITION)
            self._advance(WRITE_RAMP_NS + ADIABATIC_DURATION_PS / 1000.0)

            # Simulate: write succeeds
            self._cells[self._active_cell] = self._target_state

            # Phase 4: Verify
            # WRITE_TRANSITION -> WRITE_VERIFY
            self._transition_to(BridgeState.WRITE_VERIFY)
            self._advance(TOTAL_READ_NS)

            verified = int(self._cells[self._active_cell])

            if verified == self._target_state:
                # WRITE_VERIFY -> WRITE_COMPLETE -> IDLE
                self._transition_to(BridgeState.WRITE_COMPLETE)
                self._transition_to(BridgeState.IDLE)
                return BridgeResponse(
                    status=ErrorCode.SUCCESS,
                    data=self._target_state,
                    confidence=255,
                    timestamp_ns=int(self._sim_time_ns),
                )

            self._retry_count += 1
            if self._retry_count >= MAX_RETRIES:
                # WRITE_VERIFY -> WRITE_FAILED -> IDLE
                self._transition_to(BridgeState.WRITE_FAILED)
                self.defective_cells.add(self._active_cell)
                self._transition_to(BridgeState.IDLE)
                return BridgeResponse(
                    status=ErrorCode.DEFECTIVE_CELL,
                    data=verified,
                    confidence=0,
                    timestamp_ns=int(self._sim_time_ns),
                )

            # WRITE_VERIFY -> WRITE_TRANSITION (retry)
            # (loop continues)

    # ---- calibration protocol ---------------------------------------------

    def _execute_calibration(self, cell_id: int) -> BridgeResponse:
        """
        Calibration: cycle through all 8 states, measure, compute
        correction factors.  Per spec: ~1 us per cell.
        """
        self._advance(CALIBRATION_PER_CELL_NS)

        denom = MU_BOHR * G_FACTOR * MEASUREMENT_FIELD_T ** 2

        for state_idx in range(8):
            eigs = CANONICAL_EIGENVALUES[state_idx]

            # Expected energy for z-axis measurement (representative)
            e_expected = -eigs[2] * denom

            # Simulated "measured" value — in real hardware this comes from
            # the actual sensor.  Here we model it as ideal (correction = 1).
            e_measured = e_expected  # placeholder; real HW would differ

            if abs(e_measured) > 1e-30:
                self._calibration[cell_id, state_idx] = e_expected / e_measured
            else:
                self._calibration[cell_id, state_idx] = 1.0

        self._calibrated[cell_id] = True

        return BridgeResponse(
            status=ErrorCode.SUCCESS,
            data=0,
            confidence=255,
            timestamp_ns=int(self._sim_time_ns),
        )

    # ---- calibration query ------------------------------------------------

    def is_calibrated(self, cell_id: int) -> bool:
        return bool(self._calibrated[cell_id])

    # ---- convenience: binary helpers --------------------------------------

    @staticmethod
    def octal_to_binary(octal_value: int) -> str:
        """Convert 0-7 octal value to 3-bit binary string."""
        if not 0 <= octal_value <= 7:
            raise ValueError(f"octal_value must be 0..7, got {octal_value}")
        return format(octal_value, "03b")

    @staticmethod
    def binary_to_octal(bits: str) -> int:
        """Convert 3-bit binary string to 0-7 octal value."""
        if len(bits) != 3 or not set(bits) <= {"0", "1"}:
            raise ValueError(f"Expected 3-bit string, got {bits!r}")
        return int(bits, 2)

    # ---- parallel block ---------------------------------------------------

    def execute_parallel_block(
        self,
        commands: List[BridgeCommand],
    ) -> List[BridgeResponse]:
        """
        Execute up to 8 commands in a frequency-multiplexed parallel block.
        Total simulated time: 116 ns (per spec).
        """
        if len(commands) > PARALLEL_BLOCK_CELLS:
            raise ValueError(
                f"Parallel block supports at most {PARALLEL_BLOCK_CELLS} "
                f"commands, got {len(commands)}"
            )

        responses: List[BridgeResponse] = []
        # Save time — we model the entire block as one 116 ns chunk
        block_start = self._sim_time_ns

        for i, cmd in enumerate(commands):
            # Each cell uses frequency FREQ_MUX_TABLE_GHZ[i]
            resp = self.execute(cmd)
            responses.append(resp)

        # Override timing: the whole block completes in 116 ns
        self._sim_time_ns = block_start + PARALLEL_BLOCK_NS

        # Update timestamps on responses
        for resp in responses:
            resp.timestamp_ns = int(self._sim_time_ns)

        return responses


# ---------------------------------------------------------------------------
# Self-test when run directly
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Quick smoke test to verify the module loads and basic operations work."""
    proto = MagneticBridgeProtocol(num_cells=8)

    # Calibrate cell 0
    cmd_init = BridgeCommand(CommandType.INIT, cell_id=0)
    resp = proto.execute(cmd_init)
    assert resp.status == ErrorCode.SUCCESS, f"Calibration failed: {resp}"
    assert proto.is_calibrated(0)

    # Write state 5 to cell 0
    cmd_write = BridgeCommand(CommandType.WRITE, cell_id=0, data=5)
    resp = proto.execute(cmd_write)
    assert resp.status == ErrorCode.SUCCESS, f"Write failed: {resp}"
    assert resp.data == 5

    # Read back
    cmd_read = BridgeCommand(CommandType.READ, cell_id=0)
    resp = proto.execute(cmd_read)
    assert resp.status == ErrorCode.SUCCESS, f"Read failed: {resp}"
    assert resp.data == 5

    # Binary conversion round-trip
    bits = MagneticBridgeProtocol.octal_to_binary(5)
    assert bits == "101"
    assert MagneticBridgeProtocol.binary_to_octal(bits) == 5

    # Parallel block
    cmds = [
        BridgeCommand(CommandType.WRITE, cell_id=i, data=i)
        for i in range(8)
    ]
    resps = proto.execute_parallel_block(cmds)
    assert len(resps) == 8
    for i, r in enumerate(resps):
        assert r.status == ErrorCode.SUCCESS

    # Verify all cells read back correctly
    for i in range(8):
        r = proto.execute(BridgeCommand(CommandType.READ, cell_id=i))
        assert r.data == i, f"Cell {i}: expected {i}, got {r.data}"

    # Error code enum coverage
    assert ErrorCode.TIMEOUT == 0x01
    assert ErrorCode.DEFECTIVE_CELL == 0x05

    # State transitions sanity
    assert BridgeState.READ_INIT in STATE_TRANSITIONS[BridgeState.IDLE]

    print(f"All self-tests passed. Simulated time: {proto.sim_time_ns:.1f} ns")


if __name__ == "__main__":
    _self_test()
