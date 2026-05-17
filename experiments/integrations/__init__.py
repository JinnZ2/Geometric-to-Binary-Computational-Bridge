"""
experiments/integrations/

OPT-IN add-ons that bridge the polyglot dispatcher / playground stack
to other parts of the repo. Nothing in here is auto-loaded; the
existing dispatcher.py / dispatcher_v2_energetic.py / runner_api.py /
polyglot_playground.py work fine without it. Import what you want.

Currently:

  registry_adapter.py   wraps the root solver_registry.py Registry as
                        a polyglot_playground.solver_adapter callable.
                        Unlocks ~50 named solvers (GEIS, all 11 bridges,
                        Silicon core/FRET/lattice, NFS) as pipeline
                        steps without writing new runner files.

  bridge_steps.py       turns any bridges/*_encoder.py into a
                        Playground Step factory: bridge_step("magnetic",
                        input_key="geometry", output_key="binary") -> Step.

See experiments/solvers/ for the parallel set of opt-in cells:

  nfs_runner.py         registers the geometric NFS factorization
                        pipeline as a "nfs" cell, racable against the
                        toy Pollard-rho cells (python/c/perl).

  geis_runner.py        registers GEIS encode/decode as a "geis" cell
                        for geis_encode / geis_decode problem families.
"""
