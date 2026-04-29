import os           # Navigates through files
import re as regex  # Detect timestamp patterns
import subprocess   # Calls powershell to modify metadata
import tempfile     # Powershell will create .ps1 files during batches, so this will keep temp files organized

# ======================================================================================================================
# =========================================== START OF CONFIG ==========================================================
# ======================================================================================================================

# =========================================== REGEX PATTERNS ===========================================================
# ! Ensure the order of the patterns are unique and cannot have similarity conflicts with others !
TIMESTAMPS_PATTERNS = [
    r"(\d{4})\-(\d{2})\-(\d{2}) (\d{2})\-(\d{2})\-(\d{2})",             # OBS:                  2026-02-27 21-49-06
    r"(\d{4})\.(\d{2})\.(\d{2}) \- (\d{2})\.(\d{2})\.(\d{2})",          # NVIDIA:               2024.09.30 - 20.56.37.04
    r"_(\d{4})\-(\d{2})\-(\d{2})_(\d{2})\-(\d{2})\-(\d{2})",            # VRCHAT Photos:        VRChat_2026-01-05_06-17-15.741_2560x1440
    r"Screenshot (\d{4})\-(\d{2})\-(\d{2}) (\d{2})(\d{2})(\d{2})",      # Windows Screenshot:   Screenshot 2026-04-18 175856.png
    r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})_1",                    # Steam Screenshot:     20190119184452_1
    r"Robloxapp-(\d{4})(\d{2})(\d{2})\-(\d{2})(\d{2})(\d{2})"           # Roblox:               Robloxapp-20230215-2302123
]
# ======================================================================================================================

# =========================================== SUB REGEX PATTERNS ===========================================================
# Regex to match (IF NOT FOUND IN MAIN PATTERN)
# NOT IMPLEMENTED YET
sub_pattern_VRChat = r"_(\d{4})\-(\d{2})\-(\d{2})"    # _2021-09-01
# ======================================================================================================================

EXTENSIONS = (".mp4", ".mkv", ".png", ".jpeg", ".jpg")
DIR_EXCEPTIONS = [
    r"B:\▬ Videos and Photos ▬\(HANDBRAKE THESE FUCKERS)", 
    r"B:\▬ Videos and Photos ▬\(New Recordings)"
]
# ======================================================================================================================
# =========================================== END OF CONFIG ============================================================
# ======================================================================================================================

error_count = 0
skipped_count = 0
processed_count = 0
access_denied_count = 0
ps_commands = []

skipped_files = []

# Pre-compile regex patterns for performance scaling
# compiled_patterns = [regex.compile(pattern) for pattern in TIMESTAMPS_PATTERNS]
compiled_patterns = []
for patterns in TIMESTAMPS_PATTERNS:
    compiled_patterns.append(regex.compile(patterns))

def print_skipped_files():
    while(True):
        user_choice = input("List skipped files (y/n)?: ")
        if user_choice in ("y", "yes", "hai", "si", "ye", "yeah", "yup", "yep", "ja", "oui"):
            print(f"\n================ SKIPPED FILES ================")
            for item in skipped_files:
                print(item)
            break
        elif user_choice in ("n", "no", "non", "nein", "nyet", "nope", "nah", "nuh"):
            break
    return

def print_summary():
    print_skipped_files()
    print(f"\n=================== SUMMARY ===================")
    print(f"PROCESSED: {processed_count}")
    print(f"SKIPPED: {skipped_count}")
    print(f"ACCESS DENIED (Read only?): {access_denied_count}")
    print(f"ERROR: {error_count}")
    print("================================================\n")

def execute_recursively():
    directory = input("Enter directory: ")
    for root, dirs, files in os.walk(directory):
        if root in DIR_EXCEPTIONS:
            print(f"(Exception) Skipping directory: {root}")
            continue
        else:
            change_timestamp_with_title(root, files)
    return

def execute_only_path():
    directory = input("Enter directory: ")
    files = os.listdir(directory)
    change_timestamp_with_title(directory, files)
    return

def change_timestamp_with_title(root, files):
    global error_count, skipped_count, processed_count, ps_commands
    for filename in files:
        if not filename.lower().endswith(EXTENSIONS):
            print(f"Skipping {filename} - Invalid Extension.")
            skipped_files.append(filename)
            skipped_count += 1
            continue
        
        # Checks for appropiate regex patterns
        regex_match = None

        for compiled_regex in compiled_patterns:
            regex_match = compiled_regex.search(filename)
            if regex_match:
                break

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
            skipped_files.append(filename)
            skipped_count += 1
    return

def main():
    global access_denied_count

    while True:
        user_choice = input("Run recursively? (y/n): ").strip().lower()
        if user_choice in ("y", "yes", "hai", "si", "ye", "yeah", "yup", "yep", "ja", "oui"):
            execute_recursively()
            break
        elif user_choice in ("n", "no", "non", "nein", "nyet", "nope", "nah", "nuh"):
            execute_only_path()
            break
            
    if ps_commands:
        print(f"\n===============================")
        print(f"Applying {len(ps_commands)} timestamps via PowerShell batch... Please wait.")
        ps_script_path = os.path.join(tempfile.gettempdir(), f"update_timestamps.ps1")
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