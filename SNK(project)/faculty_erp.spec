# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for AI-Enabled Faculty Attendance, Leave and Substitute Management ERP.
Bundles the complete PySide6 application, NumPy NLP classifiers, MySQL adapters, and assets.
"""
import sys
from pathlib import Path

block_cipher = None
BASE_DIR = Path(__file__).resolve().parent

# Collect required runtime data files
datas = [
    (str(BASE_DIR / 'database' / 'schema.sql'), 'database'),
    (str(BASE_DIR / 'database' / 'seed_data.sql'), 'database'),
    (str(BASE_DIR / 'models'), 'models'),
    (str(BASE_DIR / 'diagrams'), 'diagrams'),
    (str(BASE_DIR / '.env.example'), '.'),
]

# Hidden imports required for dynamic imports & plugins
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'mysql.connector',
    'pymysql',
    'numpy',
    'joblib',
    'sklearn',
    'sklearn.utils._typedefs',
    'reportlab',
    'reportlab.pdfgen.canvas',
    'reportlab.platypus',
    'reportlab.lib.pagesizes',
    'reportlab.lib.colors',
    'reportlab.lib.styles',
    'dotenv',
    'config.settings',
    'utils.logger',
    'utils.exceptions',
    'database.connection',
    'database.init_db',
    'services.auth_service',
    'services.attendance_service',
    'services.grace_service',
    'services.leave_rules_service',
    'services.leave_workflow_service',
    'services.substitute_service',
    'services.recommendation_service',
    'services.analytics_service',
    'services.report_service',
    'services.audit_service',
    'services.backup_service',
]

a = Analysis(
    ['main.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib.tests', 'scipy.spatial.cKDTree'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FacultyERP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging console output, False for clean GUI release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FacultyERP',
)
