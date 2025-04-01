import telnetlib
import socket
from concurrent.futures import ThreadPoolExecutor
import threading
import time

# Конфигурация
MAX_THREADS = 5
USERNAME = 'username'
PASSWORD = 'pass'
TFTP_SERVER = '0.0.0.0'
FIRMWARE_FILE = 'firmware.img'
TIMEOUT = 25

print_lock = threading.Lock()

def send_command(tn, command, expected_response, timeout=10):
    tn.write(command.encode('ascii') + b"\r\n")
    return tn.read_until(expected_response.encode('ascii'), timeout=timeout)

def execute_commands(ip):
    try:
        with telnetlib.Telnet(ip, timeout=TIMEOUT) as tn:
            # Аутентификация
            tn.read_until(b"login: ", timeout=7)
            tn.write(USERNAME.encode('ascii') + b"\r\n")

            tn.read_until(b"Password: ", timeout=7)
            tn.write(PASSWORD.encode('ascii') + b"\r\n")

            # Переход в enable режим
            send_command(tn, "enable", "#")

            # Конфигурационный режим
            send_command(tn, "configure", "(config)#")

            # Загрузка прошивки
            response = send_command(
                tn,
                f"tftp get {TFTP_SERVER} {FIRMWARE_FILE} localfile {FIRMWARE_FILE}",
                "%Transmission success",
                timeout=600
            )
            if b"Transmission success" not in response:
                raise Exception("Ошибка загрузки прошивки")

            send_command(tn, f"upgrade os {FIRMWARE_FILE}", "Please select", 10)
            send_command(tn, "2", "please wait", 300)

            send_command(tn, "boot os main", "(config)#")
            send_command(tn, "boot startup-config", "(config)#")

            tn.write(str.encode(f"reboot\r"))
            tn.read_until(str.encode("  WARNING:System will reboot! Continue?(y/n) [y]"))
            tn.write(str.encode(f"y\r"))

            with print_lock:
                print(f"{ip}: Успешная перезагрузка")

    except (socket.timeout, ConnectionResetError, EOFError):
        with print_lock:
            print(f"[{ip}] Соединение закрыто (перезагрузка)")
    except Exception as e:
        with print_lock:
            print(f"[{ip}] Ошибка: {str(e)}")

def main():
    with open('ip.txt', 'r') as f:
        ips = [line.strip() for line in f if line.strip()]

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        executor.map(execute_commands, ips)

if __name__ == "__main__":
    print("Запуск автоматического обновления...")
    main()
    print("Обработка всех устройств завершена.")
