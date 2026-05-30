#!/usr/bin/env python3
import os
import re
import sys

def automate_syntax_upgrade(target_directory):
    """
    Scans all .asm files in the target directory and replaces legacy '?' 
    syntax with '0' inside specific macro invocations to comply with RGBDS 0.9.0.
    """
    # Matches lines that begin with whitespace followed by targeted data macros
    macro_pattern = re.compile(r'^(\s*)(dn|bigBCD6)\s+(.*)$')
    
    modified_files = 0
    for root, dirs, files in os.walk(target_directory):
        for filename in files:
            if filename.endswith(".asm"):
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    continue # Skip any invalid encoded files
                
                file_changed = False
                for i, line in enumerate(lines):
                    match = macro_pattern.match(line)
                    if match:
                        indent, macro_name, args = match.groups()
                        
                        # Only execute if the legacy '?' placeholder is present
                        if '?' in args:
                            # Isolate comments to prevent replacing '?' inside text remarks
                            if ';' in args:
                                code_part, comment_part = args.split(';', 1)
                                new_code = code_part.replace('?', '0')
                                new_args = f"{new_code};{comment_part}"
                            else:
                                new_args = args.replace('?', '0')
                                
                            # Reconstruct and apply the corrected line
                            lines[i] = f"{indent}{macro_name} {new_args}\n"
                            file_changed = True
                
                if file_changed:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    print(f"[+] Upgraded legacy syntax in: {filepath}")
                    modified_files += 1

    print(f"Syntax upgrade complete. Modified {modified_files} source files.")

if __name__ == "__main__":
    # Target the provided directory, or default to current working directory
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    automate_syntax_upgrade(directory)
