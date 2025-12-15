# DONE: Render
# DONE: Add event
# DONE: Hover
# DONE: Edit
# DONE: Intralane Collision
# DONE: Add and show deps
# DONE: Dep constraints
# DONE: Render names of events
# DONE: Rename
# DONE: Delete
# DONE: Switch lanes
# TODO: Shove (and thus bulk edit, toggleable)
# TODO: Lock events
# DONE: Pan and zoom
# DONE: Time Markers
# DONE: Type pos and len
# TODO: Constraints while typing
# TODO: Save and load
# TODO: Ghost lane
# TODO: Binary Search

import pygame
from datetime import datetime as dt, timedelta as td
from pygame.locals import *
from enum import Enum, auto
pygame.font.init()
font = pygame.font.Font('D:/Assets/Product Sans Regular.ttf', 16)

c = type('c', (), {'__matmul__': (lambda s, x: (*x.to_bytes(3, 'big'),)), '__sub__': (lambda s, x: (x&255,)*3)})()
COL_BG   = c-0x22
COL_REG  = c-0x80
COL_SEL  = c@0xff6040
COL_SEL_DEP = c@0xc0a030
COL_HVR  = c--1
COL_LANE = c-0x32
COL_DEP  = c-0x50
COL_MARKER = c-0x50
COL_TIMETEXT = c-0x80
COL_NAME = c@0xffffa0

HANDLE_SIZE = 1
HANDLE_W = 3
MSG_COOLDOWN = td(seconds=4)
ZOOM_FAC = 1-3e-3
FOV_MIN = td(hours=1)
FOV_MAX = td(7)

DATE_FMT = '%d-%b %H:%M:%S'

fps = 60

w, h = res = (1280, 720)

LANE_GAP = 32
TOP_PADDING = 20

class TextFields(Enum):
	len = auto()
	pos = auto()
	name = auto()

class Modes(Enum):
	std = auto()
	len = auto()
	pre_len = auto()
	pos = auto()
	dep = auto()
	text = auto()
	pan = auto()

class Event:
	def __init__(self, name, start, dur, lane):
		self.name = name
		self.start = start
		self.dur = dur
		self.lane = lane
		self.deps = []  # These must complete only before self

		# Storing just deps is sufficient to deduce the depees,
		# but we make a space-time tradeoff by storing the depees explicitly
		self.depees = []  # These must begin only after self

	def __repr__(self):
		return f'Event{self.name!r}< {self.start} |{self.dur}| >'

	def add_dep(self, dep):
		# TODO: Get a hash or something
		if dep in self.deps: return

		self.deps.append(dep)
		dep.depees.append(self)
		print('Created dependency:', dep, 'to', self)

	def tightest_dep(self):
		out = None
		for dep in self.deps:
			if out is None or dep.start+dep.dur > out.start+out.dur: out = dep
		# print('tightest dep out of', len(self.deps), '->', out)
		return out

	def tightest_depee(self):
		out = None
		for depee in self.depees:
			if out is None or depee.start < out.start: out = depee
		# print('tightest depee out of', len(self.depees), '->', out)
		return out


lanes = []  # This is where we'll populate events

msgs = []
def alert(msg):
	msgs.append((msg, dt.now()+MSG_COOLDOWN))

def update_stat(msg = None, update = True):
	'''
	Use this with update=True to display the status of long running operations
	that would otherwise hang the ui
	'''

	rect = (0, h-20, w, 21)
	display.fill(c-0, rect)

	global msgs
	now = dt.now()
	
	# TODO: use binary search
	i = 0
	for i, e in enumerate(msgs):
		if e[1] > now: break
	else:
		i += 1

	msgs = msgs[i:]
	rmsg = '; '.join(msg for msg, cooldown in msgs)
	if msg is not None:
		rmsg = f'{msg}; {rmsg}'

	tsurf = font.render(rmsg, True, c--1)
	display.blit(tsurf, (5, h-20))

	if update: pygame.display.update(rect)

def resize(size):
	global w, h, res, display
	w, h = res = size
	display = pygame.display.set_mode(res, RESIZABLE)
	update_display()

