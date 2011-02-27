import sqlite3
from re import compile

enw = compile("http://en.wikipedia.org/wiki/([^#]+)")

conn = sqlite3.connect("History")
c = conn.cursor()

links = {}

#c.execute("select urls1.url, visits.visit_time, urls2.url from visits,urls as urls1,urls as urls2 where visits.url = urls1.id and visits.from_visit = urls2.id")
c.execute("select urls1.id,urls1.url, visits1.visit_time, urls2.url from visits as visits1,urls as urls1,urls as urls2,visits as visits2 where visits1.url = urls1.id and visits1.from_visit != 0 and visits1.from_visit = visits2.id and visits2.url = urls2.id")
for row in c:
	(id, url, time, ref) = row

	end = enw.search(url)
	begin = enw.search(ref)

	if begin and end:
		begin = begin.groups()[0]
		end = end.groups()[0]
		if begin not in links:
			links[begin] = set()
		links[begin].add(end)

print "digraph wikipedia {"

for begin in sorted(links):
	for end in sorted(links[begin]):
		print "%s -> %s;"%(begin, end)

print "}"
