#!/usr/bin/env python3
import sys
import re
import os

def parse_sym(sym_path):
    symbols = []
    with open(sym_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'): 
                continue
            # Matches standard RGBDS symbol format: "Bank:Address Label" (e.g., "0C:4800 gfx_title_screen")
            match = re.match(r'([0-9A-Fa-f]{2,3}):([0-9A-Fa-f]{4})\s+(.+)', line)
            if match:
                bank = int(match.group(1), 16)
                addr = int(match.group(2), 16)
                label = match.group(3)
                symbols.append((bank, addr, label))
    return symbols

def calculate_sizes_and_write(symbols, out_path):
    # Sort primarily by bank, then by memory address
    symbols.sort(key=lambda x: (x[0], x[1]))
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, 'w') as f:
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
            
            # Filter out temporary/macro labels to keep the header lightweight
            if label.startswith('.'): 
                continue

            # Calculate physical ROM offset based on Game Boy MBC architecture
            phys_offset = 0
            if bank == 0:
                phys_offset = addr
            else:
                phys_offset = (bank * 0x4000) + (addr - 0x4000)
                
            # Calculate size based on the distance to the next symbol in the same bank
            size = 0
            if i + 1 < len(symbols) and symbols[i+1][0] == bank:
                size = symbols[i+1][1] - addr
            else:
                # Fallback: Size extends to the end of the current 16KB bank
                size = 0x4000 - (addr % 0x4000)
                if size == 0: 
                    size = 0x4000 

            # Escape strings for C++ compliance
            safe_label = label.replace('\\', '\\\\').replace('"', '\\"')
            f.write(f'    {{"{safe_label}", 0x{phys_offset:X}, 0x{size:X}, 0x{bank:02X}}},\n')
            
        f.write("};\n")
        f.write(f"constexpr uint32_t ROM_ASSETS_COUNT = sizeof(ROM_ASSETS) / sizeof(ROM_ASSETS[0]);\n")

if __name__ == '__main__':
    # Default paths targeting standard build outputs and Android CPP directory
    sym_file = "Pokemon Pinball (U) [C][!].sym"
    out_file = "app/src/main/cpp/asset_dictionary.h"
    
    if len(sys.argv) > 2:
        sym_file = sys.argv[1]
        out_file = sys.argv[2]
        
    print(f"Parsing symbols from {sym_file}...")
    parsed_symbols = parse_sym(sym_file)
    calculate_sizes_and_write(parsed_symbols, out_file)
    print(f"Generated C++ asset dictionary at {out_file}")
