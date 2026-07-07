import sys
import os
import gc
import machine
import network
import urequests

version = 1.0

VERSION_URL = "https://raw.githubusercontent.com/твой_профиль/твой_репозиторий/main/version.txt"
CODE_URL = "https://raw.githubusercontent.com/твой_профиль/твой_репозиторий/main/main.py"

def cmd_help(args):
    return "Доступные команды: help, status, echo, write, rm, ls, cat, os_version, update"

def cmd_status(args):
    return "Memory: {} bytes free".format(gc.mem_free())

def cmd_echo(args):
    return " ".join(args)

def cmd_write(args):
    if len(args) < 2:
        return "Example: write <file_name> <text>"

    filename = args[0]
    content = " ".join(args[1:])

    try:
        with open(filename, 'w') as f:
            f.write(content)
        return "File '{}' created successfully.".format(filename)
    except Exception as e:
        return "Write error: {}".format(e)

def cmd_rm(args):
    if len(args) < 1:
        return "Example: rm <file_name>"

    try:
        os.remove(args[0])
        return "File '{}' deleted.".format(args[0])
    except OSError:
        return "Error: File '{}' not found.".format(args[0])

def cmd_ls(args):
    try:
        files = os.listdir()
        if not files:
            return "No files found."
        return "Files: " + ", ".join(files)
    except Exception as e:
        return "Error reading directory: {}".format(e)

def cmd_cat(args):
    if len(args) < 1:
        return "Example: cat <file_name>"
    try:
        with open(args[0], 'r') as f:
            return f.read()
    except OSError:
        return "Error: File '{}' not found.".format(args[0])

def cmd_os_version(args):
    return "OS Version: {}".format(version)

def cmd_update(args):
    sta_if = network.WLAN(network.STA_IF)
    
    if not sta_if.isconnected():
        return "Error: No Wi-Fi connection. Connect your ESP8266 to the internet first."
    
    print("Checking for updates...")
    try:
        response = urequests.get(VERSION_URL)
        server_version = float(response.text.strip())
        response.close()
        
        if server_version <= version:
            return "Your OS is up to date (v{}).".format(version)
        
        print("New version v{} found! Downloading...".format(server_version))
        
        response = urequests.get(CODE_URL)
        if response.status_code == 200:
            with open("main.new", "w") as f:
                f.write(response.text)
            response.close()
            
            try:
                os.remove("main.py")
            except OSError:
                pass 
            
            os.rename("main.new", "main.py")
            
            print("Update successful! Rebooting system...")
            machine.reset() 
        else:
            response.close()
            return "Error: Server returned status code {}".format(response.status_code)
            
    except Exception as e:
        return "Update failed: {}".format(e)


commands = {
    "help": cmd_help,
    "status": cmd_status,
    "echo": cmd_echo,
    "write": cmd_write,
    "rm": cmd_rm,
    "ls": cmd_ls,
    "cat": cmd_cat,
    "os_version": cmd_os_version,
    "update": cmd_update
}


print("\n=== ESP8266 CLI v{} Started ===".format(version))
print("Type 'help' to see available commands.\n")

while True:
    try:
        line = input(">>> ").strip()
        
        if not line:
            continue
            
        parts = line.split()
        cmd_name = parts[0].lower()
        cmd_args = parts[1:]
        
        if cmd_name in commands:
            result = commands[cmd_name](cmd_args)
            if result:
                print(result)
        else:
            print("Error: Command '{}' not found. Type 'help'.".format(cmd_name))
            
    except Exception as e:
        print("System Error: {}".format(e))