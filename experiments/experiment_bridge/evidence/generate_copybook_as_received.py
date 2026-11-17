import json

def get_max_len(data_list, field):
    """Dynamically find the longest string to set the PIC X sizes."""
    lengths = [len(str(item.get(field, ""))) for item in data_list]
    return max(lengths) if lengths else 20

def generate_cobol_copybook(json_file, output_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    place_structures = data.get('place_structures', [])
    evidentials = data.get('evidentials', [])

    # Calculate dynamic lengths for the text fields
    max_eng = max(get_max_len(place_structures, 'english'), get_max_len(evidentials, 'english'))
    max_class = max(get_max_len(place_structures, 'class'), get_max_len(evidentials, 'class'))
    max_gismu = max(get_max_len(place_structures, 'gismu'), get_max_len(evidentials, 'gismu'))
    max_struct = max(get_max_len(place_structures, 'place_structure_verbatim'), get_max_len(evidentials, 'place_structure_verbatim'))
    max_reason = max(get_max_len(place_structures, 'mapping_reason'), get_max_len(evidentials, 'mapping_reason'))
    
    # Ensure minimum lengths for standard headers
    max_eng = max(max_eng, 15)
    max_class = max(max_class, 15)
    max_gismu = max(max_gismu, 10)
    max_struct = max(max_struct, 100) # Large aperture for the verbatim string
    max_reason = max(max_reason, 100)

    with open(output_file, 'w') as f:
        f.write("      *> =========================================================\n")
        f.write("      *> LOJBAN METROLOGY COPYBOOK - AUTO-GENERATED\n")
        f.write("      *> PURPOSE: Immutable ledger for NCM/COBOL semantic bridging\n")
        f.write("      *> =========================================================\n\n")
        
        f.write("       01  LOJBAN-LEDGER-RECORD.\n")
        f.write("           05  RECORD-TYPE             PIC X(12).\n")
        f.write("           05  ENGLISH-CONCEPT         PIC X({:02d}).\n".format(max_eng))
        f.write("           05  SEMANTIC-CLASS          PIC X({:02d}).\n".format(max_class))
        f.write("           05  VALSI-IDENTIFIER        PIC X({:02d}).\n".format(max_gismu))
        f.write("           05  STRUCT-STATUS           PIC X(10).\n")
        f.write("           05  MAPPING-STATUS          PIC X(10).\n")
        f.write("           05  PLACE-STRUCTURE         PIC X({:03d}).\n".format(max_struct))
        f.write("           05  AUDIT-REASON            PIC X({:03d}).\n\n".format(max_reason))
        
        f.write("      *> Place Structures (Judgments, Comparatives, Emotive, Fear, Other)\n")
        for item in place_structures:
            # Default to spaces if null
            gismu = item.get('gismu') if item.get('gismu') else "VOID"
            struct = item.get('place_structure_verbatim') if item.get('place_structure_verbatim') else "NO DEFINITION"
            
            # COBOL strings are space-padded by default. We format the VALUE clauses.
            f.write("       01  ENTRY-{: <15}.\n".format(str(item['english']).upper()[:15].replace(' ', '-')))
            f.write("           05  FILLER                  PIC X(12) VALUE 'PLACE-STRUCT'.\n")
            f.write("           05  FILLER                  PIC X({:02d}) VALUE '{: <{}}'.\n".format(max_eng, item['english'], max_eng))
            f.write("           05  FILLER                  PIC X({:02d}) VALUE '{: <{}}'.\n".format(max_class, item['class'], max_class))
            f.write("           05  FILLER                  PIC X({:02d}) VALUE '{: <{}}'.\n".format(max_gismu, gismu, max_gismu))
            f.write("           05  FILLER                  PIC X(10) VALUE '{: <10}'.\n".format(item['structure_status']))
            f.write("           05  FILLER                  PIC X(10) VALUE '{: <10}'.\n".format(item['mapping_status']))
            f.write("           05  FILLER                  PIC X({:03d}) VALUE '{: <{}}'.\n".format(max_struct, struct[:max_struct], max_struct))
            f.write("           05  FILLER                  PIC X({:03d}) VALUE '{: <{}}'.\n\n".format(max_reason, item['mapping_reason'][:max_reason], max_reason))

        f.write("      *> Evidentials (Epistemic Markers)\n")
        for item in evidentials:
            gismu = item.get('gismu') if item.get('gismu') else "VOID"
            struct = item.get('place_structure_verbatim') if item.get('place_structure_verbatim') else "NO DEFINITION"

            f.write("       01  ENTRY-{: <15}.\n".format(str(item['english']).upper()[:15].replace(' ', '-').replace('/', '')))
            f.write("           05  FILLER                  PIC X(12) VALUE 'EVIDENTIAL  '.\n")
            f.write("           05  FILLER                  PIC X({:02d}) VALUE '{: <{}}'.\n".format(max_eng, item['english'], max_eng))
            f.write("           05  FILLER                  PIC X({:02d}) VALUE '{: <{}}'.\n".format(max_class, item['class'], max_class))
            f.write("           05  FILLER                  PIC X({:02d}) VALUE '{: <{}}'.\n".format(max_gismu, gismu, max_gismu))
            f.write("           05  FILLER                  PIC X(10) VALUE '{: <10}'.\n".format(item['structure_status']))
            f.write("           05  FILLER                  PIC X(10) VALUE '{: <10}'.\n".format(item['mapping_status']))
            f.write("           05  FILLER                  PIC X({:03d}) VALUE '{: <{}}'.\n".format(max_struct, struct[:max_struct], max_struct))
            f.write("           05  FILLER                  PIC X({:03d}) VALUE '{: <{}}'.\n\n".format(max_reason, item['mapping_reason'][:max_reason], max_reason))

    print(f"Copybook successfully generated at {output_file}")

# Run the generator
generate_cobol_copybook('lojban_wordslot_reference.json', 'lojban_ledger.cpy')
