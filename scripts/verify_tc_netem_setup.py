import argparse
import sys

from qprism.netem import profiles as netem_profiles
from qprism.netem import controller as netem_controller

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify tc netem")
    parser.add_argument("-i", "--interface", default="lo")

    args = parser.parse_args()
    iface = args.interface

    profiles = netem_profiles.load_profiles()
    if not profiles:
        raise Exception("No Netem profiles found...")
    test_profile_name = "mid_loss" if "mid_loss" in profiles else next(iter(profiles))
    profile = profiles[test_profile_name]
    print(f'Profile: {test_profile_name} on interface {iface}...')
    try:
        netem_controller.apply_profile(profile, interface=iface)
    except Exception as e:
        if isinstance(e, PermissionError):
            print("Error: root privileges are required to apply netem profiles")
        elif isinstance(e, FileNotFoundError):
            print("Error: 'tc' command not found")
        elif "Specified qdisc kind is unknown" in str(e):
            print("Kernel not prepped, for fedora use 'sudo modprobe sch_netem")
        else:
            print(f"Error: failed to apply profile {e}")
        sys.exit(1)

    try:
        netem_controller.clear(interface=iface)
        print(f'Interface: {iface} cleared...')

    except Exception as e:
        print(f"Failed to clear interface: {iface} due to {e}")
