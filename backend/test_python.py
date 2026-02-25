#!/usr/bin/env python3
print("✅ Python is working correctly!")
print(f"Python version: {__import__('sys').version}")
print(f"Current directory: {__import__('os').getcwd()}")
try:
    import reportlab
    print("✅ reportlab is installed")
except ImportError:
    print("❌ reportlab is NOT installed")
try:
    import matplotlib
    print("✅ matplotlib is installed")
except ImportError:
    print("❌ matplotlib is NOT installed")
try:
    import numpy
    print("✅ numpy is installed")
except ImportError:
    print("❌ numpy is NOT installed")
print("✅ All basic checks completed!")