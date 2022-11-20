# TODO: markers

import pygame
from pygame.locals import *
from tkinter.filedialog import asksaveasfilename as tksave
from tkinter.filedialog import askopenfilename as tkopen
from tkinter import Tk

root = Tk()
root.withdraw()
pygame.font.init()
font  = pygame.font.Font('../Product Sans Regular.ttf', 16)
mfont = pygame.font.Font('../Product Sans Regular.ttf', 12)

# Modes
[NONE, RESIZING, PANNING, COLOUR, MOVING, TYPING, *_] = range(8)
modes = ['NONE', 'RESIZING', 'PANNING', 'COLOUR', 'MOVING', 'TYPING']

filetypes = [('Gantt Chart Files', '*.bars'), ('All Files', '*')]
img_filetypes = [('Image files','*.png;*.jpg;*.gif;*.bmp;*.pcx;*.tga;*.tif;*.lbm;*.pbm')]


untitled = 'untitled'

c = type('c', (), {'__matmul__': (lambda s, x: (*x.to_bytes(3, 'big'),)), '__sub__': (lambda s, x: (x&255,)*3)})()
bg = c-0
row_c = c-34
sel_row_c = c-50
sel_bar_c = c@0xffffc0
m_c = c-90
mt_c = c-192
p_c = c-70
pt_c = c-141
fg = c@0xff9088

msg_cooldown = 45
fps = 60

w, h = res = (1280, 720)

def updateStat(msg = None, update = True):
	rect = (0, h-20, w, 21)
	display.fill(c-0, rect)

	display.fill(Bar.col, (0, h-20, 20, 20))

	v_start = -Bar.pos*Bar.zoom//w
	if sel_bar == -1: b_start = b_end = Size = -1; b_name = ''
	else:
		bar = rows[sel_row][sel_bar]
		b_name = bar.name
		b_start = bar.start
		b_end   = bar.end
		Size = b_end - b_start

	m_pos = pygame.mouse.get_pos()[0]*Bar.zoom//w
	tsurf = font.render(msg or (b_name and b_name+'; ' or '')
		+ f'Colour = {Bar.col}'#; Mode = {modes[mode]}'
		+ f'; Row = {sel_row}'*(sel_row!=-1)
		+ f'; Bar = {b_start} to {b_end}; {Size = }'*(Size!=-1)
		+ f'; Zoom = {Bar.zoom}; '
		+ (name or 'Untitled'),
		True, c--1)
	display.blit(tsurf, (25, h-20))

	if update: pygame.display.update(rect)

def resize(size):
	global res, w, h, display, colours
	res = w, h = size
	display = pygame.display.set_mode(res, RESIZABLE)
	colours = None
	Bar.update_rects(view_also = True)
	updateDisplay()

def updateDisplay():
	if mode == COLOUR:
		blue = pygame.Surface(res)
		blue.fill((0, 0, b))
		display.blit(colours, (0, 0))
		display.blit(blue, (0, 0), special_flags = BLEND_MAX)
	else:
		display.fill(bg)
		for row, bars in enumerate(rows):
			if row == sel_row: display.fill(c-50,
				(0, row*Bar.r_height+Bar.top_pad, w, Bar.height))
			else: display.fill(c-34,
				(0, row*Bar.r_height+Bar.top_pad, w, Bar.height))
			for i, bar in enumerate(bars):
				rect = bar.rect
				if (row, i) == (sel_row, sel_bar):
					dec = not rect.left
					display.fill(sel_bar_c, rect.inflate(4-2*dec, 4))
					display.fill(c-34, rect.inflate(2-dec, 2))
					display.fill((255, 255, 255, 96), rect)
				display.fill(bar.col, rect)

		col, tcol = m_c, mt_c
		for m, marker in enumerate(markers):
			mx = marker.pos *w //Bar.zoom + Bar.pos
			if m == len(markers)-1: col, tcol = p_c, pt_c
			display.fill(col, (mx, 0, 1, h))
			text = mfont.render(marker.text, True, tcol)
			display.blit(text, (mx, 0))
	pygame.display.update((0, 0, w, h-20))

