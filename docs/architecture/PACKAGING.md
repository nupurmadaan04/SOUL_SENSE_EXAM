# Desktop Packaging Guide

## Overview
This guide explains how to package SoulSense EQ Test as a standalone desktop application using PyInstaller.

## Prerequisites
- Python 3.11+
- All dependencies installed (`pip install -r requirements.txt`)
- PyInstaller (`pip install pyinstaller`)

## Quick Build

### Windows
```bash
build.bat
```

### Manual Build
```bash
pyinstaller soulsense.spec
```

## Output
- Executable: `dist/SoulSense/SoulSense.exe`
- All dependencies bundled automatically
- Database and data files included

## Configuration

### soulsense.spec
The spec file controls packaging behavior:
- **datas**: Includes `data/questions.txt` and i18n translations
- **hiddenimports**: Ensures sklearn, nltk, and sqlalchemy modules are bundled
- **console=False**: Runs as GUI application (no console window)

### Customization
Edit `soulsense.spec` to:
- Add/remove data files
- Include additional hidden imports
- Change executable name or icon

## Troubleshooting

### Missing Modules
Add to `hiddenimports` in soulsense.spec:
```python
hiddenimports=['module_name']
```

### Missing Data Files
Add to `datas` in soulsense.spec:
```python
datas=[('source_path', 'dest_folder')]
```

### NLTK Data
NLTK vader_lexicon is downloaded at runtime if missing.

## Distribution
The `dist/SoulSense/` folder contains:
- SoulSense.exe (main executable)
- All required DLLs and dependencies
- Data files and translations

Zip the entire folder for distribution.

## Notes
- First run may take longer (ML model training, NLTK downloads)
- Database created automatically in application directory
- Logs saved to `logs/soulsense.log`
