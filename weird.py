from pylast import *
import math

class ListenerCache:
	def __init__(self, key=None, secret=None):
		self.net = LastFMNetwork(api_key=key, api_secret=secret)
		self.cachePath = "track.cache"
		self.net.enable_caching(self.cachePath)

	def recent_tracks(self, user):		
		user = self.net.get_user(username=user)
		#self.net.disable_caching()
		tracks = user.get_recent_tracks(limit=200)
		#self.net.enable_caching(self.cachePath)
		return tracks

	def listener_count(self, track):
		return track.get_listener_count()
		
lc = ListenerCache(key="9d388089456b20ea34b1f87e09017e9d", secret="8671d6c7022130f6919ecb3622504219")
tracks = lc.recent_tracks("lshift")

for t in tracks:
	print math.log(lc.listener_count(t.track),2), t.track
