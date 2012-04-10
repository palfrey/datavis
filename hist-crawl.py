import sqlite3
from re import compile
from os.path import expanduser, join, exists, dirname
import shutil, tempfile
from urllib import unquote
import codecs
from os import system, mkdir
from optparse import OptionParser
from ConfigParser import SafeConfigParser
from types import DictType

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

host = compile("http://(.+)")

niceLabels = {
		compile("google.(?:(?:co.uk)|(?:com))/search\?.*?q=([^&]+)"): "Google search: '%s'",
		compile("google.(?:(?:co.uk)|(?:com))/url\?"): "Google link from search...",
		compile("local.google.(?:(?:co.uk)|(?:com))/maps\?.*?q=([^&]+)"): "Google maps search for '%s'",
		}

links = {}
ends = {}

if not exists(opts.outdir):
	mkdir(opts.outdir)

def simplify(l):
	if l[-1] == "/":
		l = l[:-1]
	return l

def cleanup(name):
	return simplify(unquote(name.replace("_", " ")))

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

def genTree(r, conn, rconn, fwd, prev = None):
	if prev == None:
		prev = [r]
	if r not in conn:
		return ([], prev)
	items = []
	for l in conn[r]:
		if fwd:
			items.append((r,l))
		else:
			items.append((l,r))
		if l not in prev:
			(newitems, prev) = genTree(l, conn, rconn, fwd, prev + [l])
			items.extend(newitems)
			(newitems, prev) = genTree(l, rconn, conn, not fwd, prev + [l])
			items.extend(newitems)
	return (items, prev + list(conn[r]))

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
	print "start", start
	pairs = set(genTree(start, links, ends, True)[0] + genTree(start, ends, links, False)[0])
	if not exists(psfile) and len(pairs) > 1:
		
	
		def comparelinks(one, two):
			return simplify(one) == simplify(two)

		print "pairs", pairs
		inset = set([x[0] for x in pairs] + [x[1] for x in pairs])
		tree = {}
		for link in inset:
			if link.find("?")!=-1:
				(begin, rest) = link.split("?",1)
				bits = begin.split("/")
				bits[-1] += "?" + rest
			else:
				bits = link.split("/")
			current = tree
			for bit in bits[:-1]:
				if bit not in current:
					try:
						current[bit] = {}
					except:
						print current, bit
						raise
				if type(current[bit])!=DictType:
					current[bit] = {"":current[bit]}
				current = current[bit]
			if current.has_key(bits[-1]):
				if type(current[bits[-1]]) != DictType:
					assert comparelinks(link, current[bits[-1]]),(link, current[bits[-1]])
					current[bits[-1]] = simplify(link)
				else:
					assert type(current[bits[-1]]) == DictType, (link, current[bits[-1]])
					assert not current[bits[-1]].has_key("") or comparelinks(link, current[bits[-1]][""]), (link, current[bits[-1]][""])
					current[bits[-1]][""] = simplify(link)
			else:
				current[bits[-1]] = simplify(link)
			print "adding", bits, link
		print "original tree", tree

		def collapsetree(top):
			for k in top:
				#print "top",top
				#print "k", k
				if type(top[k]) == DictType:
					if len(top[k]) == 1:
						sk = top[k].keys()[0]
						nk = k + "/" + sk
						print "collapsing", k, sk
						top[nk] = top[k][sk]
						del top[k]
						if type(top[nk]) != DictType:
							continue
						k = nk
					collapsetree(top[k])

		out = codecs.open(dotfile, "wb", "utf-8")
		print >>out, "digraph links {"
		print >>out, "\tgraph [overlap=\"false\", sep=\"+2,2\"];"

		collapsetree(tree)
		print "collapse tree",tree

		def makeLink(link):
			l = safeLink.sub("_", link)
			if l[0].isdigit():
				l = "_" + l
			return l

		def makeLabel(link, fulllink):
			for k in niceLabels:
				m = k.search(fulllink)
				if m!=None:
					return (niceLabels[k] % m.groups()).replace("+", " ")
			return link.replace("\"", "_")[:100]

		def writeTree(top, insert = "\t"):
			for k in top:
				if type(top[k]) == DictType:
					print >> out, insert + "subgraph cluster_%s {"%(makeLink(k))
					print >> out, insert + "\tlabel=\"%s\";"%makeLabel(k, k)
					writeTree(top[k], insert + "\t")
					print >> out, insert + "}"
				else:
					print >> out, insert + "%s [label =\"%s\"];"%(makeLink(top[k]), makeLabel(k, top[k]))

		writeTree(tree)


		for (a, b) in pairs:
			print >>out, "\t\"%s\" -> \"%s\";" % (
				makeLink(a), makeLink(b)
			)
		print >>out, "}"
		out.close()
		for prog in ("dot", "fdp", "neato"):
			cmd = prog + " \"%s\" -Tps -o \"%s\""%(dotfile, psfile)
			print cmd
			ret = system(cmd)
			if ret == 0:
				break
			print "ret", ret
		else:
			raise Exception, "All graphviz commands failed for %s" % dotfile
	removePairs(links, pairs, True)
	removePairs(ends, pairs, False)
