"""Test StealthMark GUI imports and basic functionality."""
import sys

sys.path.insert(0, r"D:\work\code\stealthmark\src")
sys.path.insert(0, r"D:\work\code\stealthmark")

def test_import():
    from stealthmark.gui import MainWindow, WatermarkWorker
    print("[OK] stealthmark.gui imported")
    print(f"     MainWindow: {MainWindow}")
    print(f"     WatermarkWorker: {WatermarkWorker}")


def test_pyqt6():
    from PyQt6 import QtWidgets, QtCore
    print("[OK] PyQt6 imported")
    print(f"     QtWidgets: {QtWidgets}")
    print(f"     QtCore: {QtCore}")


def test_core_import():
    from src.core.manager import StealthMark
    sm = StealthMark()
    print("[OK] StealthMark core imported")
    print(f"     handlers: {len(sm._handler_registry)}")
    print(f"     formats: {sm.supported_formats()[:6]}...")


if __name__ == "__main__":
    test_pyqt6()
    test_core_import()
    test_import()
    print("\nAll GUI tests passed!")
