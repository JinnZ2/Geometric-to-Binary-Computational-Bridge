identification division.
program-id. aperture-probe.
data division.
working-storage section.
01 initial-value pic x(4) value 'VOID'.
01 oversized-source pic x(6) value 'abcdef'.
01 aperture pic x(3).
01 decimal-aperture pic 9v99.
procedure division.
    move 'PASS' to initial-value
    move oversized-source to aperture
    move 1.239 to decimal-aperture
    display 'INITIAL=' initial-value
    display 'APERTURE=' aperture
    display 'DECIMAL=' decimal-aperture
    goback.
