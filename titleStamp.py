import os
import re as regex
import subprocess
import tempfile
import argparse

# ======================================================================================================================
# =========================================== START OF CONFIG ==========================================================
# ======================================================================================================================

# =========================================== REGEX PATTERNS ===========================================================
# ! Ensure the order of the patterns are unique and cannot have similarity conflicts with others !
pattern_OBS = r"(\d{4})\-(\d{2})\-(\d{2}) (\d{2})\-(\d{2})\-(\d{2})"                    # 2026-02-27 21-49-06
pattern_NVIDIA = r"(\d{4})\.(\d{2})\.(\d{2}) - (\d{2})\.(\d{2})\.(\d{2})"               # 2024.09.30 - 20.56.37.04 (NOT INCLUDING "".04")
pattern_VRChat = r"_(\d{4})\-(\d{2})\-(\d{2})_(\d{2})\-(\d{2})\-(\d{2})"                # _2021-09-01_21-20-52
pattern_Screenshot = r"Screenshot (\d{4})\-(\d{2})\-(\d{2}) (\d{2})(\d{2})(\d{2})"      # Screenshot 2026-04-18 175856.png
pattern_Steam_Screenshot = r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})_1"              # 20190119184452_1
pattern_apple = r"IMG\_(\d{4})(\d{2})(\d{2})\_(\d{2})(\d{2})(\d{2})"                    # IMG_20260502_022119
pattern_Samsung = r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})"                        # 20260506_155609
pattern_Generic = r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})"                         # 20260509105257 (Includes many typical Android media regex)


# Pre-compile regex patterns for performance scaling
PATTERNS = [
    regex.compile(pattern_OBS),
    regex.compile(pattern_NVIDIA),
    regex.compile(pattern_VRChat),
    regex.compile(pattern_Screenshot),
    regex.compile(pattern_Steam_Screenshot),
    regex.compile(pattern_Samsung),
    regex.compile(pattern_Generic),
    regex.compile(pattern_apple)
]

# ======================================================================================================================

# =========================================== SUB REGEX PATTERNS ===========================================================
# Regex to match (IF NOT FOUND IN MAIN PATTERN)
# TODO: Unfinished, the goal was to handle shorter patterns if the original pattern fails
sub_pattern_VRChat = r"_(\d{4})\-(\d{2})\-(\d{2})"    # _2021-09-01
# ======================================================================================================================

extensions = (".mp4", ".mkv", ".png", ".jpeg", ".jpg", ".heic")

# ======================================================================================================================
# =========================================== END OF CONFIG ============================================================
# ======================================================================================================================

error_count = 0
skipped_count = 0
processed_count = 0
access_denied_count = 0
ps_commands = []

def print_summary():
    print(f"\n===============================")
    print(f"PROCESSED: {processed_count}")
    print(f"SKIPPED: {skipped_count}")
    print(f"ACCESS DENIED (Read only?): {access_denied_count}")
    print(f"ERROR: {error_count}")
    print("===============================\n")

def execute_recursively():
    directory = os.getcwd()
    for root, dirs, files in os.walk(directory):
        change_timestamp_with_title(root, files)

def execute_only_path():
    directory = os.getcwd()
    files = os.listdir(directory)
    change_timestamp_with_title(directory, files)

def change_timestamp_with_title(root, files):
    global error_count, skipped_count, processed_count, ps_commands
    for filename in files:
        if not filename.lower().endswith(extensions):
            print(f"Skipping {filename} - Invalid Extension.")
            skipped_count += 1
            continue
        
        # Checks for appropiate regex patterns
        regex_match = next((match for pattern in PATTERNS if (match := pattern.search(filename))), None)

        if regex_match:
            # Extract parts
            year, month, day, hour, minute, second = regex_match.groups()
            
            # Format for PowerShell (YYYY-MM-DD HH:MM:SS is safest for parsing)
            formatted_date = f"{year}-{month}-{day} {hour}:{minute}:{second}"
            
            full_path = os.path.join(root, filename)
            modified_path = full_path.replace("'", "''")
            
            # Form the raw powershell command
            ps_commands.append(f"(Get-Item -LiteralPath '{modified_path}' -Force).CreationTime = '{formatted_date}'; (Get-Item -LiteralPath '{modified_path}' -Force).LastWriteTime = '{formatted_date}'")
            print(f"Adding to list: {filename} -> {formatted_date}")
            processed_count += 1
        else:
            print(f"Skipping {filename} - Pattern did not match.")
            skipped_count += 1

def main():
    global access_denied_count

    # Takes arguments for recursion
    parser = argparse.ArgumentParser(prog='titleStamp', description="Syncs files\'s metadata based on its filename")
    parser.add_argument('-r','--recursive', action='store_true')
    parser.add_argument('-d', '--dry_run', action='store_true')
    args = parser.parse_args()
    if args.recursive:
        execute_recursively()
    else:
        execute_only_path()
    
    # Executing powershell script
    if args.dry_run:
        print(f"\n===============================")
        print("Dry run, no files were affected. Posting summary only.")
    else:
        if ps_commands:
            print(f"\n===============================")
            print(f"Applying {len(ps_commands)} timestamps via PowerShell batch... Please wait.")
            ps_script_path = os.path.join(tempfile.gettempdir(), "update_timestamps.ps1")
            try:
                with open(ps_script_path, "w", encoding="utf-8-sig") as f:
                    f.write("\n".join(ps_commands))
                
                # Capture the native PowerShell output so we can scan it for specific errors
                result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script_path], capture_output=True, text=True)
                
                # Pass the console output through so the user can still read the raw log
                if result.stdout: print(result.stdout)
                if result.stderr: print(result.stderr)
                
                # Analyze combined log for specific Access Denied issues
                combined_log = result.stdout + result.stderr
                denied_paths = set(regex.findall(r"Access to the path '(.+?)' is denied", combined_log))
                access_denied_count = len(denied_paths)
                
                print("Batch execution complete!")
            except Exception as e:
                print(f"Error during PowerShell batch execution: {e}")
                error_count += 1
            finally:
                if os.path.exists(ps_script_path):
                    os.remove(ps_script_path)
                
    print_summary()
                
if __name__ == "__main__":
    main()