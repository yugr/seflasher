#!/cygdrive/c/Users/User/AppData/Local/Programs/Python/Python37-32/python
#!/usr/bin/python3

# Copyright 2013-2018 Yury Gribov
#
# The MIT License (MIT)
#
# Use of this source code is governed by MIT license that can be
# found in the LICENSE.txt file.

# TODO:
# - cmdline options (-v, -h, ...)
# - error checking
# - checksum
# - decode answers
# - clarify spec:
#   * on sending packet, when should I wait for 100 ms?
#     after reading reply or before?
#   * what to do with response?
#   * is AA present in packet file?

import time
import re
import array
import sys

try:
  import serial
  import tkinter
  import tkinter.filedialog
  import tkinter.messagebox
except ModuleNotFoundError:
  print("""\
Please install dependencies by running
  > python -m ensurepip
  > python -m pip install pyserial tkinter
in command line.
""")
  sys.exit(1)

def log(lev, msg):
  if lev not in ['DBG', 'WARN', 'ERR']:
    print('ERR: Unknown logging level: %s' % lev)
  print(lev + ': ' + msg)

# Scan for available ports.
def find_ports():
  ports = []
  for i in range(256):
    try:
      s = serial.Serial('COM%d' % i)
      log('DBG', 'Successfully opened port %d' % i)
      ports.append((i, s.name))
      s.close()
    except serial.SerialException:
      pass
  return ports

def read_file(fname):
  with open(fname, 'r') as f:
    log('DBG', 'Successfully opened file %s' % fname)
    lines = f.readlines()
    return lines

def parse_packet(line):
  log('DBG', 'Parsing ''%s''' % line)

  # Remove comments
  line = re.sub(r'\/\/.*$', '', line)
  line = re.sub(r'#.*$', '', line)

  line = line.strip().upper()
  if not line:
    return None

  # TODO: handle exceptions
  pak = list(map(int, line.split()))

  log('DBG', 'Parse results: ' + str(pak))

  return pak

def parse_packets(lines):
  paks = []
  for line in lines:
    pak = parse_packet(line)
    if pak:
      paks.append(pak)
  return paks

def check_packet(i, pak):
  # Check for header
  if pak[0] != 0xAA:
    log('ERR', 'No header (0xAA) in packet %d, inserting' % i)
    pak.insert(0, 0xAA)

  # Check byte values
  for byte in pak:
    if not 0 <= byte <= 255:
      log('ERR', 'Not a byte value: %d' % byte)

def check_packets(paks):
  for i, pak in enumerate(paks):
    check_packet(i, pak)

def encode_packet(pak):
  # Replace magic bytes
  new_pak = []
  for byte in pak:
    if 0xAA == byte:
      new_pak.append(55)
      new_pak.append(2)
    elif 55 == byte:
      new_pak.append(55)
      new_pak.append(1)
    else:
      new_pak.append(byte)
  pak = new_pak

  # Append checksum
  csum = 0 # TODO
  log('DBG', csum)
  pak.append(csum)

def encode_packets(paks):
  return list(map(encode_packet, paks))

def decode_ans(ans):
  return ans   # TODO

def check_ans(ans):
  pass

def send_packet(p, pak):
  s = array.array('B', pak).tostring()
  log('DBG', 'Writing ''%s'' to port %s' % (s, p.name))
  p.write(s)
  log('DBG', 'Sleep for 100 ms')
  time.sleep(0.100)
  log('DBG', 'Reading response')
  ans = parse_packet(p.read())
  ans = decode_ans(ans)
  check_ans(ans)
  return ans

def open_pakfile_dialog(root):
  fname = tkinter.filedialog.askopenfilename(
    title='Select file with packet data',
    filetypes=[('All files', '*')])
  if fname:
    root.pakfile_name_content.set(fname)

def create_dropdown(parent, val0, vals):
  var = tkinter.StringVar(parent)
  var.set(val0)
  lst = tkinter.OptionMenu(*(parent, var) + tuple(vals))
  return (lst, var)

class SeflasherApp(tkinter.Tk):
  def __init__(self, parent):
    super().__init__(self, parent)
    self.parent = parent
    self.initialize()

  def initialize(self):
    self.grid()

    # Find ports

    ports = find_ports()
    portnames = []
    for p, name in ports:
      portnames.append(name)
      log('DBG', 'Found port %d: %s' % (p, name))

    if not ports:
      log('ERR', 'No ports found')
      exit(1)

    # Create widgets

    port_frame = tkinter.LabelFrame(self, text='Connection')
    port_frame.grid(row=0, column=0, padx=5, pady=5)

    port_list, self.port_var = create_dropdown(
      port_frame,
      portnames[0],
      portnames)
    port_list.pack(padx=10, pady=10)

    speed_list, self.speed_var = create_dropdown(
      port_frame,
      '9600',
      ['9600', '19200', '38400', '57600', '115200'])
    speed_list.pack(padx=10, pady=10)

    file_frame = tkinter.LabelFrame(self, text='Data')
    file_frame.grid(row=1, column=0, padx=5, pady=5)

    self.pakfile_name_content = tkinter.StringVar()
    pakfile_name = tkinter.Entry(file_frame, textvariable=self.pakfile_name_content)
    pakfile_name.grid(row=0, column=0, padx=10, pady=10)

    open_pakfile = tkinter.Button(
      file_frame,
      text='...',
      command=lambda: open_pakfile_dialog(self))
    open_pakfile.grid(row=0, column=1, padx=10, pady=10)

    send_paks = tkinter.Button(
      self,
      text='Send',
      command=self.send_packets)
    send_paks.grid(row=2, column=0, padx=5, pady=5)

    self.resizable(0, 0)

  def send_packets(self):
    fname = self.pakfile_name_content.get()
    if not fname:
      tkinter.messagebox.showerror(
        'File not found',
        'Please specify name of file with packets')
      return

    try:
      paks = parse_packets(read_file(fname))
      log('DBG', 'Raw file data: %s' % paks)
    except ValueError:
      log('ERR', 'Error reading packet')
      tkinter.messagebox.showerror(
        'Failed to read data',
        'Error reading packet')
      return

    check_packets(paks)
    encode_packets(paks)
    log('DBG', 'Encoded data: ' + str(paks))

    portname = self.port_var.get()
    log('DBG', 'Selected port: %s' % portname)

    speed = int(self.speed_var.get())
    log('DBG', 'Selected speed: %d' % speed)

    try:
      p = serial.Serial(
        port=portname,
        timeout=30,
        writeTimeout=30,
        baudrate=speed)

      # TODO: do something with ans?
      for pak in paks:
        ans = send_packet(p, pak)

      log('DBG', 'Done sending packets')

      p.close()
    except serial.SerialException:
      log('ERR', 'Error opening port')
      tkinter.messagebox.showerror(
        'Failed to open port',
        'Error opening port')
      return

def main():
  root = SeflasherApp(None)
  root.title('Serial Flasher')
  root.mainloop()

if __name__ == '__main__':
  main()
