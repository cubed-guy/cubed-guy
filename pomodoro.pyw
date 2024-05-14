'''
Requires pygame. Use the following command to install.
$ pip install pygame

Start timer with your spacebar.
Timer stops only once it ends.
This is by design. It forces you to commit to the time.
'''

from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'

from datetime import datetime as dt, timedelta as td
from sys import argv

from os.path import dirname
import pygame
from pygame.locals import *
pygame.font.init()
font_path = f'{dirname(__file__)}/Product Sans Regular.ttf'
font  = pygame.font.Font(font_path, 216)
nfont = pygame.font.Font(font_path, 36)
sfont = pygame.font.Font(font_path, 12)

c = type('c', (), {'__matmul__': (lambda s, x: (*x.to_bytes(3, 'big'),)), '__sub__': (lambda s, x: (x&255,)*3)})()
bg = c-34
sub_fg = c@0xa06055
fg = c@0xff9088
green = c@0xa0ffe0

fps = 60

w, h = res = (1280, 720)

def updateStat(msg = None, update = True):
	# call this if you have a long loop that'll taking too long
	rect = (0, h-20, w, 21)
	display.fill(c-0, rect)

	tsurf = sfont.render(msg or f'{timer}', True, c--1)
	display.blit(tsurf, (5, h-20))

	if update: pygame.display.update(rect)

def resize(size):
	global w, h, res, display
	w, h = res = size
	display = pygame.display.set_mode(res, RESIZABLE)
	updateDisplay()

def updateDisplay():

	display.fill(bg)

	nsurf = nfont.render(f'{n} session{"s" * (n != 1)} done today.', True, sub_fg)
	if ticking: col = green
	else: col = fg
	surf = font.render(f'{timer:%M:%S}', True, col)
	x, y = (w - surf.get_width()) // 2, (h - surf.get_height()) // 2

	display.blit(surf, (x, y))

	x = (w - nsurf.get_width()) // 2
	y -= nsurf.get_height() * 2
	display.blit(nsurf, (x, y))

	updateStat(update = False)
	pygame.display.flip()

def toggleFullscreen():
	global pres, res, w, h, display
	res, pres =  pres, res
	w, h = res
	if display.get_flags()&FULLSCREEN: resize(res)
	else: display = pygame.display.set_mode(res, FULLSCREEN); updateDisplay()

pos = [0, 0]
dragging = False
origin = dt.utcfromtimestamp(0)
pomodoro = td(minutes=25)
timer = origin + pomodoro
ticking = False
n = 0 if len(argv) < 2 else int(argv[1])

resize(res)
pres = pygame.display.list_modes()[0]
# pygame.key.set_repeat(500, 50)
clock = pygame.time.Clock()
running = True
while running:
	for event in pygame.event.get():
		if event.type == KEYDOWN:
			if   event.key == K_F11: toggleFullscreen()
			elif event.key == K_SPACE: ticking = True
		elif event.type == QUIT: running = False
			
	updateDisplay()
	ticks = clock.tick(fps)

	if ticking:
		timer -= td(milliseconds=ticks)
		if timer < origin:
			timer = origin + pomodoro
			ticking = False
			n += 1
		