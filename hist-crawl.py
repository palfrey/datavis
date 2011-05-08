import sqlite3
from re import compile
from os.path import expanduser, join, exists
import shutil, tempfile
from urllib import unquote
import codecs
from sys import argv
from os import system
from optparse import OptionParser
from pickle import load, dump

parser = OptionParser()
parser.add_option("-o","--outfile", dest="outfile", default="out.ps")
parser.add_option("-p","--path", dest="path", default=expanduser("~/.config/chromium/Default/History"),help="Path to Chrom(e|ium) history file")
parser.add_option("-s","--pickle", dest="stored", action="append", default=[], help="Add other pickled links files")
opts, args = parser.parse_args()

if not exists(opts.path):
	parser.error("History path '%s' doesn't exist!"%opts.path)

host = compile("http://(en.wikipedia.org)/wiki/([^#]+)")
#enw = compile("http://tvtropes.org/pmwiki/pmwiki.php/Main/(.+)")
#host = compile("http://([^\/]+)/([^\?]+)")
#host = compile("http://((?:tvtropes.org)|(?:en.wikipedia.org))/([^\?]+)")

try:
	conn = sqlite3.connect(opts.path, timeout=1)
	conn.execute("select top(1) from visits")
except sqlite3.OperationalError, e:
	if str(e).find("database is locked")!=-1:
		newpath = join(tempfile.gettempdir(), "History")
		shutil.copyfile(opts.path, newpath)
		conn = sqlite3.connect(newpath)
c = conn.cursor()

links = {}

for f in opts.stored:
	extra = load(open(f))
	for begin in extra:
		if begin not in links:
			links[begin] = set()
		links[begin].update(extra[begin])

c.execute("select urls1.id,urls1.url, visits1.visit_time, urls2.url from visits as visits1,urls as urls1,urls as urls2,visits as visits2 where visits1.url = urls1.id and visits1.from_visit != 0 and visits1.from_visit = visits2.id and visits2.url = urls2.id")

def cleanup(name):
	return unquote(name.replace("_", " "))

for row in c:
	(id, url, time, ref) = row

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
dotfile = join(tempfile.gettempdir(), "history-dot")
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
	print >>out, "\tsubgraph cluster_%s {"%(p.replace(".", "_").replace("/","_"))
	print >>out, "\t\tlabel=\"%s\";"%p
	for begin, end in prefixes[p]:
		print >>out, "\t\t\"%s\" -> \"%s\";"%(begin, end)
	print >>out, "\t}"

print >>out, "}"
out.close()
cmd = "fdp %s -Tps -o %s"%(dotfile,opts.outfile)
print cmd
system(cmd)
