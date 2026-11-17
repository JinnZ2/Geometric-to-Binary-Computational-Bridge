      *> =========================================================
      *> LOJBAN METROLOGY COPYBOOK - AUTO-GENERATED
      *> PURPOSE: Immutable ledger for NCM/COBOL semantic bridging
      *> =========================================================

       01  LOJBAN-LEDGER-RECORD.
           05  RECORD-TYPE             PIC X(12).
           05  ENGLISH-CONCEPT         PIC X(20).
           05  SEMANTIC-CLASS          PIC X(20).
           05  VALSI-IDENTIFIER        PIC X(20).
           05  STRUCT-STATUS           PIC X(10).
           05  MAPPING-STATUS          PIC X(10).
           05  PLACE-STRUCTURE         PIC X(100).
           05  AUDIT-REASON            PIC X(100).

      *> Place Structures (Judgments, Comparatives, Emotive, Fear, Other)
       01  ENTRY-TEST           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(20) VALUE 'test                '.
           05  FILLER                  PIC X(20) VALUE 'judgment            '.
           05  FILLER                  PIC X(20) VALUE 'xagme'a             '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(100) VALUE 'x1 fits x2.                                                                                         '.
           05  FILLER                  PIC X(100) VALUE 'test reason                                                                                         '.

      *> Evidentials (Epistemic Markers)
