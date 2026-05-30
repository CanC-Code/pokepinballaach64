#!/usr/bin/env python3
import sys
import re
import os

def parse_sym(sym_path):
    if not os.path.exists(sym_path):
        print(f"CRITICAL ERROR: The symbol file '{sym_path}' does not exist.")
        print("This indicates that 'make' failed to assemble and link the ROM. Please check preceding workflow logs.")
        sys.exit(1)

    symbols = []
    with open(sym_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'): 
                continue
            
            # Matches standard RGBDS symbol format: "Bank:Address Label"
            match = re.match(r'([0-9A-Fa-f]{2,3}):([0-9A-Fa-f]{4})\s+(.+)', line)
            if match:
                bank = int(match.group(1), 16)
                addr = int(match.group(2), 16)
                label = match.group(3).strip()
                symbols.append((bank, addr, label))
    return symbols

def calculate_sizes_and_write(symbols, out_path):
    # Sort primarily by bank, then by memory address to ensure continuous offset blocks
    symbols.sort(key=lambda x: (x[0], x[1]))
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("#pragma once\n")
        f.write("#include <stdint.h>\n\n")
        f.write("struct AssetDefinition {\n")
        f.write("    const char* name;\n")
        f.write("    uint32_t physical_offset;\n")
        f.write("    uint32_t size;\n")
        f.write("    uint8_t original_bank;\n")
        f.write("};\n\n")
        f.write("constexpr AssetDefinition ROM_ASSETS[] = {\n")
        
        for i in range(len(symbols)):
            bank, addr, label = symbols[i]
            
            # Filter out temporary/macro localized labels to keep the header file clean
            if label.startswith('.') or '@' in label: 
                continue

            # Calculate physical ROM offset based on Game Boy MBC architecture
            phys_offset = addr if bank == 0 else (bank * 0x4000) + (addr - 0x4000)
                
            # Calculate size based on the distance to the next symbol in the same bank
            if i + 1 < len(symbols) and symbols[i+1][0] == bank:
                size = symbols[i+1][1] - addr
            else:
                # Fallback: Size extends to the end of the current 16KB bank block
                size = 0x4000 - (addr % 0x4000)
                if size == 0: 
                    size = 0x4000 

            # Sanitize the label string explicitly to strip any corrupted macro expansion characters
            # keeping only alphanumeric characters, spaces, dashes, and underscores.
            clean_label = re.sub(r'[^a-zA-Z0-9_\s\-\[\]().]', '', label)
            
            # Double escape quotes and backslashes for structural safety inside the C++ literal map
            safe_label = clean_label.replace('\\', '\\\\').replace('"', '\\"')
            
            if safe_label: # Only emit if there is a valid string remaining after cleanup
                f.write(f'    {{"{safe_label}", 0x{phys_offset:X}, 0x{size:X}, 0x{bank:02X}}},\n')
            
        f.write("};\n")
        f.write(f"constexpr uint32_t ROM_ASSETS_COUNT = sizeof(ROM_ASSETS) / sizeof(ROM_ASSETS[0]);\n")

if __name__ == '__main__':
    sym_file = "pokepinball.sym"
    out_file = "app/src/main/cpp/asset_dictionary.h"
    
    if len(sys.argv) > 2:
        sym_file = sys.argv[1]
        out_file = sys.argv[2]
        
    print(f"Parsing symbols from {sym_file}...")
    parsed_symbols = parse_sym(sym_file)
    calculate_sizes_and_write(parsed_symbols, out_file)
    print(f"Generated clean C++ asset dictionary at {out_file}")
