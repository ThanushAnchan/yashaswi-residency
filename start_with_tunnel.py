import subprocess
import threading
import time
import re
import sys
import os
import urllib.request
import ssl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

def keep_alive_pinger(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    while True:
        try:
            time.sleep(25)
            req = urllib.request.Request(f"{url}/api/health", headers={'User-Agent': 'KeepAlive/1.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                pass
        except Exception:
            pass

def run_tunnel():
    active_pinger_url = None
    while True:
        print("\nConnecting to secure public HTTPS tunnel for Yashaswi Residency...")
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=10",
            "-o", "ServerAliveCountMax=5",
            "-R", "80:127.0.0.1:5000",
            "nokey@localhost.run"
        ]
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in iter(process.stdout.readline, ''):
                match = re.search(r'(https://[a-zA-Z0-9.-]+\.lhr\.life)', line)
                if match:
                    public_url = match.group(1)
                    link_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PUBLIC_LINKS.txt")
                    with open(link_file, "w", encoding="utf-8") as f:
                        f.write(f"PUBLIC_URL={public_url}\nADMIN_URL={public_url}/admin\n")
                    print("\n" + "=" * 68)
                    print("  🏡 YASHASWI RESIDENCY HOME STAY - LIVE PUBLIC WEBSITE ONLINE!")
                    print("=" * 68)
                    print(f"  🌐 Public Website Link: {public_url}")
                    print(f"  🔐 Owner Admin Link:    {public_url}/admin")
                    print("  🔑 Admin Login:         admin / yashaswi2026!")
                    print("=" * 68)
                    print(f"  (Saved in: {link_file})")
                    print("  Share this link on WhatsApp, mobile, or desktop anywhere!")
                    print("=" * 68 + "\n")
                    sys.stdout.flush()
                    if active_pinger_url != public_url:
                        active_pinger_url = public_url
                        t_ping = threading.Thread(target=keep_alive_pinger, args=(public_url,), daemon=True)
                        t_ping.start()
            process.wait()
        except Exception as e:
            print("Tunnel connection reconnecting in 3s...", e)
        time.sleep(3)

if __name__ == '__main__':
    t_flask = threading.Thread(target=run_flask, daemon=True)
    t_flask.start()
    time.sleep(1.5)
    run_tunnel()
