from pylast import *
import math
import sqlite3
from pickle import dump, load
from pyx import *
from sys import argv, exit
from stats import *

assert len(argv) == 2, "Specify a username to check"

class ListenerCache:
	def __init__(self, key=None, secret=None):
		self.net = LastFMNetwork(api_key=key, api_secret=secret)
		self.cachePath = "track.cache"
		self.con = sqlite3.connect(self.cachePath)
		self.cur = self.con.cursor()

		self.cur.execute("SELECT name FROM sqlite_master WHERE type = \"table\" and name=\"tracks\"")
		if self.cur.fetchone() == None:
			self.cur.execute("create table tracks (artist text, title text, listener_count int)")
			self.con.commit()

	def recent_tracks(self, user):
		cacheFile = "%s.cache"%user
		try:
			tracks = load(file(cacheFile, "rb"))
		except (IOError, EOFError):
			user = self.net.get_user(username=user)
			tracks = user.get_recent_tracks(limit=200)
			dump(tracks, file(cacheFile, "wb"))
		return tracks

	def listener_count(self, track):
		artist = track.get_artist().name
		title = track.get_title()
		self.cur.execute("select listener_count from tracks where artist=? and title=?", (artist, title))
		item = self.cur.fetchone()
		if item:
			return item[0]
		else:
			print "getting count for \"%s\" - \"%s\""%(artist,title)
			count = track.get_listener_count()
			self.cur.execute("insert into tracks values(?, ?, ?)", (artist, title, count))
			self.con.commit()
			return int(count)
	
try:
	(api_key, secret) = [x.strip() for x in file("secrets").readlines()]
except IOError:
	print "Make a file called 'secrets' with two lines: your Last.fm api key and secret"
	exit(-1)
lc = ListenerCache(key=api_key, secret=secret)
tracks = lc.recent_tracks(argv[1])

logValues = {}
rawLogValues = []
rawValues = []

for t in tracks:
	rawValue = lc.listener_count(t.track) 
	rawValues.append(rawValue)
	logValue = math.log(rawValue,2)
	rawLogValues.append(logValue)
	logValue = int(logValue)
	if logValue not in logValues:
		logValues[logValue] = 1
	else:
		logValues[logValue] += 1

for k in range(max(logValues.keys())):
	if k not in logValues:
		logValues[k] = 0

bincount = 20

binsize = max(rawValues)/(bincount*1.0)
binned = dict([(x,0) for x in range(bincount)])

print "bin size", binsize

for v in rawValues:
	binned[min(int(v/binsize),bincount-1)] +=1

ms = meanstdv(rawLogValues)
towrite = "median: %.2f mean: %.2f std dev: %.2f"%(median(rawLogValues),ms[0],ms[1])

text.set(mode=r"latex")

g = graph.graphxy(width=16, x=graph.axis.bar())
g.plot(graph.data.points(logValues.items(), xname=1, y=2), [graph.style.bar()])
g.finish()
pos = g.vpos(0.02,0.92) # numbers plucked out the air after experimenting
g.text(pos[0], pos[1], towrite)
g.pipeGS(filename="log-%s.png"%argv[1], device="png16m")

g = graph.graphxy(width=16, x=graph.axis.bar())
g.plot(graph.data.points(binned.items(), xname=1, y=2), [graph.style.bar()])
g.pipeGS(filename="binned-%s.png"%argv[1], device="png16m")
