import subprocess
import argparse
import sys

def ping_ip(ip, timeout):
    try:
        # Adjust the ping command based on the operating system
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            # For Linux and macOS
            output = subprocess.check_output(["ping", "-c", "1", "-W", str(timeout), ip], stderr=subprocess.STDOUT, universal_newlines=True)
        elif sys.platform == "win32":
            # For Windows
            output = subprocess.check_output(["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip], stderr=subprocess.STDOUT, universal_newlines=True)
        else:
            return f"Unsupported platform: {sys.platform}"
        
        if "1 received" in output or "1 packets received" in output:
            return f"{ip} \t is up"
        else:
            return f"{ip} \t is down"
    except subprocess.CalledProcessError:
        return f"{ip} \t is down"

def main(base_ip, timeout):
    for i in range(1, 255):  # .0 is network address and .255 is broadcast address
        ip = f"{base_ip}.{i}"
        print(ping_ip(ip, timeout))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Ping a range of IP addresses in a subnet.')
    parser.add_argument('base_ip', type=str, help='The base IP address (e.g., 10.22.11)')
    parser.add_argument('--timeout', type=float, default=1, help='Timeout for each ping in seconds (default is 1 second)')
    
    args = parser.parse_args()
    
    main(args.base_ip, args.timeout)
