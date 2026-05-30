#!/usr/bin/env python3
import os
import re
import sys

def upgrade_line_syntax(line: str) -> tuple[str, bool]:
    """
    Parses an assembly line, strictly separating active code, string literals, 
    and comments to safely clear legacy '?' characters without corrupting text assets.
    """
    # If the line is empty or completely a comment, skip it
    if not line.strip() or line.strip().startswith(';'):
        return line, False

    # Isolate trailing comments to preserve text inside notes
    comment_parts = line.split(';', 1)
    code_part = comment_parts[0]
    comment_part = f";{comment_parts[1]}" if len(comment_parts) > 1 else ""

    # Tokenize strings to protect text variables like: db "Where is Pikachu?"
    # Split by double quotes, keeping track of inside vs outside strings
    string_tokens = re.split(r'(".*?")', code_part)
    
    line_modified = False
    for i in range(len(string_tokens)):
        token = string_tokens[i]
        # Only modify if we are outside of a string literal
        if not (token.startswith('"') and token.endswith('"')):
            if '?' in token:
                # Loop-based replacement using capturing groups to avoid variable-width lookbehinds.
                # Matches '?' bounded by line boundaries or non-alphanumeric/non-underscore characters.
                pattern = r'(^|[^a-zA-Z0-9_])\?([^a-zA-Z0-9_]|$)'
                
                # We loop to catch adjacent occurrences (e.g., "dn ?,?") cleanly
                while True:
                    updated_token = re.sub(pattern, r'\1踩0\2', token)
                    # Use a unique placeholder '踩0' temporarily to avoid recursive matching
                    if updated_token == token:
                        break
                    token = updated_token
                    line_modified = True
                
                # Restore the true '0' value from our temporary placeholder
                if line_modified:
                    string_tokens[i] = token.replace('踩0', '0')

    # Re-stitch the line components back together safely
    new_line = "".join(string_tokens) + comment_part
    return new_line, line_modified

def automate_syntax_upgrade(target_directory):
    """
    Recursively scans all .asm files in the target folder to convert legacy 
    unmapped '?' tokens into compliant '0' values for the RGBDS 0.9.0 engine.
    """
    modified_files = 0
    
    for root, dirs, files in os.walk(target_directory):
        for filename in files:
            if filename.endswith(".asm"):
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    # Fallback context safety layer for legacy character maps
                    try:
                        with open(filepath, 'r', encoding='shift_jis') as f:
                            lines = f.readlines()
                    except Exception:
                        continue
                
                file_changed = False
                for i, line in enumerate(lines):
                    updated_line, line_changed = upgrade_line_syntax(line)
                    if line_changed:
                        lines[i] = updated_line
                        file_changed = True
                
                if file_changed:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    print(f"[+] Cleaned legacy syntax tokens in: {filepath}")
                    modified_files += 1

    print(f"Syntax upgrade complete. Modified {modified_files} source files.")

if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    automate_syntax_upgrade(directory)
