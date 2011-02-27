import sqlite3
from re import compile
from os.path import expanduser, join
import shutil, tempfile
from urllib import unquote
import codecs
from sys import argv
from os import system

assert len(argv)==2

enw = compile("http://en.wikipedia.org/wiki/([^#]+)")

path = expanduser("~/.config/chromium/Default/History")

try:
	conn = sqlite3.connect(path, timeout=1)
	conn.execute("select top(1) from visits")
except sqlite3.OperationalError, e:
	if str(e).find("database is locked")!=-1:
		newpath = join(tempfile.gettempdir(), "History")
		shutil.copyfile(path, newpath)
		conn = sqlite3.connect(newpath)
c = conn.cursor()

links = {}

c.execute("select urls1.id,urls1.url, visits1.visit_time, urls2.url from visits as visits1,urls as urls1,urls as urls2,visits as visits2 where visits1.url = urls1.id and visits1.from_visit != 0 and visits1.from_visit = visits2.id and visits2.url = urls2.id")

def cleanup(name):
	return unquote(name.replace("_", " "))

for row in c:
	(id, url, time, ref) = row

	end = enw.search(url)
	begin = enw.search(ref)

	if begin and end:
		begin = cleanup(begin.groups()[0])
		end = cleanup(end.groups()[0])
		if begin == end:
			continue
		if begin not in links:
			links[begin] = set()
		links[begin].add(end)

dotfile = join(tempfile.gettempdir(), "history-dot")
out = codecs.open(dotfile, "wb", "utf-8")

print >>out, "digraph wikipedia {"
print >>out, "graph [overlap=\"false\", sep=\"+8,8\"];"

for begin in sorted(links):
	for end in sorted(links[begin]):
		print >>out, "\"%s\" -> \"%s\";"%(begin, end)

print >>out, "}"
system("twopi %s -Tps -o %s"%(dotfile,argv[1]))
