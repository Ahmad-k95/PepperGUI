import serial
import serial.tools.list_ports
import re

class ArduinoSerialManager(object):
    def __init__(self, log_widget=None):
        self.serial_port = None
        self.connection = None
        self.log_widget = log_widget
        self.ports = []

    def log(self, message, color="white"):
        if self.log_widget:
            self.log_widget.insert("end", message, color)
            self.log_widget.insert("end", "\n")
            self.log_widget.see("end")
        else:
            print(message)

    def list_ports(self):
        ports = list(serial.tools.list_ports.comports())
        filtered_ports = [port for port in ports if self._is_arduino_port(port.device)]
        self.ports = filtered_ports

        if not filtered_ports:
            self.log("> No Arduino serial ports found.", "red")
            return []

        self.log("> Available Arduino serial ports:", "yellow")
        for i, port in enumerate(filtered_ports):
            self.log("port{}: {}".format(i + 1, port.device), "white")

        return filtered_ports

    def _is_arduino_port(self, port_name):
        return (
            re.match(r'/dev/ttyACM[0-9]+', port_name) or
            re.match(r'/dev/ttyUSB[0-9]+', port_name) or
            re.match(r'COM[0-9]+', port_name, re.IGNORECASE)
        )

    def connect(self, port, baudrate=9600, timeout=1):
        try:
            self.connection = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            self.serial_port = port
            self.log("> Connected to Arduino on {}".format(port), "green")
        except serial.SerialException as e:
            self.log("> Failed to connect to port {}: {}".format(port, e), "red")
            self.connection = None

    def send_message(self, message):
        if self.connection and self.connection.is_open:
            try:
                self.connection.write((message + "\n").encode('utf-8'))
                self.log("> Vicon Trigger signal: '{}'".format(message), "yellow")
            except serial.SerialException as e:
                self.log("> Failed to send message: {}".format(e), "red")
        else:
            self.log("> Serial connection is not open.", "red")
