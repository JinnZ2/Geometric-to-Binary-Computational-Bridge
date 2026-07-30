# Directional Silicon Deposition on Current-Carrying Copper

**Status:** one uncontrolled observation, ~1990s. Mechanism unknown.
**License:** CC0
**What this document is:** a test plan. Not a framework.

Supersedes the ~6,200-word "Theoretical Framework: Energy-Pattern Guided
Materials Organization". Deleted claims are listed with the reason each fails.
Code: `epg_bounds.py`, tested by `tests/test_epg_bounds.py`.

---

## THE OBSERVATION

Plasma Si source + copper substrate carrying lateral current
-> deposition organized directionally across the substrate.

Uncontrolled. No parameter variation. No characterization of the
deposited phase. Terminated over fume generation. Single trial.

Everything below is downstream of one datum.

---

## STATUS OF EVERY CLAIM

    ESTABLISHED   plasma modifies Si surface chemistry predictably
    ESTABLISHED   Si self-organizes in thermal plasma (microspheres,
                  Fe-tipped VLS nanowires) -- ATMOSPHERIC TORCH regime,
                  Tgas ~ 1e4 K. NOT the low-pressure PECVD regime
                  proposed here. different machine.
    ESTABLISHED   wettability patterning guides component-scale
                  fluidic self-assembly
    OBSERVED 1x   directional Si organization under lateral substrate
                  current
    UNTESTED      that the direction had anything to do with the current
    UNTESTED      what the deposited structures were made of

---

## NULL HYPOTHESIS (run this first)

Rolled copper foil is anisotropic by manufacture: rolling texture,
elongated grains, directional surface scratches, preferred
crystallographic orientation. Step-flow nucleation on a textured
surface yields aligned structures with NO field, NO current, NO
gradient.

    TEST: rotate the current 90 deg relative to the foil rolling
          direction.

    pattern follows CURRENT -> field or thermal effect. proceed.
    pattern follows FOIL    -> substrate texture. this document ends.

Cost: two samples. This test was available in 1990 and has never run.

---

## COMPETING MECHANISMS

    ID  MECHANISM                     SIGNATURE        SEPARATED BY
    --  ----------------------------  ---------------  -----------------
    M0  substrate rolling texture     tracks foil      90 deg rotation
    M1  lateral sheath potential      tracks current   run without plasma
        gradient -> ion energy/angle   path, ODD in I  (evaporate Si)
    M2  Joule heating gradient        EVEN in I        reverse polarity:
        -> nucleation density,                          M2/M4 unchanged
        adatom diffusion length
    M3  surface electromigration      ODD in I         kill the plasma:
        (Cu is the textbook case)                       M1 dies, M3 lives
    M4  thermomigration (Soret)       EVEN in I        not separable from
                                                       M2 -- see below
    M5  Cu3Si formation. Cu is a      structures are   EDS / XRD.
        known Si nanowire catalyst;   SILICIDE not Si  swap Cu -> W or Mo
        Cu3Si forms ~150-200 C, far
        below the 802 C eutectic

**M1 parity, corrected.** The table previously listed M1 as "even in I" while
also saying polarity reversal flips both M1 and M3. Those cannot both hold. A
lateral current puts an ohmic drop `V(x) = V0 - I·R·x/L` along the substrate;
plasma potential is ~uniform, so sheath voltage has a lateral slope whose
**sign is set by sign(I)**. Ion energy and incidence angle tilt toward the more
negative end, and reversing the current makes structures lean the other way.
**M1 is ODD in I.** The separator column was right; the signature column was
wrong.

Consequence: polarity reversal separates `{M1,M3}` from `{M2,M4}` and does
**not** separate M1 from M3. Removing the plasma does.

**M2/M4 are not separable by this matrix.** Both are EVEN in I and both survive
without plasma, because both are driven by the same ∇T that Joule heating
produces. The listed separator for M4 — external heater, same ΔT, I = 0 —
reproduces M2 equally well; it separates thermal from electrical, not Soret
drift from nucleation-density variation. The matrix resolves four of five
mechanisms, not five. This does not affect EPG-1, which only asks
current-or-foil.