def getColours():
	outsurf = pygame.Surface(res)
	oh = h-20
	updateStat('Generating colour grid...')
	for (x, y) in ((x, y) for x in range(w) for y in range(oh)):
		outsurf.set_at((x, y), (x*255//w, y*255//oh, 0))
	return outsurf

def toggleFullscreen():
	global pres, res, w, h, display, colours
	res, pres =  pres, res
	w, h = res
	if display.get_flags()&FULLSCREEN: resize(res)
	else:
		colours = None
		display = pygame.display.set_mode(res, FULLSCREEN)
		Bar.update_rects(view_also = True)
		updateDisplay()

def get_sel_bar(pos):
	sel_row = (pos[1]-Bar.top_pad)//Bar.r_height
	sel_bar = -1
	if sel_row in range(len(rows)):
		for i, bar in enumerate(rows[sel_row]):
			if bar.isselected(): sel_bar = i
	else: sel_row = -1
	return sel_row, sel_bar

rows = [[] for i in range(6)]
class Bar:
	@classmethod
	def update_rects(cls, view_also = False):
		for row, bars in enumerate(rows):
			for i, bar in enumerate(bars):
				if view_also: bar.update_view()
				bar.update_rect(row)

	@staticmethod
	def saveall(filename):
		file = open(filename, 'a') # 'a'ccomodate markers
		for bars in rows:
			for bar in bars:
				print(bar.start, bar.end, *bar.col[:4], file = file)
			print(file = file)
		file.close()

	@staticmethod
	def open(filename):
		global rows
		file = open(filename)
		rows = [[]]
		markers = True
		for line in file:
			line = line[:-1]
			if not line:
				if not markers: rows.append([])
				else: markers = False
				continue
			if markers: continue
			start, end, r, g, b = map(int, line.split())
			rows[-1].append(Bar(start, end, (r, g, b)))
		if not rows[-1]: rows.pop()

	zoom = 75
	z_thresh = 25
	pos = 0
	col = fg
	height = 50
	r_height = 70
	top_pad = 120
	pad_thresh = 75

	def __init__(self, start, end, col = None, name = '', locked = False):
		self.start = start
		self.end = end
		self.locked = locked
		self.name = name
		if col is None: self.col = self.col
		else: self.col = col

		self.size = 0
		self.update_view()
		self.rect = pygame.Rect(0, 0, 0, 0)

	def __repr__(self):
		return f'Bar({self.start}, {self.end}, {self.col})'

	def update_view(self): # shouldn't have to sort here
		if self.end < self.start: start, end = self.end, self.start
		else: start, end = self.start, self.end
		self.size   = (end - start)*w//self.zoom
		self.offset = start*w//self.zoom

	def normalize(self):
		if self.end < self.start: self.start, self.end = self.end, self.start

	def update_rect(self, row):
		y = self.top_pad + row*self.r_height
		pos = self.pos+self.offset
		clipped = max(0, pos)
		self.rect = pygame.Rect(
			(clipped, y),
			(self.size+pos-clipped+1, self.height)
		)

	def displace(self, start_mpos, size):
		self.start = start_mpos*Bar.zoom//w
		self.end   = self.start + size

	def copy(self, col = None):
		if col is None: col = self.col
		return Bar(self.start, self.end, col, self.name)

	def lock(self): self.locked = True
	def unlock(self): self.locked = False

	def isselected(self):
		return self.rect.collidepoint(pygame.mouse.get_pos())

class Marker:
	def __init__(self, pos, text):
		self.pos = pos
		self.text = text

	@staticmethod
	def saveall(filename):
		file = open(filename, 'w')
		for marker in markers[:-1]:
			print(marker.pos, marker.text, file = file)
		print(file = file)
		file.close()

	@staticmethod
	def open(filename):
		global markers
		file = open(filename)
		markers = []
		for line in file:
			line = line[:-1]
			if not line: break
			x, _, text = line.partition(' ')
			markers.append(Marker(int(x), text))
		markers.append(Marker(0, 'Pointer'))

markers = [Marker(1, 'January'), Marker(32, 'February'), Marker(60, 'March'), Marker(0, 'Pointer')]

# rows = [[Bar(-19, -4, c@0x90ff88), Bar(-1, 4, c--90), Bar(5, 10), Bar(12, 16, c-90), Bar(25, 50, c--1)],
# [Bar(-10, -9, c--1), *(Bar(i, i+7, c@((255<<8)|i)) for i in range(0, 200, 10))],
# [Bar(5, 4, c-0)],
# [Bar(j, k, c@(255<<16|i*50)) for i, (j, k) in zip(range(10), [(-15, 15), (1, 2), (2, 3), (5, 10), (-2, -1)])]]

name = ''
b = 0 # location in colour grid along blue axis
mode = NONE
bar = None
modified = False
sel_row = sel_bar = -1
Bar.update_rects()

msg = ''
msg_timer = 0

resize(res)
pres = pygame.display.list_modes()[0]
pygame.display.set_caption(untitled)

clock = pygame.time.Clock()
running = True
while running:
	for event in pygame.event.get():
		if event.type == VIDEORESIZE:
			if not display.get_flags()&FULLSCREEN: resize(event.size)
		elif event.type == QUIT: running = False

		elif event.type == MOUSEMOTION:
			if mode == NONE:
				sel_row, sel_bar = get_sel_bar(event.pos)
				pos = (event.pos[0] - Bar.pos)*Bar.zoom//w
				marker = markers[-1]
				marker.pos = pos
				marker.text = str(pos)

			elif mode == RESIZING:
				bar.end = (event.pos[0] - Bar.pos)*Bar.zoom//w
				bar.update_view()
				bar.update_rect(sel_row)

			elif mode == PANNING:
				sel_row, sel_bar = get_sel_bar(event.pos)
				Bar.pos += event.rel[0]
				# Bar.top_pad = max(Bar.pad_thresh, Bar.top_pad + event.rel[1])
				Bar.update_rects()

			elif mode == MOVING:
				x = event.pos[0]
				g_bar.displace(x+g_offset, g_size)
				g_bar.update_view()
				g_bar.update_rect(sel_row)

			elif mode == COLOUR: Bar.col = colours.get_at(event.pos)[:2]+(b,)

			pos = (event.pos[0] - Bar.pos)*Bar.zoom//w
			marker = markers[-1]
			marker.pos = pos
			marker.text = str(pos)
			updateDisplay()


		elif event.type == KEYUP:
			if   event.key == K_d:
				if mode == MOVING:  mode = NONE
			elif event.key == K_c:
				if mode == COLOUR:  mode = NONE; updateDisplay()
			elif event.key == K_SPACE:
				if mode == PANNING: mode = NONE
			elif event.key == K_w:
				if mode == RESIZING:
					bar.normalize()
					bar  = None
					mode = NONE
					updateDisplay()

		elif event.type == MOUSEBUTTONUP:
			if event.button == 1:
				if mode == MOVING: mode = NONE
			elif event.button == 3:
				if mode == RESIZING:
					bar.normalize()
					bar  = None
					mode = NONE
					updateDisplay()


		elif event.type == KEYDOWN:
			if event.key == K_F11: toggleFullscreen()
			elif mode == TYPING:
				if event.unicode and event.unicode.isprintable():
					bar.name += event.unicode
				elif event.key == K_BACKSPACE:
					keys = pygame.key.get_pressed()
					if keys[L_CTRL] or keys[R_CTRL]:
						bar.name = ' '.join(bar.name.split()[:-1])
					else: bar.name = bar.name[:-1]
				elif event.key == K_TAB:
					mode = NONE
			elif event.key == K_TAB:
				if mode != NONE or sel_bar == -1: continue
				mode = TYPING
				bar = rows[sel_row][sel_bar]
			elif event.key == K_ESCAPE: running = False
			elif event.key == K_q: running = False


			# <bar files start with markers>
			# x_pos text
			# <empty line to start bars>
			# start end r g b name
			# <empty lines here signify next row>

			elif event.key == K_e: # open bar file
				_name = tkopen(filetypes = filetypes)
				if _name:
					name = _name
					Marker.open(name)
					Bar.open(name)
					Bar.update_rects(view_also = True)
					pygame.display.set_caption(name)

			elif event.key == K_a: # save as
				name = tksave(filetypes = filetypes)
				if name:
					if not name.endswith('.bars'): name += '.bars'
					Marker.saveall(name)
					Bar.saveall(name)
					pygame.display.set_caption(name)

			elif event.key == K_s: # save
				if name: msg = 'saved'; msg_timer = msg_cooldown
				name = name or tksave(filetypes = filetypes)
				if name:
					if not name.endswith('.bars'): name += '.bars'
					Marker.saveall(name)
					Bar.saveall(name)
					pygame.display.set_caption(name)

			elif event.key == K_m: # load markers from file
				_name = tkopen(filetypes = filetypes)
				if _name: Marker.open(_name)

			elif event.key == K_i: # save display image
				img_name = tksave(filetypes = img_filetypes)
				if img_name:
					exts = img_filetypes[0][1].split(';')
					if not any(img_name.endswith(i[1:]) for i in exts):
						img_name += '.png'
					updateStat(
						'#'+''.join(f'{i:02x}' for i in Bar.col),
						update = False)
					pygame.image.save(display, img_name)

			elif event.key == K_c: # choose colour
				if mode == NONE:
					if colours == None: colours = getColours()
					mode = COLOUR
					updateDisplay()

			elif event.key == K_x: # delete selected
				if mode != NONE or sel_bar == -1: continue
				rows[sel_row].pop(sel_bar)
				sel_bar = -1
				updateDisplay()

			elif event.key == K_w: # change the width of selected
				if mode != NONE or sel_bar == -1: continue
				mode = RESIZING
				bar = rows[sel_row][sel_bar]
				bar.normalize()
				x = pygame.mouse.get_pos()[0]
				if x-bar.offset-Bar.pos <= bar.size//2:
					bar.start, bar.end = bar.end, bar.start

			elif event.key == K_r: # move selected bar to previous row*
				if sel_bar == -1 or sel_row < 1: continue
				bar = rows[sel_row].pop(sel_bar)
				sel_row -= 1
				sel_bar = len(rows[sel_row])
				rows[sel_row].append(bar)
				Bar.update_rects()
				updateDisplay()

			elif event.key == K_f: # move selected bar to next row*
				if sel_bar == -1 or sel_row+1 >= len(rows): continue
				bar = rows[sel_row].pop(sel_bar)
				sel_row += 1
				sel_bar = len(rows[sel_row])
				rows[sel_row].append(bar)
				Bar.update_rects()
				updateDisplay()

			# *The bar stays selected after row changes until the mouse moves.

			elif event.key == K_d: # duplicate selected bar with current colour
				if mode != NONE or sel_bar == -1: continue
				mode = MOVING
				g_bar = rows[sel_row][sel_bar].copy(col = Bar.col)
				sel_bar = len(rows[sel_row])
				rows[sel_row].append(g_bar)

				x = pygame.mouse.get_pos()[0]
				g_init   = (g_bar.start, g_bar.end)
				g_offset = g_bar.offset-x
				g_size   = g_bar.end - g_bar.start

				g_bar.update_rect(sel_row)
				updateDisplay()

			elif event.key == K_LSHIFT: # cancel movement
				if mode != MOVING: continue
				mode = NONE
				g_bar.start, g_bar.end = g_init
				Bar.update_rects(view_also = True)
				updateDisplay()

			elif event.key == K_LALT: # get colour of selected bar
				if sel_bar == -1: continue
				Bar.col = rows[sel_row][sel_bar].col

			elif event.key == K_SPACE: # pan view
				if mode == NONE: mode = PANNING

		elif event.type == MOUSEBUTTONDOWN:
			if   event.button == 1:
				if mode != NONE or sel_bar == -1: continue
				mode = MOVING
				g_bar = rows[sel_row][sel_bar]
				x = event.pos[0]
				g_init   = (g_bar.start, g_bar.end)
				g_offset = g_bar.offset-x
				g_size   = g_bar.end - g_bar.start
			elif event.button == 3:
				if sel_row == -1 or mode != NONE: continue
				mode = RESIZING
				pos = (event.pos[0] - Bar.pos)*Bar.zoom//w
				bar = Bar(pos, pos)
				rows[sel_row].append(bar)

			elif event.button in (4, 5):
				delta = 36-event.button*8
				if mode == COLOUR:
					delta += event.button-4
					b = max(0, min(255, b-delta))
					Bar.col = (*colours.get_at(event.pos)[:2], b)
				elif Bar.zoom > delta+Bar.z_thresh:
					if Bar.zoom > 200: delta *= 4
					z = Bar.zoom
					Bar.zoom -= delta
					Bar.pos = (Bar.pos-event.pos[0])*z//Bar.zoom + event.pos[0]
					Bar.update_rects(view_also = True)
				updateDisplay()


	if mode == RESIZING:
		msg_timer = 0
		size = bar.end - bar.start
		updateStat(f'{bar.start} to {bar.end}, {size = }')
	elif mode == TYPING:
		msg_timer = 0
		size = bar.end - bar.start
		updateStat(bar.name+' ')
	elif msg_timer: updateStat(msg); msg_timer -= 1
	else: updateStat()
	clock.tick(fps)
