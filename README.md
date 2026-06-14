# metaSync

A Python utility that syncs file metadata (creation and last-modified timestamps) to the date and time encoded in the filename.

## Overview

Many apps — OBS, NVIDIA ShadowPlay, VRChat, Steam, Samsung Gallery, Android cameras, and Windows screenshot tools — embed a timestamp directly in the filename when saving media. `titleStamp.py` reads that timestamp, then sets the file's `CreationTime` and `LastWriteTime` metadata to match, so your files sort chronologically by when they were actually captured rather than when they were copied or transferred.

## Supported Filename Formats (Mutable)

| Source | Pattern | Example |
|---|---|---|
| OBS | `YYYY-MM-DD HH-MM-SS` | `2026-02-27 21-49-06.mkv` |
| NVIDIA ShadowPlay | `YYYY.MM.DD - HH.MM.SS` | `2024.09.30 - 20.56.37.mp4` |
| VRChat | `_YYYY-MM-DD_HH-MM-SS` | `world_2021-09-01_21-20-52.png` |
| Windows Screenshot | `Screenshot YYYY-MM-DD HHMMSS` | `Screenshot 2026-04-18 175856.png` |
| Steam Screenshot | `YYYYMMDDHHMMSS_1` | `20190119184452_1.jpg` |
| Samsung / Android | `YYYYMMDD_HHMMSS` | `20260506_155609.jpg` |
| Generic Android | `YYYYMMDDHHMMSS` | `20260509105257.mp4` |

## Adding a Custom Filename Format

If your files use a timestamp format not listed above, you can add your own pattern in the config section at the top of `titleStamp.py`.

**1. Write a regex pattern with exactly 6 capture groups** in this order: year, month, day, hour, minute, second.

```python
pattern_MyApp = r"(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})(\d{2})"  # MyApp_2026-06-13_175856
```

Each `(\d{N})` captures a fixed-width number. Separators between groups (dashes, dots, spaces, underscores) are matched literally and sit outside the parentheses.

**2. Add it to the `PATTERNS` list**, before `pattern_Generic` — Generic is a catch-all and should always be last to avoid false matches.

```python
PATTERNS = [
    regex.compile(pattern_OBS),
    ...
    regex.compile(pattern_MyApp),   # add here
    regex.compile(pattern_Generic)  # keep last
]
```

> **Note:** If two patterns could match the same filename, whichever appears first in the list wins. Make sure your pattern is specific enough that it won't accidentally match filenames intended for a different format.

## Supported File Types (Mutable)

`.mp4`, `.mkv`, `.png`, `.jpeg`, `.jpg`

## Requirements

- Windows (uses PowerShell to apply timestamps)
- Python 3.x

## Setup

To call `titleStamp` from any directory without navigating to this folder first:

1. Add this folder to your system PATH (run PowerShell as Administrator):

```powershell
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\path\to\metaSync", "Machine")
```

2. Restart your terminal.

## Usage

Navigate to the folder containing your media files, then run:

```
titleStamp
```

To also process all subdirectories, pass the `-r` flag:

```
titleStamp -r
```

To preview what would change without modifying any files, add the `-d` flag:

```
titleStamp -d
titleStamp -r -d
```

The script targets whichever directory your terminal is currently in, collects all timestamp changes into a single PowerShell batch, applies them in one pass, then prints a summary:

```
===============================
PROCESSED: 142
SKIPPED: 3
ACCESS DENIED (Read only?): 0
ERROR: 0
===============================
```

Files are skipped if their extension is unsupported or if no recognized timestamp pattern is found in the filename.