M5 note: if the structures were Cu3Si, the observation is real and
interesting as catalyst templating -- but it is not silicon
self-organization, and Cu is a lifetime killer banned from CMOS
front-end for exactly this reason. Different finding. Still a finding.

---

## TEST MATRIX

    current:  { +, -, 0 }
    plasma:   { on, off }
    foil:     { rolling || current, rolling _|_ current }

    plus ONE characterization question that settles M5 alone:
      IS THE DEPOSIT SILICON OR COPPER SILICIDE?
      Nobody has looked. EDS answers it in one session.

Three binary discriminators, five mechanisms: 2^3 = 8 cases, of which 6
resolve uniquely, one leaves the M2/M4 pair, and one is **consistent with no
mechanism at all** (even in I but dying without plasma). That last case is the
design catching its own measurement error rather than naming a winner.
`surviving_mechanisms()` returns the compatible set and flags the empty one.

Phase 1 cost: sample prep + SEM/EDS/XRD access. Not $100k-500k.
The expensive program in the previous draft was budgeted before the
$0 test that decides whether the program exists.

---

## PRIOR ART (the previous draft listed these as gaps)

    DIRECTED SELF-ASSEMBLY (DSA), block-copolymer lithography.
      = "design an energy landscape, let material organize, skip the
        mask." Funded at industrial scale since the mid-2000s.
      Two guiding modes, both already named:
        GRAPHOEPITAXY  = topographic guides   ("template substrates")
        CHEMOEPITAXY   = chemical guides      ("surface terminations")

    WHY DSA IS STILL NOT IN PRODUCTION AFTER 20 YEARS:
      defect density. Logic needs ~0.01 defects/cm^2. Dislocations and
      disclinations are THERMODYNAMICALLY REQUIRED in a self-assembled
      phase at finite T. Free-energy floor, not process immaturity.

      QUANTIFIED. At 25 nm pitch a cm^2 holds 1.6e11 features, so
      0.01 defects/cm^2 caps per-feature defect probability at 6.3e-14
      and demands E_f/kT >= 30.4 -- E_f >= 1.37 eV at a 250 C anneal.
      Measured BCP dislocation and disclination energies are a few kT
      to ~10 kT. Short by 3x-10x. `defect_floor()`.

    DIELECTROPHORESIS.  F proportional to grad|E|^2.
      The established mechanism for field-aligning nanostructures.
      Requires a field GRADIENT, not a field. This is what
      "electrical gradients" was reaching for, with an equation.

---

