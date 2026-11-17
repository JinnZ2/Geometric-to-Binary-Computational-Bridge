      *> =========================================================
      *> LOJBAN METROLOGY COPYBOOK - AUTO-GENERATED
      *> PURPOSE: Immutable ledger for NCM/COBOL semantic bridging
      *> =========================================================

       01  LOJBAN-LEDGER-RECORD.
           05  RECORD-TYPE             PIC X(12).
           05  ENGLISH-CONCEPT         PIC X(36).
           05  SEMANTIC-CLASS          PIC X(15).
           05  VALSI-IDENTIFIER        PIC X(10).
           05  STRUCT-STATUS           PIC X(10).
           05  MAPPING-STATUS          PIC X(10).
           05  PLACE-STRUCTURE         PIC X(402).
           05  AUDIT-REASON            PIC X(290).

      *> Place Structures (Judgments, Comparatives, Emotive, Fear, Other)
       01  ENTRY-BETTER         .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'better                              '.
           05  FILLER                  PIC X(15) VALUE 'judgment       '.
           05  FILLER                  PIC X(10) VALUE 'xagmau    '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'xa1=z1 is better than z2 for xa2 by standard xa3, by amount z4.                                                                                                                                                                                                                                                                                                                                                   '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses this lujvo "better ; by the standard of goodness"; it is the xamgu+zmadu compound, i.e. the direct comparative of good. Notes mark xauzma as the canonical form, xagmau as the form in use.                                                                                     '.

       01  ENTRY-WORSE          .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'worse                               '.
           05  FILLER                  PIC X(15) VALUE 'judgment       '.
           05  FILLER                  PIC X(10) VALUE 'xagme'a   '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'xa1=m1 is worse than/not as good as m2 for xa2 by standard xa3, by amount m4.                                                                                                                                                                                                                                                                                                                                     '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses this lujvo "worse ; by the standard of goodness"; xamgu+mleca compound, the direct comparative antonym of xagmau.                                                                                                                                                               '.

       01  ENTRY-BEST           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'best                                '.
           05  FILLER                  PIC X(15) VALUE 'judgment       '.
           05  FILLER                  PIC X(10) VALUE 'xagrai    '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 't1=x1 is the best among set/range t4 for x2 by standard x3.                                                                                                                                                                                                                                                                                                                                                       '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses this entry "best ; surpassing all others" / "superlative in goodness"; it is the xamgu+traji (goodness-superlative) lujvo. The same entry carries a second definition glossed "optimal" (see "optimal").                                                                        '.

       01  ENTRY-WORST          .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'worst                               '.
           05  FILLER                  PIC X(15) VALUE 'judgment       '.
           05  FILLER                  PIC X(10) VALUE 'xlarai    '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 't1=x1 is the worst among set/range t4 for x2 by standard x3.                                                                                                                                                                                                                                                                                                                                                      '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses this lujvo "worst" (xlali+traji, badness-superlative), mirror image of xagrai.                                                                                                                                                                                                  '.

       01  ENTRY-APPROPRIATE    .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'appropriate                         '.
           05  FILLER                  PIC X(15) VALUE 'judgment       '.
           05  FILLER                  PIC X(10) VALUE 'mapti     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 fits/matches/suits/is compatible/appropriate/corresponds to/with x2 in property/aspect x3.                                                                                                                                                                                                                                                                                                                     '.
           05  FILLER                  PIC X(290) VALUE 'No valsi is glossed "appropriate" in jbovlaste; mapti's definition itself contains "appropriate" and its fit/suit/match sense covers appropriateness of x1 for x2 in aspect x3.                                                                                                                   '.

       01  ENTRY-SUPERIOR       .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'superior                            '.
           05  FILLER                  PIC X(15) VALUE 'judgment       '.
           05  FILLER                  PIC X(10) VALUE 'zmadu     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 exceeds/is more than x2 in property/quantity x3 (ka/ni) by amount/excess x4.                                                                                                                                                                                                                                                                                                                                   '.
           05  FILLER                  PIC X(290) VALUE 'In the judgment sense, "x1 is superior to x2 in respect x3" is the exceeds-relation; jbovlaste's "superior" gloss entries are anatomical only (claco'uklo, claco'umau), so zmadu is the fitting gismu.                                                                                            '.

       01  ENTRY-INFERIOR       .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'inferior                            '.
           05  FILLER                  PIC X(15) VALUE 'judgment       '.
           05  FILLER                  PIC X(10) VALUE 'tolba'i   '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'b1 is low/inferior/abject in property b2 (ka) by standard b3.                                                                                                                                                                                                                                                                                                                                                     '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses this lujvo "inferior" directly (to'e+banli, the opposite of great).                                                                                                                                                                                                             '.

       01  ENTRY-MORE           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'more                                '.
           05  FILLER                  PIC X(15) VALUE 'comparative    '.
           05  FILLER                  PIC X(10) VALUE 'zmadu     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 exceeds/is more than x2 in property/quantity x3 (ka/ni) by amount/excess x4.                                                                                                                                                                                                                                                                                                                                   '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste keys the gloss "more" to zmadu; it is the base comparative gismu (more than x2 in property x3 by margin x4).                                                                                                                                                                            '.

       01  ENTRY-LESS           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'less                                '.
           05  FILLER                  PIC X(15) VALUE 'comparative    '.
           05  FILLER                  PIC X(10) VALUE 'mleca     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 is less than x2 in property/quantity x3 (ka/ni) by amount x4.                                                                                                                                                                                                                                                                                                                                                  '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste keys the gloss "less" to mleca; it is zmadu's direct antonym.                                                                                                                                                                                                                           '.

       01  ENTRY-GREATER        .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'greater                             '.
           05  FILLER                  PIC X(15) VALUE 'comparative    '.
           05  FILLER                  PIC X(10) VALUE 'zmadu     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 exceeds/is more than x2 in property/quantity x3 (ka/ni) by amount/excess x4.                                                                                                                                                                                                                                                                                                                                   '.
           05  FILLER                  PIC X(290) VALUE 'No valsi is glossed "greater" in jbovlaste; "greater than x2 in property x3" is the zmadu relation (same wordslot as "more").                                                                                                                                                                     '.

       01  ENTRY-SMALLER        .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'smaller                             '.
           05  FILLER                  PIC X(15) VALUE 'comparative    '.
           05  FILLER                  PIC X(10) VALUE 'cmamau    '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'z1 is smaller than z2 in dimension c2 by margin z4.                                                                                                                                                                                                                                                                                                                                                               '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses this lujvo "smaller" directly (cmalu+zmadu).                                                                                                                                                                                                                                    '.

       01  ENTRY-OPTIMAL        .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'optimal                             '.
           05  FILLER                  PIC X(15) VALUE 'comparative    '.
           05  FILLER                  PIC X(10) VALUE 'xagrai    '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 't1=x1 is optimal in property t2 of extremity t3 among range t4.                                                                                                                                                                                                                                                                                                                                                   '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste's second definition of xagrai is glossed "best ; optimal" and "optimal"; the xamgu+traji compound covers optimum-as-best directly.                                                                                                                                                      '.

       01  ENTRY-EFFICIENT      .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'efficient                           '.
           05  FILLER                  PIC X(15) VALUE 'comparative    '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(402) VALUE 'NO DEFINITION                                                                                                                                                                                                                                                                                                                                                                                                     '.
           05  FILLER                  PIC X(290) VALUE 'No valsi is glossed or keyworded "efficient"/"efficiency": the jbovlaste English gloss index has no entry and the keyword lookup returns nothing for either term; no gismu expresses efficiency. tadji (method) and pilno (use) were considered and rejected — neither is an efficiency predicate.'.

       01  ENTRY-EFFECTIVE      .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'effective                           '.
           05  FILLER                  PIC X(15) VALUE 'comparative    '.
           05  FILLER                  PIC X(10) VALUE 'bapli     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 [force] (ka) forces/compels event x2 to occur; x1 determines property x2 to manifest.                                                                                                                                                                                                                                                                                                                          '.
           05  FILLER                  PIC X(290) VALUE 'bapli is the only valsi carrying the official gloss "effective". The sense is narrow — an effective/compelling force that makes x2 happen (notes: "requires success") — not general "produces the intended result". Reported as the best available, flagged as a sense mismatch.                  '.

       01  ENTRY-WARM           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'warm                                '.
           05  FILLER                  PIC X(15) VALUE 'emotive        '.
           05  FILLER                  PIC X(10) VALUE 'xendo     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 (person) is kind to x2 in actions/behavior x3.                                                                                                                                                                                                                                                                                                                                                                 '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste's "warm" glosses are all temperature senses (mligla, kufygla, glare); no gismu is glossed "warm" in the emotive sense. xendo (kind in behavior) is the nearest interpersonal-warmth gismu.                                                                                              '.

       01  ENTRY-COLD           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'cold                                '.
           05  FILLER                  PIC X(15) VALUE 'emotive        '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(402) VALUE 'NO DEFINITION                                                                                                                                                                                                                                                                                                                                                                                                     '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste's "cold" glosses are temperature (lenku, tolkuflenku) or illness (zuKAM); nothing covers the emotive sense. A tolxendo (unkind) record exists but carries no English definition, so there is no quotable place structure. Not invented.                                                 '.

       01  ENTRY-FRIENDLY       .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'friendly                            '.
           05  FILLER                  PIC X(15) VALUE 'emotive        '.
           05  FILLER                  PIC X(10) VALUE 'pendo     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 is/acts as a friend of/to x2 (experiencer); x2 befriends x1.                                                                                                                                                                                                                                                                                                                                                   '.
           05  FILLER                  PIC X(290) VALUE 'No valsi is glossed "friendly"; pendo is the base friend predicate and its "acts as a friend" phrasing covers friendly behavior.                                                                                                                                                                  '.

       01  ENTRY-HOSTILE        .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'hostile                             '.
           05  FILLER                  PIC X(15) VALUE 'emotive        '.
           05  FILLER                  PIC X(10) VALUE 'le'onmo   '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 feels/is aggressive/hostile/antagonistic towards x2                                                                                                                                                                                                                                                                                                                                                            '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses this lujvo "aggressive/hostile/antagonistic" — the hostile feeling itself, matching the emotive class.                                                                                                                                                                          '.

       01  ENTRY-AGGRESSIVE     .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'aggressive                          '.
           05  FILLER                  PIC X(15) VALUE 'emotive        '.
           05  FILLER                  PIC X(10) VALUE 'le'onmo   '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 feels/is aggressive/hostile/antagonistic towards x2                                                                                                                                                                                                                                                                                                                                                            '.
           05  FILLER                  PIC X(290) VALUE 'Same jbovlaste entry as "hostile"; its notes state it denotes feeling the emotions associated with attacking, unlike gunta which is the active attack — hence it fits the emotive class.                                                                                                          '.

       01  ENTRY-COMPASSIONATE  .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'compassionate                       '.
           05  FILLER                  PIC X(15) VALUE 'emotive        '.
           05  FILLER                  PIC X(10) VALUE 'kecti     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 (person) pities/feels sorry for x2 (person) about x3 (abstraction).                                                                                                                                                                                                                                                                                                                                            '.
           05  FILLER                  PIC X(290) VALUE 'No valsi is glossed "compassionate"; kecti (pities/feels sorry for) is the compassion gismu.                                                                                                                                                                                                      '.

       01  ENTRY-SAFE           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'safe                                '.
           05  FILLER                  PIC X(15) VALUE 'fear           '.
           05  FILLER                  PIC X(10) VALUE 'snura     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 is secure/safe from threat x2 (event).                                                                                                                                                                                                                                                                                                                                                                         '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste glosses snura "safe ; secure"; the threat-from-which place (x2) matches the fear-class slot exactly.                                                                                                                                                                                    '.

       01  ENTRY-DANGEROUS      .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'dangerous                           '.
           05  FILLER                  PIC X(15) VALUE 'fear           '.
           05  FILLER                  PIC X(10) VALUE 'ckape     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 is perilous/dangerous/potentially harmful to x2 under conditions x3.                                                                                                                                                                                                                                                                                                                                           '.
           05  FILLER                  PIC X(290) VALUE 'No valsi is glossed "dangerous"; ckape's definition itself contains "dangerous" (perilous/potentially harmful to x2), the exact sense.                                                                                                                                                            '.

       01  ENTRY-THREAT         .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'threat                              '.
           05  FILLER                  PIC X(15) VALUE 'fear           '.
           05  FILLER                  PIC X(10) VALUE 'capnu'e   '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 threatens x2 with x3 (danger, peril).                                                                                                                                                                                                                                                                                                                                                                          '.
           05  FILLER                  PIC X(290) VALUE 'Closest attested threat predicate in jbovlaste. It is agentive ("threatens"), not the threat itself; no gismu has the form "x1 is a threat to x2" — that role exists only as a place of other predicates (snura x2, bandu x3, ckape). Flagged as a role mismatch.                                 '.

       01  ENTRY-IMMINENT       .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'imminent                            '.
           05  FILLER                  PIC X(15) VALUE 'fear           '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(10) VALUE 'VOID      '.
           05  FILLER                  PIC X(402) VALUE 'NO DEFINITION                                                                                                                                                                                                                                                                                                                                                                                                     '.
           05  FILLER                  PIC X(290) VALUE 'No valsi is glossed or keyworded "imminent" in jbovlaste. A bavlami record exists but carries no English definition, so nothing quotable; balvi is bare temporal ordering (future of x2), not imminence. Not invented.                                                                            '.

       01  ENTRY-NEAR           .
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'near                                '.
           05  FILLER                  PIC X(15) VALUE 'other          '.
           05  FILLER                  PIC X(10) VALUE 'jibni     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'PROPOSED  '.
           05  FILLER                  PIC X(402) VALUE 'x1 is near/close to/approximates x2 in property/quantity x3 (ka/ni).                                                                                                                                                                                                                                                                                                                                              '.
           05  FILLER                  PIC X(290) VALUE 'jbovlaste keys the gloss "near" to jibni; the base gismu for proximity in property/quantity x3.                                                                                                                                                                                                   '.

       01  ENTRY-GLARE-(RECALL-C.
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'glare (recall check)                '.
           05  FILLER                  PIC X(15) VALUE 'recall_check   '.
           05  FILLER                  PIC X(10) VALUE 'glare     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'DIFFERS   '.
           05  FILLER                  PIC X(402) VALUE 'x1 is hot/[warm] by standard x2.                                                                                                                                                                                                                                                                                                                                                                                  '.
           05  FILLER                  PIC X(290) VALUE 'recalled: "x1 hot by standard x2" — source: "x1 is hot/[warm] by standard x2." — same place count; recall drops "is" and the "/[warm]" variant (gismu list wording identical: "x1 is hot/[warm] by standard x2").                                                                                 '.

       01  ENTRY-SNURA-(RECALL-C.
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'snura (recall check)                '.
           05  FILLER                  PIC X(15) VALUE 'recall_check   '.
           05  FILLER                  PIC X(10) VALUE 'snura     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'DIFFERS   '.
           05  FILLER                  PIC X(402) VALUE 'x1 is secure/safe from threat x2 (event).                                                                                                                                                                                                                                                                                                                                                                         '.
           05  FILLER                  PIC X(290) VALUE 'recalled: "x1 safe from threat x2" — source: "x1 is secure/safe from threat x2 (event)." — same place count; recall drops "is", "secure/", and the "(event)" qualifier on x2.                                                                                                                     '.

       01  ENTRY-JIBNI-(RECALL-C.
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'jibni (recall check)                '.
           05  FILLER                  PIC X(15) VALUE 'recall_check   '.
           05  FILLER                  PIC X(10) VALUE 'jibni     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'DIFFERS   '.
           05  FILLER                  PIC X(402) VALUE 'x1 is near/close to/approximates x2 in property/quantity x3 (ka/ni).                                                                                                                                                                                                                                                                                                                                              '.
           05  FILLER                  PIC X(290) VALUE 'recalled: "x1 near x2 in property x3" — source: "x1 is near/close to/approximates x2 in property/quantity x3 (ka/ni)." — same place count; recall drops "is", "/close to/approximates", "/quantity", and "(ka/ni)".                                                                               '.

       01  ENTRY-ZMADU-(RECALL-C.
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'zmadu (recall check)                '.
           05  FILLER                  PIC X(15) VALUE 'recall_check   '.
           05  FILLER                  PIC X(10) VALUE 'zmadu     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'DIFFERS   '.
           05  FILLER                  PIC X(402) VALUE 'x1 exceeds/is more than x2 in property/quantity x3 (ka/ni) by amount/excess x4.                                                                                                                                                                                                                                                                                                                                   '.
           05  FILLER                  PIC X(290) VALUE 'recalled: "x1 exceeds x2 in property x3 by amount x4" — source: "x1 exceeds/is more than x2 in property/quantity x3 (ka/ni) by amount/excess x4." — same place count; recall drops "/is more than", "/quantity", "(ka/ni)", and "/excess".                                                        '.

       01  ENTRY-XAMGU-(RECALL-C.
           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.
           05  FILLER                  PIC X(36) VALUE 'xamgu (recall check)                '.
           05  FILLER                  PIC X(15) VALUE 'recall_check   '.
           05  FILLER                  PIC X(10) VALUE 'xamgu     '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'DIFFERS   '.
           05  FILLER                  PIC X(402) VALUE 'x1 (object/event) is good/beneficial/nice/[acceptable] for x2 by standard x3.                                                                                                                                                                                                                                                                                                                                     '.
           05  FILLER                  PIC X(290) VALUE 'recalled: "x1 good for x2 by standard x3" — source: "x1 (object/event) is good/beneficial/nice/[acceptable] for x2 by standard x3." — same place count; recall drops "(object/event)", "is", and "/beneficial/nice/[acceptable]".                                                                 '.

      *> Evidentials (Epistemic Markers)
       01  ENTRY-I-OBSERVE      .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I observe                           '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'za'a      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[zgana] I observe" ; "A bridi marked by za'a is based on perception or direct observation by the speaker."                                                                                                                                                                                                                                                                                                       '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from zgana (observe).                                                                                                                                                                                    '.

       01  ENTRY-I-HEAR-(HEARSAY.
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I hear (hearsay)                    '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'ti'e      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[tirna] I hear (hearsay)" ; "A bridi marked by ti'e is relayed information from some source other than the speaker. There is no necessary implication that the information was relayed via the speaker's ears; what we read in a newspaper is an equally good example of ti'e, unless we have personal knowledge of the content."                                                                                '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from tirna (hear).                                                                                                                                                                                       '.

       01  ENTRY-I-STATE        .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I state                             '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'ju'a      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[jufra] I state" ; "Finally, the evidential ju'a is used to avoid stating a specific basis for a statement. It can also be used when the basis for the speaker's statement is not covered by any other evidential."                                                                                                                                                                                              '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from jufra (sentence).                                                                                                                                                                                   '.

       01  ENTRY-I-DEFINE       .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I define                            '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'ca'e      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"I define" ; "A bridi marked by ca'e is true because the speaker says so. In addition to definitions of words, ca'e is also appropriate in what are called performatives, where the very act of speaking the words makes them true."                                                                                                                                                                              '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; no rafsi source given in the CLL table.                                                                                                                                                                          '.

       01  ENTRY-I-OPINE        .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I opine                             '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'pe'i      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[pensi] I opine" ; "A bridi marked by pe'i is the opinion of the speaker."                                                                                                                                                                                                                                                                                                                                       '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from pensi (think).                                                                                                                                                                                      '.

       01  ENTRY-I-POSTULATE    .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I postulate                         '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'ru'a      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[sruma] I postulate" ; "A bridi marked by ru'a is an assumption made by the speaker."                                                                                                                                                                                                                                                                                                                            '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from sruma (assume).                                                                                                                                                                                     '.

       01  ENTRY-I-KNOW-BY-CULTU.
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I know by cultural means            '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'ka'u      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[kulnu] I know by cultural means" ; "A bridi marked by ka'u is one held to be true in the speaker's cultural context, as a matter of myth or custom, for example."                                                                                                                                                                                                                                               '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from kulnu (culture).                                                                                                                                                                                    '.

       01  ENTRY-I-KNOW-BY-INTER.
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I know by internal experience       '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'se'o      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[senva] I know by internal experience" ; "On the other hand, se'o marks a bridi whose truth is asserted by the speaker as a result of an internal experience not directly available to others, such as a dream, vision, or personal revelation."                                                                                                                                                                 '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from senva (dream).                                                                                                                                                                                      '.

       01  ENTRY-I-CONCLUDE     .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I conclude                          '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'ja'o      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[jalge] I conclude" ; "A bridi marked by ja'o is a conclusion by the speaker based on other (stated or unstated) information or ideas. Rough English equivalents of ja'o are “thus” and “therefore”."                                                                                                                                                                                                            '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); gloss and defining sentence quoted verbatim; derived from jalge (result).                                                                                                                                                                                     '.

       01  ENTRY-I-EXPECT--I-EX .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I expect / I experience / I remember'.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'ba'a      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[balvi] I expect / I experience / I remember" ; "The three scale positions of ba'a, when attached to a bridi, indicate that it is based on the speaker's view of the real world. Thus ba'a means that the statement represents a future event as anticipated by the speaker; ba'acu'i, a present event as experienced by the speaker; ba'anai, a past event as remembered by the speaker."                       '.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); NOT in the requester's list — added per instruction 2. Gloss and defining sentence quoted verbatim; derived from balvi (future). Scalar: ba'a / ba'acu'i / ba'anai.                                                                                           '.

       01  ENTRY-I-GENERALIZE-- .
           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.
           05  FILLER                  PIC X(36) VALUE 'I generalize / I particularize      '.
           05  FILLER                  PIC X(15) VALUE 'evidential     '.
           05  FILLER                  PIC X(10) VALUE 'su'a      '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(10) VALUE 'OBSERVED  '.
           05  FILLER                  PIC X(402) VALUE '"[sucta] I generalize / I particularize" ; "A bridi marked by su'a is a generalization by the speaker based on other (stated or unstated) information or ideas. The difference between su'a and ja'o is that ja'o suggests some sort of reasoning or deduction (not necessarily rigorous), whereas su'a suggests some sort of induction or pattern recognition from existing examples (not necessarily rigorous)."'.
           05  FILLER                  PIC X(290) VALUE 'CLL §13.11 evidential (selma'o UI); NOT in the requester's list — added per instruction 2. Gloss and defining sentence quoted verbatim; derived from sucta (abstract). Scale opposite su'anai = abduction.                                                                                        '.

