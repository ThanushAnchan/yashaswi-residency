import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🏡 YASHASWI RESIDENCY HOME STAY - LOCAL WEB SERVER")
    print("=" * 60)
    print("  • Public Website:    http://127.0.0.1:5000")
    print("  • Owner Admin Login: http://127.0.0.1:5000/admin/login")
    print("  • Credentials:       admin / yashaswi2026!")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
