The Geometry of Coupled
Quintessence:
Parameter Sweeps, Fisher
Geometry, and Packing Analysis of a
Dark-Energy–Dark-Matter
Interaction Model
A Consolidated Simulation and Information-Geometry Report
Computational cosmology working report
August 2026
1. Introduction and Motivation
Contents
1. Introduction and Motivation
2. The Model: Coupled Quintessence as a Dynamical System
3. Simulation Engine Design
4. Background Parameter Sweeps
5. Growth Sweeps: The Fifth-Force Observable
6. The Eﬀective (Phantom) Layer
7. Fisher Geometry of the Model Manifold
8. Packing Geometry: Distinguishability and Optimal Covering
Appendix A. Machine-Readable Manifold Graph
9. Conclusions and Caveats
References
1. Introduction and Motivation
Recent baryon acoustic oscillation measurements from the Dark Energy Spectroscopic
Instrument (DESI), combined with CMB and supernova data, hint that the dark energy
equation of state may deviate from the cosmological constant value w = −1
, with a
combined preference in the Chevallier–Polarski–Linder (CPL) plane for w
≈
0−0.9
and a
negative time evolution [1][2]
w <
a 0
. This report consolidates a numerical investigation of
one candidate physics class—coupled quintessence, in which a scalar field ϕ
rolls in an
exponential potential while exchanging energy with pressureless dark matter[3]
—and
reframes the parameter constraints as problems in information geometry.
The investigation proceeded in six stages, each documented below: (i) construction of a
background expansion and linear-growth integration engine; (ii) parameter sweeps over
the potential slope λ β
and coupling ; (iii) an eﬀective CPL layer reaching the phantom
regime w <
0−1
that canonical fields cannot access; (iv) the Fisher (Mahalanobis)
geometry of the model manifold, including the geodesic distance from the canonical model
family to the DESI-preferred region; (v) the intrinsic curvature of that manifold; and (vi) a
packing-geometry analysis quantifying how many statistically distinguishable cosmologies
the model family contains.
2
2. The Model: Coupled Quintessence as a Dynamical System
2. The Model: Coupled Quintessence as a Dynamical System
2.1 Background equations
We adopt the standard dimensionless autonomous formulation for a scalar field with
exponential potential V (ϕ) = V e
−λϕ/M
Pl
0
conformally coupled to dark matter with
˙
strength [4]
β x ≡ /( H M )
ϕ
6 Pl y ≡
2
V /(3H M )
2 z ≡ Ω
. With , , and the radiation
Pl
r
N= ln a
fraction, evolution in e-folds obeys
x′
= −3x +
3 2
λy +
, 2
3 (2 2
2
x 1 + x− y +
3
−
z ) 2
3
β Ω
m
y′
3
= −
λxy + y 1 + x− y + , 2
3 (2 2
2
z )
3
z′
= z−1 + 3x− 3y + z ,
(2 2 )
with state
Ω
m 1 − x−
=
2 y−
2 z Ω
, dark energy fraction =
ϕ x +
2 y2
, and field equation of
(1)
2 2
x− y
w
=
ϕ ≥
2 2
x + y
−1,
where the inequality is saturated only for a vanishing kinetic term—canonical fields
(2)
cannot cross .
w = −1
2.2 Linear growth with a fifth force
δ
Sub-horizon dark matter perturbations obey
m
δ +
1
′′ 1 + (1 − 3w ) δ
m
[2
′
eff ]m
−
3
2
G
eff
Ω δ
=
m 0,
m G
G
2
eff 1 + 2β,
=
G
where the enhancement 1 + 2β2
is the scalar-mediated fifth force between dark matter
(3)
particles. We track and .
f= d ln δ /d ln a
m f σ (z)
8
3. Simulation Engine Design
3.1 Failure of backward integration
An initial implementation integrated the system backward from present-day boundary
conditions (w , Ω )
0 ϕ,0
. A 384-run diagnostic sweep showed that every such model violates
3
4. Background Parameter Sweeps
early-universe bounds catastrophically, with Ω (z ≈
ϕ 1100) ≈ 0.94
regardless of
parameters. This is the well-known attractor problem: generic late-time conditions do not
lie on the early-time scaling trajectory, and thawing quintessence is unstable under time
reversal. Geometrically, the viable models form an exponentially thin separatrix of the flow.
Design principle. Thawing quintessence must be integrated forward from early-universe
initial conditions, with the present-day density targeted by a shooting method.
3.2 Forward engine and shooting
The production engine starts at N
i−14 z ∼ 106
=
( ) in radiation domination with correct
x
=
matter–radiation balance, , , and matter-era perturbation initial
i 0 y
i
=
Ω
ϕ,i
conditions. For each , a bisection on pins (λ, β) Ω
ϕ,i Ω (0) =
ϕ 0.685 ± 5 × 10−4
. The
required initial densities are Ω
∼
ϕ,i 10−21
, making the fine-tuning of thawing models
Λ λ → 0 β= 0
explicit and quantified rather than assumed. A CDM control run ( , )
calibrates all growth observables; because the sub-horizon growth equation systematically
underestimates f f σ
in the radiation era, all 8
results are reported as ratios to the control.
4. Background Parameter Sweeps
Ω
With pinned, 90 models over and were integrated. All
ϕ,0 λ ∈ [0.1, 1.5] β ∈ [0, 0.05]
satisfy the null energy condition and the early-dark-energy bound
Ω (z ≈
ϕ 1100) < 0.02
by construction. The results show a clean degeneracy structure:
Table 1 Background sweep means over negligible at background level)
β
(coupling
λ w
0 w
a λ w
0 w
a
0.1 -0.999 -0.002 0.9 -0.888 -0.171
0.3 -0.990 -0.022 1.1 -0.828 -0.241
0.5 -0.969 -0.058 1.3 -0.754 -0.312
0.7 -0.935 -0.109 1.5 -0.662 -0.378
The potential slope λ (w , w )
alone selects the position on the thawing track in the 0 a
plane;
β ≤ 0.05
is invisible at background level. The track passes above the DESI-preferred
region, with best overlap at λ ≈ 0.8 1.0
– near the 2σ boundary (Figure 1).
4
5. Growth Sweeps: The Fifth-Force Observable
Figure 1 Background sweep: (a) thawing track vs DE
