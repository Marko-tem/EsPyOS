import sys
import os
import gc
import machine
import network
import urequests

VERSION_URL = "https://github.com/Marko-tem/EsPyOS/blob/main/version.txt"
CODE_URL = "https://github.com/Marko-tem/EsPyOS/blob/main/main.py"

class MicroTerminal:
    def __init__(self):
        self.version = 1.1
        self.platform = sys.platform
        self.display = None
        
        self.commands = {
            "help": self.cmd_help,
            "status": self.cmd_status,
            "echo": self.cmd_echo,
            "write": self.cmd_write,
            "rm": self.cmd_rm,
            "ls": self.cmd_ls,
            "cat": self.cmd_cat,
            "os_version": self.cmd_os_version,
            "wifi": self.cmd_wifi,
            "set_wifi": self.cmd_set_wifi,
            "wifi_status": self.cmd_wifi_status,
            "i2c_scan": self.cmd_i2c_scan,
            "run": self.cmd_run,
            "update": self.cmd_update
        }

    def output(self, *args, **kwargs):
        print(*args, **kwargs)
        if self.display:
            pass

    def execute_line(self, line):
        line = line.strip()
        if not line:
            return

        parts = line.split()
        cmd_name = parts[0].lower()
        cmd_args = parts[1:]

        if cmd_name in self.commands:
            try:
                result = self.commands[cmd_name](cmd_args)
                if result:
                    self.output(result)
            except Exception as e:
                self.output("Execution Error: {}".format(e))
        else:
            self.output("Error: Command '{}' not found. Type 'help'.".format(cmd_name))

    def cmd_help(self, args):
        return "Available commands:\n" + ", ".join(sorted(self.commands.keys()))

    def cmd_status(self, args):
        gc.collect()
        return "Platform: {} | Memory: {} bytes free".format(self.platform.upper(), gc.mem_free())

    def cmd_echo(self, args):
        return " ".join(args)

    def cmd_write(self, args):
        if len(args) < 2: return "Example: write <file_name> <text>"
        try:
            with open(args[0], 'w') as f:
                f.write(" ".join(args[1:]))
            return "File '{}' saved.".format(args[0])
        except Exception as e: return "Write error: {}".format(e)

    def cmd_rm(self, args):
        if len(args) < 1: return "Example: rm <file_name>"
        try:
            os.remove(args[0])
            return "File '{}' deleted.".format(args[0])
        except OSError: return "Error: File not found."

    def cmd_ls(self, args):
        files = os.listdir()
        return "Files: " + ", ".join(files) if files else "No files found."

    def cmd_cat(self, args):
        if len(args) < 1: return "Example: cat <file_name>"
        try:
            with open(args[0], 'r') as f: return f.read()
        except OSError: return "Error: File not found."

    def cmd_os_version(self, args):
        return "OS Version: {}".format(self.version)

    def cmd_wifi(self, args):
        if len(args) < 2: return "Example: wifi <SSID> <password>"
        import time
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        
        self.output("Connecting to {}...".format(args[0]))
        sta_if.connect(args[0], " ".join(args[1:]))
        
        timeout = 10
        while not sta_if.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            self.output(".", end="")
        self.output("") 
        
        if sta_if.isconnected():
            return "Connected! IP: {}".format(sta_if.ifconfig()[0])
        return "Connection failed."

    def cmd_set_wifi(self, args):
        if len(args) < 2: return "Example: set_wifi <SSID> <password>"
        import json
        config = {"ssid": args[0], "password": " ".join(args[1:])}
        try:
            with open("config.json", "w") as f:
                json.dump(config, f)
            return "Credentials saved to config.json. Rebooting to apply..."
        except Exception as e: return "JSON Save error: {}".format(e)

    def cmd_wifi_status(self, args):
        sta_if = network.WLAN(network.STA_IF)
        if sta_if.isconnected():
            return "Status: Connected\nIP: {}\nGateway: {}\nSubnet: {}".format(sta_if.ifconfig()[0], sta_if.ifconfig()[2], sta_if.ifconfig()[1])
        return "Status: Disconnected"

    def cmd_i2c_scan(self, args):
        from machine import I2C, Pin
        self.output("Scanning I2C bus...")
        try:
            if self.platform == "esp8266":
                i2c = I2C(scl=Pin(5), sda=Pin(4))
            else:
                i2c = I2C(0, scl=Pin(22), sda=Pin(21))
                
            devices = i2c.scan()
            if not devices: return "No I2C devices detected."
            return "Found devices at HEX addresses: " + ", ".join([hex(d) for d in devices])
        except Exception as e: return "I2C Error: {}".format(e)

    def cmd_run(self, args):
        if len(args) < 1: return "Example: run <script.py>"
        filename = args[0]
        try:
            self.output("Launching {}...".format(filename))
            with open(filename, "r") as f:
                exec(f.read(), globals())
            return "Execution finished."
        except OSError: return "Error: File '{}' not found.".format(filename)
        except Exception as e: return "Runtime Error: {}".format(e)

    def cmd_update(self, args):
        sta_if = network.WLAN(network.STA_IF)
        if not sta_if.isconnected(): return "Error: Network is unreachable. Connect Wi-Fi first."
        
        gc.collect()
        self.output("Contacting update server...")
        try:
            response = urequests.get(VERSION_URL)
            server_version = float(response.text.strip())
            response.close()
            
            if server_version <= self.version:
                return "Your OS is already up to date (v{}).".format(self.version)
            
            self.output("New update found: v{}. Initializing download...".format(server_version))
            gc.collect()
            
            response = urequests.get(CODE_URL)
            if response.status_code == 200:
                with open("main.new", "wb") as f:
                    while True:
                        chunk = response.raw.read(256)
                        if not chunk: break
                        f.write(chunk)
                response.close()
                
                try: os.remove("main.py")
                except: pass
                os.rename("main.new", "main.py")
                
                self.output("OS upgraded successfully! System reboot...")
                machine.reset()
            else:
                response.close()
                return "Server returned error HTTP code: {}".format(response.status_code)
        except Exception as e:
            return "Update system crashed: {}".format(e)


terminal = MicroTerminal()

terminal.output("\n=== MicroTerminal OS v{} ===".format(terminal.version))
terminal.output("Hardware Architecture: {}".format(terminal.platform.upper()))
terminal.output("System initialized. Type 'help' for commands.\n")

while True:
    try:
        user_input = input("ESP8266>>> " if terminal.platform == "esp8266" else "ESP32>>> ")
        terminal.execute_line(user_input)
    except Exception as e:
        print("Fatal Core Error: {}".format(e))
