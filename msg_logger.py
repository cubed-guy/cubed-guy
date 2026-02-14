from msvcrt import getch
from datetime import datetime as dt, timedelta as td

def raw_print(s):
	print(end='\r\x1b[K'+s, flush=True)

def nl():
	line = f'{prompt_at(dt.now())}{msg}'
	raw_print(line)
	print()

def prompt_at(t):
	return f'{t:%Y-%m-%d %H:%M:%S}> '


msg = ''

while 1:
	line = f'{prompt_at(dt.now())}{msg}'
	raw_print(line)
	c = getch()
	assert isinstance(c, bytes), f'getch() returned type {type(c)}'
	if c == b'\x03':
		nl()
		break
	elif c in (b'\r', b'\n'):
		nl()
		msg = ''
	elif c == b'\x08':
		msg = msg[:-1]
	elif all(b < 128 for b in c) and c.decode().isprintable():
		msg += c.decode()
	else:
		msg += f'{[*c]}'
