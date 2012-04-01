import sqlite3
from re import compile
from os.path import expanduser, join, exists, dirname
import shutil, tempfile
from urllib import unquote
import codecs
from sys import argv
from os import system
from optparse import OptionParser
from pickle import load, dump
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
parser.add_option("-o","--outfile", dest="outfile", default="out.ps")
parser.add_option("-c","--chrome", action="callback", callback=chrome, help="Path to Chrom(e|ium) history file", nargs=1, type="string")
parser.add_option("-f","--firefox", action="callback", callback=firefox, help="Path to Firefox/Iceweasel history file", nargs=1, type="string")
parser.add_option("-s","--pickle", dest="stored", action="append", default=[], help="Add other pickled links files")
opts, args = parser.parse_args()

if len(paths) ==0 :
	parser.error("Didn't specify any history paths")

host = compile("http://(en.wikipedia.org)/wiki/([^#&]+)")
#enw = compile("http://tvtropes.org/pmwiki/pmwiki.php/Main/(.+)")
#host = compile("http://([^\/]+)/([^\?]+)")
#host = compile("http://((?:tvtropes.org)|(?:en.wikipedia.org))/([^\?]+)")

links = {}

for f in opts.stored:
	extra = load(open(f))
	for begin in extra:
		if begin not in links:
			links[begin] = set()
		links[begin].update(extra[begin])

def cleanup(name):
	return unquote(name.replace("_", " "))

for generate in paths:
	for (url, ref) in generate:
		end = host.search(url)
		begin = host.search(ref)

		if begin and end and begin.groups()[0] == end.groups()[0]:
			begin = cleanup("/".join(begin.groups()))
			end = cleanup("/".join(end.groups()))
			print begin, end
			if begin == end:
				continue
			if begin not in links:
				links[begin] = set()
			links[begin].add(end)

dump(links, open("results.pickle","wb"))

#dotfile = join(tempfile.gettempdir(), "history-dot")
dotfile = "history.dot"
out = codecs.open(dotfile, "wb", "utf-8")

print >>out, "digraph sites {"
print >>out, "\tgraph [overlap=\"false\", sep=\"+2,2\"];"

prefixes = {}

for begin in sorted(links):
	for end in sorted(links[begin]):
		prefix = ""
		while len(begin) > len(prefix) and len(end) > len(prefix) and begin[len(prefix)] == end[len(prefix)]:
			prefix += begin[len(prefix)]
		while prefix.find("/")!=-1 and prefix[-1] != "/":
			prefix = prefix[:-1]
		if prefix!="" and prefix[-1] == "/":
			if prefix not in prefixes:
				prefixes[prefix] = []
			prefixes[prefix].append((begin[len(prefix):],end[len(prefix):]))
		else:
			print >>out, "\t\"%s\" -> \"%s\";"%(begin, end)

for p in prefixes:
	print >>out, "\tsubgraph cluster_%s {"%(p.replace(".", "_").replace("/","_").replace(":", "_").replace(" ", "_"))
	print >>out, "\t\tlabel=\"%s\";"%p
	for begin, end in prefixes[p]:
		print >>out, "\t\t\"%s\" -> \"%s\";"%(begin, end)
	print >>out, "\t}"

print >>out, "}"
out.close()