## DELETED CLAIMS

    "accumulated optimization from billions of years of selection"
      109.47 deg = arccos(-1/3). For any four unit vectors,
      |sum(v_i)|^2 = 4 + 2*sum_{i<j} v_i.v_j >= 0, so the six pairwise
      dots sum to at least -2 and average at least -1/3. Maximising the
      smallest separation forces all six equal to -1/3, which is the
      regular tetrahedron. Two lines, no search, no history stored.
      Identical in the first microsecond after nucleosynthesis.
      And diamond cubic is not even the global minimum -- Si-II
      (beta-tin) is more stable above ~11 GPa. `maximin_bound()`.

      WHAT SURVIVES, restated correctly: self-assembly explores
      configuration space IN PARALLEL and can reach states top-down
      patterning cannot. That is a claim about SEARCH, and it is
      defensible.

    "8 vertices per unit cell (octahedral encoding)"
      Diamond cubic has 8 ATOMS per conventional cell: two
      interpenetrating FCC lattices offset by (1/4,1/4,1/4).
      A cube has 8 corners. An octahedron has 6 vertices.
      Si site symmetry is Td. Three distinct things merged.
      Constructed and counted: 8 atoms, 4 nearest neighbours at
      2.3517 A, all six bond angles 109.4712 deg.

    "tetrahedral bonds show directional conductivity"
      Thermal and electrical conductivity in diamond cubic Si are
      ISOTROPIC by cubic symmetry -- Neumann's principle. Averaging any
      symmetric rank-2 tensor over the 24 proper rotations of the cubic
      group returns lambda*I exactly. A theorem, not an approximation:
      no measurement can return a [111]/[100] ratio. `cubic_isotropic()`.

    "information and thermal flow through the same pathways" (as an
    advantage)
      >99% of thermal conduction in undoped Si is phonon transport.
      A lattice/strain-encoded state is destroyed by the same phonon
      flux that carries the heat. Cooling channel = erasure channel.
      Scale: Debye-Waller bond-angle sigma is already 1.89 deg at 300 K
      against an ideal 109.47 deg (`silicon_check.py`). The bath occupies
      the encoding degree of freedom before you write to it.

    "distinguishable electron density states measurable through
     MAGNETIC COUPLING" / "magnetic resonance techniques"
      FIFTH INSTANCE of this fault in Silicon/. Si is diamagnetic,
      chi ~ -4e-6. Si-28 (92.2%) and Si-30 (3.1%) have I = 0, so 95.3%
      of nuclei carry no nuclear moment; only Si-29 (4.7%) has I = 1/2.
      A 5um x 5um x 100nm cell at 50 mT carries m = 4e-19 A.m^2, which
      is 11 orders below a Hall sensor and 7 below a commercial SQUID.
      See `magnetic_authority.py` and FAB-1.
      The readout that does work is already specified in this repo:
      polarization-resolved Raman via Oh selection rules
      (`optical_interface.md`), six <110> projections, complete
      (`tensor_readout.py`, TTM-3).

    "$10M vs $300M, 10-30x capital reduction"
      Litho cost is dominated by overlay and CD control, not the
      exposure tool. A maskless route still needs the full metrology
      stack. Defect density, not capex, is what has blocked DSA.

    "biological self-assembly achieves nanoscale precision"
      (used as the counter to the precision objection)
      Biology achieves it with chaperones, proofreading, and
      ATP-driven repair -- CONTINUOUS WORK INPUT against entropy.
      A passive energy landscape has no such term. The analogy
      argues against the proposal as stated.
      To use it, you have to budget the maintenance power.

---

## CLAIM TABLE

    ID      CLAIM                              FALSIFIER          STATUS
    ------  ---------------------------------  -----------------  --------
    EPG-1   the 1990s effect tracks substrate  pattern follows    UNTESTED
            texture, not current               current under      <- RUN
                                               90 deg rotation
    EPG-2   the deposit was Cu3Si, not Si      EDS shows pure Si  UNTESTED
    EPG-3   the effect is even in polarity     direction          UNTESTED
            (thermal), not odd (electro-       reverses with
            migration)                         polarity
    EPG-4   defect density in self-assembled   a phase below the  LIVE,
            phases has a free-energy floor     entropic floor     30.4 kT
    EPG-5   heat and information cannot share  a phonon-encoded   LIVE
            a phonon pathway                   state surviving
                                               its own heat flux
    EPG-6   109.47 deg stores no optimization  a configuration    DEAD
            history                            beating arccos
                                               (-1/3)
    EPG-7   undoped single-crystal Si is       measured bulk      DEAD
            conductively isotropic             anisotropy
    EPG-8   M1 is ODD in I, so polarity        M1 surviving a     LIVE
            reversal cannot separate it        polarity reversal
            from M3                            unchanged

EPG-4, EPG-6, EPG-7 and EPG-8 are settled by
`python tests/test_epg_bounds.py`. None needed apparatus.
EPG-1, EPG-2, EPG-3 need the two samples.

---

## HAZARD

Silane (SiH4) is pyrophoric -- ignites in air with no ignition
source -- and acutely toxic. Copper oxide fume causes metal fume
fever. Chlorosilane routes evolve HCl. The original experiment was
terminated over fume generation; that was the correct call.

A corrected mechanism is not a licence to run the experiment. Silane
needs gas cabinets, cross-purge, excess-flow shutoff and trained staff.
Nothing here should be attempted outside a facility already equipped
for it.

---

## WHAT THIS DOCUMENT IS FOR

EPG-1 decides whether there is a research program here or a copper
foil artifact. One rotated sample. Everything else waits on it.
