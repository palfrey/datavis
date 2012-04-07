import sqlite3
from re import compile
from os.path import expanduser, join, exists, dirname
import shutil, tempfile
from urllib import unquote
import codecs
from os import system, mkdir
from optparse import OptionParser
from ConfigParser import SafeConfigParser

paths = []

def chrome(option, opt, value, parser):	
	if value == "-":
		path = expanduser("~/.config/chromium/Default/History")
	else:
		path = value

	if not exists(path):
		parser.error("Chrome path '%s' does not exist!"%path)

	try:
		conn = sqlite3.connect(path, timeout=1)
		conn.execute("select top(1) from visits")
	except sqlite3.OperationalError, e:
		if str(e).find("database is locked")!=-1:
			newpath = join(tempfile.gettempdir(), "History")
			shutil.copyfile(path, newpath)
			conn = sqlite3.connect(newpath)
		else:
			raise

	c = conn.cursor()

	c.execute("select urls1.url,urls2.url from visits as visits1,urls as urls1,urls as urls2,visits as visits2 where visits1.url = urls1.id and visits1.from_visit != 0 and visits1.from_visit = visits2.id and visits2.url = urls2.id")
	
	paths.append(c)

def firefox(option, opt, value, parser):	
	if value == "-":
		path = expanduser("~/.mozilla/firefox/profiles.ini")
		sp = SafeConfigParser()
		sp.read(path)
		path = join(join(dirname(path), sp.get("Profile0", "Path")), "places.sqlite")
	else:
		path = value

	if not exists(path):
		parser.error("Firefox path '%s' does not exist!"%path)

	conn = sqlite3.connect(path, timeout=1)
	c = conn.cursor()
	c.execute("select place1.url, place2.url from moz_historyvisits as visits1, moz_places as place1, moz_places as place2, moz_historyvisits as visits2 where visits1.place_id = place1.id and visits1.from_visit!=0 and visits1.from_visit = visits2.id and visits2.place_id = place2.id")
			
	paths.append(c)

parser = OptionParser()
parser.add_option("-o","--outdir", dest="outdir", default="out")
parser.add_option("-c","--chrome", action="callback", callback=chrome, help="Path to Chrom(e|ium) history file, or '-' for the default path", nargs=1, type="string")
parser.add_option("-f","--firefox", action="callback", callback=firefox, help="Path to Firefox/Iceweasel history file, or '-' for the default path", nargs=1, type="string")
opts, args = parser.parse_args()

if len(paths) ==0 :
	parser.error("Didn't specify any history paths")

#host = compile("http://(.+)")
host = compile("http://en.wikipedia.org/wiki/([^#&]+)")
#host = compile("http://tvtropes.org/pmwiki/pmwiki.php/Main/([^&?]+)")
#host = compile("http://([^\/]+)/([^\?]+)")
#host = compile("http://((?:tvtropes.org)|(?:en.wikipedia.org))/([^\?]+)")

links = {}
ends = {}

if not exists(opts.outdir):
	mkdir(opts.outdir)

def cleanup(name):
	return unquote(name.replace("_", " "))

for generate in paths:
	for (url, ref) in generate:
		end = host.search(url)
		begin = host.search(ref)

		if begin and end:
			begin = cleanup("/".join(begin.groups()))
			end = cleanup("/".join(end.groups()))
			if begin == end:
				continue
			if begin not in links:
				links[begin] = set()
			links[begin].add(end)
			if end not in ends:
				ends[end] = set()
			ends[end].add(begin)

def genTree(r, conn, fwd, prev = None):
	if prev == None:
		prev = [r]
	if r not in conn:
		return []
	items = []
	for l in conn[r]:
		if fwd:
			items.append((r,l))
		else:
			items.append((l,r))
		if l not in prev:
			items.extend(genTree(l, conn, fwd, prev + [l]))
	return items

def removePairs(conn, pairs, fwd):
	for p in pairs:
		if fwd:
			(a,b) = p
		else:
			(b,a) = p
		conn[a].discard(b)
		if len(conn[a]) == 0:
			del conn[a]

safeLink = compile("[^a-zA-Z0-9_]")

while len(links) > 0:
	start = links.keys()[0]

	startf = safeLink.sub("_", start).encode("utf-8")[:100]
	dotfile = join(opts.outdir, "%s.dot"%startf)
	psfile = join(opts.outdir, "%s.ps"%startf)
	pairs = set(genTree(start, links, True) + genTree(start, ends, False))
	if not exists(psfile) and len(pairs) > 1:
		out = codecs.open(dotfile, "wb", "utf-8")
		print >>out, "digraph links {"
		print >>out, "\tgraph [overlap=\"false\", sep=\"+2,2\"];"

		for (a, b) in pairs:
			print >>out, "\t\"%s\" -> \"%s\";" % (
				a.replace("\"", "\\\""), b.replace("\"", "\\\"")
			)
		print >>out, "}"
		out.close()
		cmd = "dot \"%s\" -Tps -o \"%s\""%(dotfile, psfile)
		print cmd
		ret = system(cmd)
		assert ret == 0, ret
	removePairs(links, pairs, True)
	removePairs(ends, pairs, False)
