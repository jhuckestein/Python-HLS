## Class Structure for HLSv1.py Playlists

class Playlist(object):
	def accept(self, validator):
        validator.visit(self)
	## Other methods that act on playlist?
		
	def __str__(self):
        return self.__class__.__name__

class VariantPlaylist(Playlist):
	# Has a list of URLs to media segments (or locally defined) that end in ".ts"
	# Has #EXT-X-PLAYLIST-TYPE the playlist type (LIVE, EVENT, VOD)
	# Has a header that starts with #EXTM3U
	# Has #EXT-X-STREAM-INF tag to indicate next URL identifieds a playlist file
	# Has #EXT-X-STREAM-INF tag which indicates BANDWIDTH attribute
	# Has #EXT-X-STREAM-INF tag which should have a CODECS attribute (RFC 6381)
	# Has #EXT-MEDIA-SEQUENCE which tells the first URL.ts that appears in the file
	# Has #EXT-X-TARGETDURATION which specifies the maximum media file duration
	# Has #EXT-X-VERSION which is the compatibility version of the playlist file
	# Has #EXT-X-ENDLIST in VOD and possibly in EVENT
	
	
class MasterPlaylist(Playlist):
	# Has a header that starts with #EXTM3U
	# Has a #EXT-X-STREAM-INF that has BANDWIDTH, RESOLUTION, & CODEC
	# Line after above is the URL.ts
	# Has a list of object references for each URL.ts media variant
	# They have to be able to create objects of VariantPlaylist

		
class Visitor:
    def __str__(self):
        return self.__class__.__name__
		
class Validator(Visitor): pass
class MasterValidator(Validator): pass
class VariantValidator(Validator): pass

