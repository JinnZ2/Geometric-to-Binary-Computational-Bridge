"""
experiments/metrology/

Substrate-native learning toolkit — vendored from
https://github.com/JinnZ2/Emotions-as-Sensors/tree/main/metrology
License: CC0, stdlib only, no upstream modifications.

What's here (4 of 9 upstream modules; the four most relevant to
runtime AI dispatch via emotion_substrate_dispatcher.py):

  pattern_extractor.py      PEX-001  builds 7-dim ConstraintStatePattern
                                     from raw signal channels (the
                                     input ESD-001 routes on)
  empathy_layer_audit.py    ELA-001  detects label-as-signal collapse
                                     (cited by ESD-001's
                                     verify_label_independence)
  measurement_honesty.py    MH-001..MH-004
                                     epoch stamps, cross-model handoff,
                                     constraint boundaries, and the
                                     InstitutionalCaptureDetector cited
                                     by ESD-001's
                                     cross_check_with_capture_detector
  cooperation_substrate.py  CS-001   substrate-mode detector (survival /
                                     comfort / institutional /
                                     competition-overlay / collapse);
                                     pairs with ELA-001 in the README's
                                     "auditing an existing system"
                                     assembly

esd_integration.py          adapter that calls MH-004 and ELA-001 and
                            feeds their results into the existing
                            cross_check_with_capture_detector /
                            verify_label_independence functions of
                            emotion_substrate_dispatcher.py.

Deferred upstream (not yet pulled in; uncomment to retrieve if needed):

  retroactive_empathy_trainer.py  RET-001  training-time skill scoring
  training_loop.py                TRN-001  5-stage curriculum
  dynamic_architecture_toolkit.py DAT-M1..M3  meta-learning trigger,
                                               energy basins, aux layer
  thermodynamic_overlays.py       TO-001..T0-004  kinetic / holographic /
                                                  canvas / damping
"""
