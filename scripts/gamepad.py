#!/usr/bin/python3

import os
import sys
import time
import signal
import subprocess
import evdev
from evdev import ecodes


class GamepadController:
    """A class to handle gamepad input events and perform actions based on button combinations."""

    reset_combo = [
        ecodes.BTN_TL,
        ecodes.BTN_TR,
        ecodes.BTN_MODE,
    ]

    tty11_combo = [
        ecodes.BTN_MODE,
        ecodes.BTN_SOUTH,
    ]

    mangohud_combo = [
        ecodes.BTN_MODE,
        ecodes.BTN_WEST,
    ]

    xboxdrv_combo = [
        ecodes.BTN_MODE,
        ecodes.BTN_START,
    ]

    makima_combo = [
        ecodes.BTN_MODE,
        ecodes.BTN_SELECT,
    ]

    def __init__(self, mac):
        self.mac = mac
        self.device_path = f"/dev/gamepad-{mac}"
        self.xboxdrv_process = None
        self.is_bluetooth = (
            mac.upper()
            in subprocess.run(
                ["bluetoothctl", "devices", "Connected"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
        )
        self.pressed_buttons = set()
        self.last_timestamp = time.time()

    def log(self, message):
        """Log a message to stdout with a timestamp."""
        print(message, flush=True)

    def run(self, args):
        """Run a command with subprocess and log the command."""
        self.log("Executing: " + " ".join(args))
        subprocess.run(args, check=False)

    def disconnect_bluetooth(self):
        """Disconnect the Bluetooth controller using bluetoothctl."""
        if not self.is_bluetooth:
            return
        bt_mac = self.mac.upper()
        os.system(f"echo disconnect {bt_mac} | bluetoothctl")

    def remove_notv_file(self):
        """Remove the /tmp/notv file if it exists."""
        file_path = "/tmp/notv"
        try:
            os.remove(file_path)
            self.log(f"{file_path} has been removed.")
        except FileNotFoundError:
            self.log(f"{file_path} does not exist. No action needed.")

    def restart_tty(self):
        """Restart the current TTY if it is not TTY1-8."""

        self.log("Restarting TTY...")

        result = subprocess.run(
            ["sudo", "fgconsole"], capture_output=True, text=True, check=False
        )

        tty = int(result.stdout.strip())
        if tty < 9:
            self.log(f"Active TTY is {tty}. Not restarting.")
            return

        self.remove_notv_file()
        self.run(["/bin/sudo", "systemctl", "restart", f"getty@tty{tty}"])

    def stop_gdm(self):
        """Stop the GDM service to allow TTY switching."""

        self.log("Stopping GDM...")
        self.run(["sudo", "systemctl", "stop", "gdm"])

    def enable_tty(self, tty):
        """Switch to a specific TTY and start the getty service."""

        self.log(f"Switching to TTY {tty}")
        self.stop_gdm()
        self.remove_notv_file()
        self.run(["/bin/sudo", "chvt", f"{tty}"])
        self.run(["/bin/sudo", "systemctl", "start", f"getty@tty{tty}"])

    def toggle_mangohud(self):
        """Toggle MangoHud on or off."""

        self.log("Toggling MangoHud")
        self.run(["/opt/scripts/mangohud-toggle"])

    def set_microphone_led(self, state):
        """Set the microphone LED state."""

        self.run(["dualsensectl", "-d", self.mac, "microphone-led", state])

    def set_lightbar_state(self, state):
        """Set the lightbar state to on, off, or blink."""

        self.run(["dualsensectl", "-d", self.mac, "lightbar", f"{state}"])

    def determine_lightbar_color(self):
        """Determine the lightbar color based on xboxdrv status."""

        if self.xboxdrv_process and self.xboxdrv_process.poll() is None:
            return [0, 255, 0]
        return [0, 0, 255]

    def update_lightbar(self):
        """Update the lightbar color based on the current state."""

        r, g, b = self.determine_lightbar_color()
        i = 50 if self.is_bluetooth else 255
        self.run(
            ["dualsensectl", "-d", self.mac, "lightbar", f"{r}", f"{g}", f"{b}", f"{i}"]
        )

    def set_lightbar(self, r, g, b):
        """Set the lightbar color to the specified RGB values."""

        i = 50 if self.is_bluetooth else 255
        self.run(
            ["dualsensectl", "-d", self.mac, "lightbar", f"{r}", f"{g}", f"{b}", f"{i}"]
        )

    def toggle_xboxdrv(self):
        """Toggle the xboxdrv process on or off."""

        if self.xboxdrv_process and self.xboxdrv_process.poll() is None:
            self.log("Stopping xboxdrv...")
            os.killpg(os.getpgid(self.xboxdrv_process.pid), signal.SIGKILL)
            self.xboxdrv_process = None
            self.log("xboxdrv stopped.")
        else:
            self.log("Starting xboxdrv...")
            self.xboxdrv_process = subprocess.Popen(
                ["/opt/scripts/simulate-xbox360-controller.sh", self.device_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.log(f"xboxdrv started with PID {self.xboxdrv_process.pid}.")
        self.update_lightbar()

    def handle_event(self, event):
        """Handle input events from the gamepad."""

        # Track thumbstick activity
        if event.type == evdev.ecodes.EV_ABS:
            if event.value < 120 or event.value > 140:
                self.last_timestamp = time.time()

        # Track normal button activity
        if event.type == evdev.ecodes.EV_KEY:
            key_event = evdev.categorize(event)
            self.last_timestamp = time.time()
            if key_event.keystate == key_event.key_down:
                self.log(f"button {event.code} pressed")
                self.pressed_buttons.add(event.code)
                if self.pressed_buttons.issuperset(self.reset_combo):
                    self.log("reset combo pressed")
                    self.pressed_buttons = set()
                    self.restart_tty()
                    return
                if self.pressed_buttons.issuperset(self.tty11_combo):
                    self.log("tty11 combo pressed")
                    self.pressed_buttons = set()
                    self.enable_tty(11)
                    return
                if self.pressed_buttons.issuperset(self.mangohud_combo):
                    self.log("mangohud combo pressed")
                    self.pressed_buttons = set()
                    self.toggle_mangohud()
                    return
                if self.pressed_buttons.issuperset(self.xboxdrv_combo):
                    self.log("xboxdrv combo pressed")
                    self.pressed_buttons = set()
                    self.toggle_xboxdrv()
                    return
            elif key_event.keystate == key_event.key_up:
                self.log(f"button {event.code} released")
                self.pressed_buttons.discard(event.code)

    def main_loop(self):
        """Main loop to read events from the gamepad and handle them."""

        self.log(f"Device    : {self.device_path}")
        self.log(f"MAC       : {self.mac}")
        self.log(f"Bluetooth : {self.is_bluetooth}")

        if self.is_bluetooth:
            time.sleep(0.5)
            self.set_lightbar_state("off")
            time.sleep(0.5)
            self.set_lightbar(0, 0, 255)
        else:
            self.set_lightbar(0, 0, 255)

        try:
            device = evdev.InputDevice(self.device_path)
        except FileNotFoundError:
            self.log(f"Error: Device {self.device_path} not found!")
            sys.exit(1)

        try:
            for event in device.read_loop():
                # If no activity in the last 5 minutes, disconnect.
                if self.is_bluetooth and time.time() - self.last_timestamp > 300:
                    self.log("Bluetooth controller is idle. Disconnecting.")
                    self.disconnect_bluetooth()
                    self.last_timestamp = time.time()
                self.handle_event(event)
        except KeyboardInterrupt:
            self.log("Terminated by user (KeyboardInterrupt).")
        except OSError:
            self.log("Terminated by OSError.")
            if self.xboxdrv_process and self.xboxdrv_process.poll() is None:
                self.log("Stopping xboxdrv...")
                os.killpg(os.getpgid(self.xboxdrv_process.pid), signal.SIGKILL)
                self.xboxdrv_process = None
            sys.exit(0)


def main():
    """Main function to initialize the GamepadController and start the event loop."""

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mac>")
        sys.exit(1)

    controller = GamepadController(sys.argv[1])
    controller.main_loop()


if __name__ == "__main__":
    main()