def update_display():
	display.fill(COL_BG)

	for l, lane in enumerate(lanes):
		y = lane_coord(l)
		display.fill(COL_LANE, (0, y, w, 1))

		for event in lane:
			x_start = max(time_coord(event.start), 0)
			x_end = time_coord(event.start+event.dur)
			event_w = x_end - x_start

			if mode in (Modes.pre_len, Modes.len) and event is hovered:
				if event is selected:
					event_col = COL_SEL
				else:
					event_col = COL_REG
				display.fill(event_col, (x_start, y, event_w, 1))
				display.fill(COL_HVR, (x_end, y-(HANDLE_W+1)//2, HANDLE_SIZE, HANDLE_W))

			else:
				if event is selected:
					if mode is Modes.dep:
						event_col = COL_SEL_DEP
					elif mode is Modes.text:
						event_col = COL_NAME
					else:
						event_col = COL_SEL
				elif event is hovered:
					event_col = COL_HVR
				else:
					event_col = COL_REG
				display.fill(event_col, (x_start, y, event_w, 1))

			x_start = time_coord(event.start)
			render_text = event.name
			if event is selected and mode is Modes.text:
				render_text = text

			tsurf = font.render(render_text, True, event_col)
			display.blit(tsurf, (x_start, y-tsurf.get_height()))

			for dep in event.deps:
				pygame.draw.aaline(display, COL_DEP, (x_start, y), screen_space(dep.start+dep.dur, dep.lane))

	render_time_marker(display, dt.now())
	if highlight_cursor:
		x, y = pygame.mouse.get_pos()
		t, _ = event_space(x, y)
		render_time_marker(display, t, override_screen_x=x)

	update_stat(update = False)
	pygame.display.flip()

def toggle_fullscreen():
	global pres, res, w, h, display
	res, pres =  pres, res
	w, h = res
	if display.get_flags()&FULLSCREEN: resize(res)
	else: display = pygame.display.set_mode(res, FULLSCREEN); update_display()

def render_time_marker(surf, t, *, override_screen_x = None):
	'''
	Pass override_screen_x to avoid recomputation of screen space coord
	'''
	if override_screen_x is None: x = time_coord(t)
	else: x = override_screen_x
	surf.fill(COL_MARKER, (x, 0, 1, h))

	tsurf = font.render(f'{t:{DATE_FMT}}', True, COL_TIMETEXT)
	if x+tsurf.get_width() >= surf.get_width():
		tx = x-tsurf.get_width()
	else:
		tx = x
	surf.blit(tsurf, (tx, 0))

def event_space(x, y):
	return (view_start + x*fov/w), (y-TOP_PADDING+LANE_GAP//2)//LANE_GAP

def lane_coord(l):
	return l*LANE_GAP+TOP_PADDING

def time_coord(t):
	return int((t - view_start)*w/fov)

def screen_space(t, l):
	return time_coord(t), lane_coord(l)

def add_to_lane(lane, e):
	# TODO: Sorted insert
	lane.append(e)

def remove_from_lane(lane, e):
	soft_remove(lane, e)

	# TODO: Use hashes to remove
	for dep in e.deps: dep.depees.remove(e)
	for depee in e.depees: depee.deps.remove(e)

def soft_remove(lane, e):
	# TODO: Binary search, maintain sorted order
	lane.remove(e)

def find_overlap(t, lane):
	# TODO: Binary search
	for e in lane:
		if e.start <= t <= e.start+e.dur:
			return e

	# Explicitly return None just to show it's expected
	return None

def next_collision(t, lane):
	''' Assumes t does not overlap with any events '''
	# TODO: Binary search
	lim = None
	for e in lane:
		if e.start <= t: continue
		if lim is not None and e.start > lim: continue
		# print('down from', lim, 'to', e.start)
		lim = e.start

	return lim

def prev_collision(t, lane):
	''' Assumes t does not overlap with any events '''
	# TODO: Binary search
	lim = None
	for e in lane:
		end = e.start+e.dur
		if end >= t:
			# print('passed on', end, 'vs', t)
			continue
		if lim is not None and end < lim: continue
		# print('up from', lim, 'to', end)
		lim = end

	return lim

def fits_in_lane(lane, e):
	if find_overlap(e.start, lane) is not None:
		return False

	lim = next_collision(e.start, lane)
	if lim is not None and lim < e.start+e.dur:
		return False

	return True

def unparse_td(dur):
	dur -= dur%td(seconds=1)
	out = f'{dur}s'
	out = out.removesuffix(':00s')
	out = out.removeprefix('0:')
	return out

def parse_td(text):
	'''
	20 --> 20 minutes
	20: OR 20:0 OR 20:00 -> 20 hours
	20s --> 20 seconds
	20:s OR 20:00s OR 00:20:00s --> 20 minutes
	20:00:00s --> 20 hours
	'''
	# default to minutes
	try:
		if text.endswith('s'):
			text, _, seconds = text[:-1].rpartition(':')
			if not seconds: seconds = 0
			else: seconds = int(seconds)
		else:
			seconds = 0

		hour_text, _, minutes = text.rpartition(':')
		if not minutes: minutes = 0
		else: minutes = int(minutes)

		if not hour_text: hours = 0
		else: hours = int(hour_text)

	except ValueError:
		alert('Could not parse text. Defaulting to 0')
		return td(0)

	return td(hours=hours, minutes=minutes, seconds=seconds)

def unparse_dt(t):
	today = dt.now().replace(hour=0, minute=0, second=0)
	return unparse_td(t-today)

def parse_dt(text):
	if text == 'n': return dt.now()

	day, _, time = text.rpartition(' ')
	if not day:
		day = dt.now().replace(hour=0, minute=0, second=0)
	elif day == 'n':
		day = dt.now()

	dur = parse_td(text)
	return day + dur

fov = td(1)
view_start = dt.now().replace(hour=0, minute=0, second=0)
mode = Modes.std
text_target = TextFields.name

hovered = None
selected = None
grab_offset = None
grab_start_lane = None
highlight_cursor = False

resize(res)
pygame.key.set_repeat(500, 50)
pres = pygame.display.list_modes()[0]
clock = pygame.time.Clock()
running = True
while running:
	for event in pygame.event.get():
		if event.type == KEYDOWN:
			if event.key == K_F11: toggle_fullscreen()
			elif mode is Modes.text:
				if event.key == K_ESCAPE:
					mode = Modes.std

				elif event.key == K_RETURN:
					if text_target is TextFields.len:
						selected.dur = parse_td(text)
					elif text_target is TextFields.pos:
						selected.start = parse_dt(text)
					elif text_target is TextFields.name:
						selected.name = text
					else:
						alert('Unknown text target:', text_target)

					mode = Modes.std

				elif event.key == K_BACKSPACE:
					text = text[:-1]
				elif event.unicode.isprintable():
					text += event.unicode

			elif event.mod & (KMOD_LCTRL|KMOD_RCTRL):
				if   event.key == K_r:  # r for resize
					mode = Modes.text
					text_target = TextFields.len
					text = unparse_td(selected.dur)
				elif event.key == K_t:  # t for time
					mode = Modes.text
					text_target = TextFields.pos
					text = unparse_dt(selected.start)

			else:
				if   event.key == K_ESCAPE:
					selected = None
				elif event.key == K_r:  # r for resize
					if mode is Modes.pre_len: mode = Modes.std
					else: mode = Modes.pre_len
				elif event.key == K_e:  # e for edit
					if selected is None:
						alert('Nothing selected for renaming')
						continue
					if mode is Modes.text: mode = Modes.std
					else:
						mode = Modes.text
						text_target = TextFields.name
						text = selected.name
				elif event.key == K_d:  # d for dependency
					if selected is None:
						alert('Nothing selected for adding dependencies')
						continue
					if mode is Modes.dep: mode = Modes.std
					else: mode = Modes.dep
				elif event.key == K_x:  # x is always delete
					if selected is None:
						alert('Nothing selected for deleting')
						continue
					remove_from_lane(lanes[selected.lane], selected)
					selected = None
				elif event.key == K_w:  # w from wasd
					if selected.lane <= 0:
						alert('Already at top most lane')
						continue

					target_lane = lanes[selected.lane-1]
					if not fits_in_lane(target_lane, selected):
						alert('Event would overlap')
						continue

					current_lane = lanes[selected.lane]
					soft_remove(current_lane, selected)
					selected.lane -= 1
					add_to_lane(target_lane, selected)

				elif event.key == K_s:  # s from wasd
					if selected.lane+1 >= len(lanes):
						target_lane = []
						lanes.append(target_lane)
					else:
						target_lane = lanes[selected.lane+1]
						if not fits_in_lane(target_lane, selected):
							alert('Event would overlap')
							continue

					current_lane = lanes[selected.lane]
					soft_remove(current_lane, selected)
					selected.lane += 1
					add_to_lane(target_lane, selected)

				elif event.key == K_t:  # t for time
					highlight_cursor = True

		elif event.type == KEYUP:
			if event.key == K_t:
				highlight_cursor = False

		elif event.type == VIDEORESIZE:
			if not display.get_flags()&FULLSCREEN: resize(event.size)
		elif event.type == QUIT: running = False
		elif event.type == MOUSEBUTTONDOWN:
			if event.button in (4, 5):
				delta = event.button*2-9
			elif event.button == 1:
				mods = pygame.key.get_mods()
				if mods & (KMOD_LCTRL|KMOD_RCTRL):  # Ctrl for new event
					t, l = event_space(*event.pos)
					if l < 0:
						alert('Lane would be too high')
						continue  # Ignore invalid events
					if l >= len(lanes):
						lanes.extend([] for _ in range(1+l-len(lanes)))
					lane = lanes[l]

					if find_overlap(t, lane) is not None:
						alert('Events would overlap')
						continue

					selected = Event(f'{dt.now().timestamp():.02f}', t, td(0), l)
					add_to_lane(lane, selected)
					mode = Modes.len

				elif mods & (KMOD_LALT|KMOD_RALT):  # Alt for scroll and zoom
					mode = Modes.pan
					start_t, _ = event_space(*event.pos)
					start_fov = fov
					start_y = event.pos[1]

				else:  # No modifiers pressed
					if hovered is not None:
						if mode is Modes.dep:
							if hovered.start+hovered.dur > selected.start:
								alert('Dependency cannot end after the event has started')
								continue
							selected.add_dep(hovered)

						else:
							selected = hovered
							print('selected', selected)

							if mode is Modes.pre_len:
								mode = Modes.len
							else:
								mode = Modes.pos
								t, grab_start_lane = event_space(*event.pos)
								grab_offset = t-selected.start

		elif event.type == MOUSEMOTION:
			if mode is Modes.len:
				if selected is None:
					alert('Nothing selected for len mode')
					mode = Modes.std
					continue

				t, l = event_space(*event.pos)
				lim = next_collision(selected.start, lanes[selected.lane])
				depee = selected.tightest_depee()
				if depee is not None and (lim is None or depee.start < lim): lim = depee.start
				if lim is not None and lim < t: t = lim
				print(f'Setting dur to: max({t-selected.start}, td(0))')
				selected.dur = max(t-selected.start, td(0))

			elif mode is Modes.pos:
				if selected is None:
					alert('Nothing selected for pos mode')
					mode = Modes.std
					continue

				t, l = event_space(*event.pos)
				new_start = t-grab_offset
				lim = next_collision(selected.start, lanes[selected.lane])
				depee = selected.tightest_depee()
				if depee is not None and (lim is None or depee.start < lim): lim = depee.start
				if lim is not None and lim-selected.dur < new_start:
					new_start = lim-selected.dur
				else:
					lim = prev_collision(selected.start+selected.dur, lanes[selected.lane])
					dep = selected.tightest_dep()
					if dep is not None and (lim is None or dep.start+dep.dur > lim): lim = dep.start+dep.dur
					if lim is not None and lim > new_start:
						# print('readjust from', new_start, 'to', lim)
						new_start = lim

				selected.start = new_start

			elif mode is Modes.pan:
				x, y = event.pos
				fov = start_fov * ZOOM_FAC ** (y-start_y)
				fov = min(max(fov, FOV_MIN), FOV_MAX)

				temp_t, _ = event_space(*event.pos)
				view_start = start_t-(temp_t - view_start)

			else:
				t, l = event_space(*event.pos)
				# TODO: Find the hovered event object
				hovered = None

				if l < 0: continue
				if l >= len(lanes): continue

				hovered = find_overlap(t, lanes[l])

		elif event.type == MOUSEBUTTONUP:
			if mode is not Modes.dep:
				print('Reset Mode')
				mode = Modes.std

	update_display()
	clock.tick(fps)
