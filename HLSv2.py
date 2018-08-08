####################################
#
# HLS1.0 Hypertext Live Streaming Validator
# by James Huckestein
# jameshuckestein@juno.com
#
####################################
#
# This HLS validator verifies the the Media playlist and
# Master playlist variants for Apple's HLS specification.
# The program can be run in command line, or batch mode
# where an input file is used to to specify targets.
#
# Program Flow:
#   1) Get a playlist URL from the user (command or batch mode)
#   2) Retrieve playlist file from web server or disk
#   3) Validate the playlist file
#   4) Produce a report
#
# Running the Program:
#   >python HLSv1.py <format: batch> <batch-file-name>
#   >python HLSv1.py <format: command> <valid-URL>
#
####################################
####################################
#
# RELEASE-2 NOTES:
# HLSv2.py is an upgrade of HLSv1.py.  In this release the following
# functionality is being added to the previously tested program:
#   1) The VariantPlaylist and MasterPlaylist classes will be extended
#      where the visitor objects will write specific check attributes
#      to the playlist objects.  The definitions will be notated in
#      the playlist objects, and added to the visitors so that when
#      a check is performed and fails the check, line number, reason
#      etc. will be returned to the visitor.
#   2) Expanded information will be returned to the visitor classes
#      that perform the checks.  The expanded print functions will not 
#      be added until Release-3.  So, the expanded check information will
#      be returned to the visitor which will write the information to the 
#      playlist object, but will use checkResults[] for printing output.
#
####################################

##Begin package import section
import sys
import json
import logging
import requests

##End package import section

##Set up logging for the program
logging.basicConfig(filename='Hlsv2.log', level=logging.DEBUG)

##Class definitions for the playlist hierarchy
class Playlist(object):
	def accept(self, validator):
		validator.visit(self)
		
	def __str__(self):
		return self.__class__.__name__
		
	def checkHeader(self, validator):
		check = False
		if self.master:
			if self.mContent[0] == '#EXTM3U':
				check = True
		else:
			if self.vContent[0] == '#EXTM3U':
				check = True
		return check
		
	def masVersion(self, validator):
		# A playlist file must not contain more than one EXT-X-VERSION tag (ERROR)
		
		logging.info("++---------->> Beginning version check for Master object")
		multiple = False      #boolean result for check 1)
		versionInstance = 0   #integer for number of EXT-X-VERSION tags found
		version = 0           #integer for extracted version number
		lineNums = []         #Keeps track of line numbers where multiple tags found
		lineNums.clear
		
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-VERSION:'):
				versionInstance += 1
				logging.info("++---------->> #EXT-X-VERSION tag found on line %s", line)
				lineNums.append(line)
				version = int(self.mContent[line].strip('#EXT-X-VERSION:'))
		if versionInstance > 1:
			multiple = True
		logging.info("++---------->> Number of EXT-X-VERSION tags found = %s", versionInstance)
		logging.info("++---------->> Version of Master object = %s", version)
		logging.info("++---------->> Leaving version check for Master object")
		return multiple, version, lineNums
				
		
	def varVersion(self, validator):
		# A playlist file must not contain more than one EXT-X-VERSION tag (ERROR)
		
		logging.info("++---------->> Beginning version check for Variant object")
		multiple = False      #Assumed false unless versionInstance > 1
		versionInstance = 0   #integer for number of EXT-X-VERSION tags found
		version = 0           #integer for extracted version number
		lineNums = []         #Keeps track of line numbers where multiple tags found
		lineNums.clear
		
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-VERSION:'):
				versionInstance += 1
				logging.info("++---------->> #EXT-X-VERSION tag found on line %s", line)
				lineNums.append(line)
				version = int(self.vContent[line].strip('#EXT-X-VERSION:'))
		if versionInstance > 1:
			multiple = True
		logging.info("++---------->> Number of EXT-X-VERSION tags found = %s", versionInstance)
		logging.info("++---------->> Version of Variant object = %s", version)
		logging.info("++---------->> Leaving version check for Variant object")
		return multiple, version, lineNums
		
	def mCompVersion(self, validator):
		# 1) Must be 7+ if Master has SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA (ERROR)
		# 2) If 6+ PROGRAM-ID attribute for EXT-X-STREAM-INF and EXT-X-I-FRAME-STREAM-INF removed (WARNING)
		# 3) If 7+ EXT-X-ALLOW-CACHE removed
		
		logging.info("++------------------------------>> Entering mCompVersion")
		compService = True  #Validation status for 1) - SERVICE values for INSTREAM-ID
		compProgram = True  #Validation status for 2) - PROGRAM-ID attribute
		compCache = True    #Validation status for 3) - EXT-X-ALLOW-CACHE
		lineNums = []
		lineNums.clear
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-MEDIA'):
				if 'INSTREAM-ID' and 'SERVICE' in self.mContent[line]:
					if self.playVersion < 7:
						compService = False
						lineNums.append('INSTREAM-ID and SERVICE require version 7+ on line= ' + str(line))
			elif self.mContent[line].startswith('#EXT-X-STREAM-INF'):
				if self.playVersion < 6 and 'PROGRAM-ID' in self.mContent[line]:
					compProgram = False
					lineNums.append('EXT-X-STREAM-INF used with PROGRAM-ID requires version 6+ line= ' + str(line))
			elif self.mContent[line].startswith('#EXT-X-I-FRAME-STREAM-INF'):
				if self.playVersion < 6 and 'PROGRAM-ID' in self.mContent[line]:
					compProgram = False
					lineNums.append('EXT-X-I-FRAME-STREAM-INF tag used with PROGRAM-ID requires version 6+ line= ' + str(line))
			elif self.playVersion >= 7:
				if 'EXT-X-ALLOW-CACHE' in self.mContent[line]:
					compCache = False
					lineNums.append('EXT-X-ALLOW-CACHE tag NOT allowed in version 7+ line= ' + str(line))
		logging.info("++------------------------------>> Leaving mCompVersion")
		return compService, compProgram, compCache, lineNums
	
	def vCompVersion(self, validator):
		# Must be 2+ if IV attribute of EXT-X-KEY:IV tag(ERROR)
		# Must be 3+ if floating point EXTINF values (ERROR)
		# Must be 4+ if contains EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags (ERROR)
		# Must be 5+ if has EXT-X-MAP (ERROR)
		# Must be 6+ if Media playlist & EXT-X-MAP does not contain EXT-X-I-FRAMES-ONLY (ERROR)
		# If 7+ EXT-X-ALLOW-CACHE removed
		logging.info("++------------------------------>> Entering vCompVersion")
		check2 = True  #Status of IV attribute of EXT-X-KEY:IV
		check3 = True  #Status of floating point EXTINF values
		check4 = True  #Status of EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY
		check5 = True  #Status of EXT-X-MAP
		check6 = True  #Status of EXT-X-MAP does not contain EXT-X-I-FRAMES-ONLY
		check7 = True  #Status of EXT-X-ALLOW-CACHE removed
		iFrames = False #True if the EXT-X-I-FRAMES-ONLY tag is found
		lineNums = []
		lineNums.clear
		
		#Fist iterate through the list to find if certain tags exist
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-I-FRAMES-ONLY'):
				iFrames = True
		#Now iterate through the list and make our checks
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-KEY:IV'):
				check2 = False
				lineNums.append('EXT-X-KEY:IV tag on line: ' + str(line))
			elif self.vContent[line].startswith('#EXTINF:'):
				tag = self.vContent[line].strip('#EXTINF:')
				if self.playVersion < 3 and '.' in tag:   #Decimals not allowed below version-3
					if tag.find('.') < 3:    #EXTINF:<duration>,<title> and title could have period
						check3 = False
						lineNums.append('EXTINF tag with decimals & Version less than 3.0  on line= ' + str(line))
			elif self.vContent[line].startswith('#EXT-X-BYTERANGE:') and self.playVersion < 4:
				check4 = False
				lineNums.append('EXT-X-BYTERANGE tag & Version < 4 on line= ' + str(line))
			elif self.vContent[line].startswith('#EXT-X-I-FRAMES-ONLY') and self.playVersion < 4:
				check4 = False
				lineNums.append('EXT-X-I-FRAMES-ONLY tag & Version < 4 on line= ' + str(line))
			elif self.vContent[line].startswith('#EXT-X-MAP'):
				if iFrames:
					if self.playVersion < 5:
						check5 = False
						lineNums.append('EXT-X-MAP tag & I-Frames with Version < 5 on line= ' + str(line))
				else:
					if self.playVersion < 6:
						check6 = False
						lineNums.append('EXT-X-MAP tag without I-Frames & Version < 6 on line= ' + str(line))
			elif self.vContent[line].startswith('#EXT-X-ALLOW-CACHE') and self.playVersion >= 7:
				check7 = False
				lineNums.append('EXT-X-ALLOW-CACHE tag & Version 7+ on line= ' + str(line))
			logging.info("++------------------------------>> Leaving vCompVersion")
			return check2, check3, check4, check5, check6, check7, lineNums
			
	def mMixCheck(self, validator):
	#This check determines if Master Playlists contain Media or Variant tags
		logging.info("++------------------------------>> Entering mMixCheck")
		mixedTags = False
		lineNums = []
		lineNums.clear
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXTINF:') or self.mContent[line].startswith('#EXT-X-BYTERANGE:'):
				mixedTags = True
				lineNums.append('#EXTINF/#EXT-X-BYTERANGE found on line= ' + str(line))
			elif self.mContent[line].startswith('#EXT-X-DISCONTINUITY:') or self.mContent[line].startswith('#EXT-X-KEY:'):
				mixedTags = True
				lineNums.append('#EXT-X-DISCONTINUITY/#EXT-X-KEY found on line= ' + str(line))
			elif self.mContent[line].startswith('EXT-X-MAP:') or self.mContent[line].startswith('#EXT-X-PROGRAM-DATE-TIME:'):
				mixedTags = True
				lineNums.append('EXT-X-MAP/EXT-X-PROGRAM-DATE-TIME found on line= ' + str(line))
			elif self.mContent[line].startswith('#EXT-X-DATERANGE:') or self.mContent[line].startswith('#EXT-X-TARGETDURATION:'):
				mixedTags = True
				lineNums.append('EXT-X-DATERANGE/EXT-X-TARGETDURATION found on line= ' + str(line))
			elif self.mContent[line].startswith('#EXT-X-MEDIA-SEQUENCE:') or self.mContent[line].startswith('#EXT-X-ENDLIST:'):
				mixedTags = True
				lineNums.append('EXT-X-MEDIA-SEQUENCE/EXT-X-ENDLIST found on line= ' + str(line))
			elif self.mContent[line].startswith('#EXT-X-PLAYLIST-TYPE:') or self.mContent[line].startswith('#EXT-X-I-FRAMES-ONLY:'):
				mixedTags = True
				lineNums.append('EXT-X-PLAYLIST-TYPE/EXT-X-I-FRAMES-ONLY found on line= ' + str(line))
			elif self.mContent[line].startswith('#EXT-X-DISCONTINUITY-SEQUENCE:'):
				mixedTags = True
				lineNums.append('EXT-X-DISCONTINUITY-SEQUENCE found on line= ' + str(line))
		return mixedTags, lineNums
		logging.info("++------------------------------>> Exiting  mMixCheck")
			
	def vMixCheck(self, validator):
	#This check determines if Variant/Media playlists contain Master tags
		logging.info("++------------------------------>> Entering vMixCheck")
		mixedTags = False
		lineNums = []
		lineNums.clear
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-MEDIA:') or self.vContent[line].startswith('#EXT-X-STREAM-INF:'):
				mixedTags = True
				lineNums.append('EXT-X-MEDIA/EXT-X-STREAM-INF found on line= ' + str(line))
			if self.vContent[line].startswith('#EXT-X-I-FRAME-STREAM-INF:') or self.vContent[line].startswith('#EXT-X-SESSION-DATA:'):
				mixedTags = True
				lineNums.append('EXT-X-I-FRAME-STREAM-INF/EXT-X-SESSION-DATA found on line= ' + str(line))
			if self.vContent[line].startswith('#EXT-X-SESSION-KEY:'):
				mixedTags = True
				lineNums.append('EXT-X-SESSION-KEY found on line= ' + str(line))
		return mixedTags, lineNums
		logging.info("++------------------------------>> Exiting  vMixCheck")
		
	def mStreamInf(self, validator):
	#This check looks to see if the EXT-X-STREAM-INF tag in a master playlist is
	#followed by a URI line, and if the BANDWIDTH attribute is present.
		logging.info("++----------------------------->> Entering mStreamInf")
		nextLine = False  #Will be set true if next line does not contain .m3u8
		bwAttr = True     #Will be set to false if no ATTRIBUTE in tag
		lineNums = []
		lineNums.clear
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-STREAM-INF:'):
				if self.mContent[line].count('BANDWIDTH') < 1:
					bwAttr = False
					lineNums.append('EXT-X-STREAM-INF tag does NOT have BANDWIDTH attribute line= ' + str(line))
				if  not self.mContent[line + 1].endswith('.m3u8'):
					nextLine = True
					lineNums.append('EXT-X-STREAM-INF tag NOT followed by URI on line= ' + str(line))
		logging.info("++----------------------------->> Exiting mStreamInf")
		return nextLine, bwAttr, lineNums
		
	def vStreamInf(self, validator):
	#This check looks to see if the EXT-X-STREAM-INF tag is present in a variant file.
	#This is a violation, and an ERROR.
		logging.info("++----------------------------->> Entering vStreamInf")
		checkV = False
		lineNums = []
		lineNums.clear
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-STREAM-INF:'):
				checkV = True
				lineNums.append('EXT-X-STREAM-INF found on line= ' + str(line))
		logging.info("++----------------------------->> Exiting vStreamInf")
		return checkV, lineNums
	
	def mIFrame(self, validator):
	#This check applies to Master Playlists and if this tag is used it must have
	#a BANDWIDTH and URI attribute
		logging.info("++----------------------------->> Entering mIFrame")
		bwAttr = True
		uriAttr = True
		lineNums = []
		lineNums.clear
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-I-FRAME-STREAM-INF:'):
				if self.mContent[line].count('BANDWIDTH') < 1:
					bwAttr = False
					lineNums.append('EXT-X-I-FRAME-STREAM-INF tag missing BANDWIDTH on line= ' + str(line))
				if self.mContent[line].count('URI') < 1:
					uriAttr = False
					lineNums.append('EXT-X-I-FRAME-STREAM-INF tag missing URI on line= ' + str(line))
		logging.info("<<-----------------------------++ Exiting mIFrame")
		return bwAttr, uriAttr, lineNums
		
	def mSessionData(self, validator):
	#This check applies to Master Playlists and if this tag is used it must have
	#a DATA-ID attribute.  It must also have one of: URI formatted as JSON or a value
	#but, may not have a value and a URI.
		logging.info("++----------------------------->> Entering mSessionData")
		dCheck = False  #If the checks are violated, json, uri, and/or multiples
		json = False   #will be set to True and returned.
		uri = False
		missing = False
		multiples = False
		tagList = []   #used to keep track of lines with the tag for multiples portion
		tagList.clear
		possibleMults = [] #list of possible multiples
		possibleMults.clear
		dIDList = []       #Used to keep track of DATA-ID values for multiple tags
		dIDList.clear
		langList = []      #Used to keep track of LANGUAGE values for multiples
		langList.clear
		iterList = []      #Working list used for parsing possible multiple tags
		iterList.clear
		multiLines = []    #Keeps track of DATA-ID:LANGUAGE lines
		multiLines.clear
		lineNums = []      #Returned list for errors and line numbers
		lineNums.clear
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-SESSION-DATA'):
				#If you have the tag DATA-ID must be present
				if not 'DATA-ID' in self.mContent[line]:
					dCheck = True
					lineNums.append('EXT-X-SESSION-DATA Must have DATA-ID attribute on line= ' + str(line))
				#If you have a VALUE it must be json formatted
				if 'VALUE' in self.mContent[line]:
					if 'URI' in self.mContent[line]:
						uri = True
						lineNums.append('VALUE may not be used with URI line= ' + str(line))
				if 'URI' in self.mContent[line]:
					if not '.json' in self.mContent[line]:
						json = True
						lineNums.append('URI MUST be JSON formatted line= ' + str(line))
				#VALUE not found, so URI must be present
				elif not 'URI' in self.mContent[line]:
					missing = True
					lineNums.append('EXT-X-SESSION-DATA Must have URI formatted as JSON or a VALUE line= ' + str(line))
				tagList.append(self.mContent[line])
				multiLines.append(line)
		if len(tagList) > 0:  #If no tags found not an issue
			logging.info("++------------------->> mSessionData possible multiples")
			#Filter out all of the possible multiple DATA-ID:LANGUAGE tags
			for l in range(0, len(tagList)):
				if 'DATA-ID' in tagList[l] and 'LANGUAGE' in tagList[l]:
					possibleMults.append(tagList[l])
				else:
					multiLines.pop(l)  #If not a match, remove the line number from the list
			#Current logic: now that we have a list of possible multiples we need to split(")
			#each line to extract the first and third elements.  If that set matches another
			#set, then we have a multiple DATA-ID and LANGUAGE and multiples is set to True.
			
			#Extract the values into new lists we can compare
			for k in range(0, len(possibleMults)):
				iterList = possibleMults[k].split('"')
				dIDList.append(iterList[1])
				langList.append(iterList[3])
				iterList.clear()
				
			#Now iterate through the dIDList and look for multiples
			for k in range(0, len(dIDList)):
				logging.info("++---------->> DATA-ID= %s", dIDList[k])
				logging.info("++---------->> LANGUAGE= %s", langList[k])
				for j in range(k+1, len(dIDList)):
					if dIDList[k] == dIDList[j] and langList[k] == langList[j]:
						multiples = True
			if multiples:
				lineNums.append('DATA-ID:LANGUAGE Lines to check for duplicates= ' + str(multiLines))
						
			logging.info("<<-------------------++ mSessionData possible multiples")
		logging.info("<<-----------------------------+++ Exiting mSessionData")
		return dCheck, json, uri, multiples, lineNums
		
	def mMediaMaster(self, validator):
		#The EXT-X-INDEPENDENT-SEGMENTS tag and EXT-X-START tag may appear in either
		#a Master or Variant playlist.  They MUST only appear once in the playlist.  Additionally,
		#the START tag also has a REQUIRED TIME-OFFSET attribute (if the optional tag is used.)
		logging.info("++------------------------------>> Entering mMediaMaster")
		segCount = 0   #counter used to keep track of the number of SEGMENTS tags
		startCount = 0 #counter used to keep track of the number of START tags
		segments = False  #Result of segments test where True indicates a Failure
		start = False     #Result of START test where True indicates a Failure
		tOffset = False   #Result of Time offset attribute where True indicates a failure
		lineNums = []      #Returned list for errors and line numbers
		lineNums.clear
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-INDEPENDENT-SEGMENTS'):
				segCount += 1
				lineNums.append('EXT-X-INDEPENDENT-SEGMENTS on line=' + str(line))
			elif self.mContent[line].startswith('#EXT-X-START'):
				startCount += 1
				lineNums.append('EXT-X-START on line= ' + str(line))
				if 'TIME-OFFSET' not in self.mContent[line]:
					tOffset = True
					lineNums.append('EXT-X-START tag missing on line= ' + str(line))
		if segCount > 1:
			segments = True
		if startCount > 1:
			start = True
		logging.info("<<------------------------------++ Exiting mMediaMaster")
		return segments, start, tOffset, lineNums
		
	def vMediaMaster(self, validator):
		#The EXT-X-INDEPENDENT-SEGMENTS tag and EXT-X-START tag may appear in either
		#a Master or Variant playlist.  They MUST only appear once in the playlist.  Additionally,
		#the START tag also has a REQUIRED TIME-OFFSET attribute (if the optional tag is used.)
		logging.info("++------------------------------>> Entering vMediaMaster")
		segCount = 0   #counter used to keep track of the number of SEGMENTS tags
		startCount = 0 #counter used to keep track of the number of START tags
		segments = False  #Result of segments test where True indicates a Failure
		start = False     #Result of START test where True indicates a Failure
		tOffset = False   #Result of Time offset attribute where True indicates a failure
		lineNums = []      #Returned list for errors and line numbers
		lineNums.clear
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-INDEPENDENT-SEGMENTS'):
				segCount += 1
				lineNums.append('EXT-X-INDEPENDENT-SEGMENTS on line=' + str(line))
			elif self.vContent[line].startswith('#EXT-X-START'):
				startCount += 1
				lineNums.append('EXT-X-START on line= ' + str(line))
				if 'TIME-OFFSET' not in self.vContent[line]:
					tOffset = True
					lineNums.append('EXT-X-START tag missing on line= ' + str(line))
		if segCount > 1:
			segments = True
		if startCount > 1:
			start = True
		logging.info("<<------------------------------++ Exiting vMediaMaster")
		return segments, start, tOffset, lineNums
		
	def vTargetDuration(self, validator):
		#This method ensures that this tag only appears once in a playlist, and the EXTINF duration 
		#must be less than or equal to this maximum amount.
		logging.info("++------------------------------>> Entering vTargetDuration")
		count = 0         #Keeps track of the number of times this tag is found in playlist
		duration = 0.0    #Duration from EXTINF tag
		maxDuration = 0.0 #Duration from Targetduration tag (the max value)
		delim = 0       #Used to note the position of ',' in the tag for slicing the duration value
		check = False   #Returned as True if TARGETDURATION tag present
		multTag = False #Returned as True if too many tags 
		durationCheck = False  #Returned as True if duration > maxDuration
		lineNums = []      #Returned list for errors and line numbers
		lineNums.clear
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-TARGETDURATION'):
				check = True
				count = count + 1
				if count == 1:
					lineNums.append('First EXT-X-TARGETDURATION tag found on line= ' + str(line))
				maxDuration = float(self.vContent[line].strip('#EXT-X-TARGETDURATION:'))
				if count > 1:
					multTag = True
					lineNums.append('Extra EXT-X-TARGETDURATION tag found on line= ' + str(line))
			if self.vContent[line].startswith('#EXTINF:'):
				duration = float(self.vContent[line].strip('#EXTINF:,'))
				if duration > maxDuration:
					durationCheck = True
					lineNums.append('EXTINF value exceeds Max on line= ' + str(line))
		logging.info("<<------------------------------++ Exiting vTargetDuration")
		return check, multTag, durationCheck, lineNums
	
	def vMediaSequence(self, validator):
		#This method ensures that the optional EXT-X-MEDIA-SEQUENCE tag appears only once in a playlist
		#and if present appears before the first media segment in the playlist.
		logging.info("++------------------------------>> Entering vMediaSequence")
		count = 0         #Keeps track of the number of times this tag is found in playlist
		medSeg = False  #Set to True when a media-segment.ts is encountered
		check = False   #Returned as True if EXT-X-MEDIA-SEQUENCE tag present and before first media segment
		multTag = False #Returned as True if too many tags 
		lineNums = []      #Returned list for errors and line numbers
		lineNums.clear
		for line in range(0, len(self.vContent)):
			if self.vContent[line].endswith('.ts'):
				medSeg = True
			if self.vContent[line].startswith('#EXT-X-MEDIA-SEQUENCE'):
				count = count + 1
				if not medSeg:
					check = True
					lineNums.append('EXT-X-MEDIA-SEQUENCE found before Media Segment line= ' + str(line))
				else:
					lineNums.append('EXT-X-MEDIA-SEQUENCE found on line= ' + str(line))
		if count > 1:
			multTag = True
		logging.info("<<------------------------------++ Exiting vMediaSequence")
		return count, check, multTag, lineNums
		
	def vDiscontinuitySequence(self, validator):
	#This method ensures that the optional EXT-X-DISCONTINUITY-SEQUENCE tag appears only once in a playlist
	#and if present appears before the first media segment in the playlist.
		logging.info("++------------------------------>> Entering vDiscontinuitySequence")
		count = 0         #Keeps track of the number of times this tag is found in playlist
		medSeg = False  #Set to True when a media-segment.ts is encountered
		check = False   #Returned as True if EXT-X-DISCONTINUITY-SEQUENCE tag present and before first media segment
		multTag = False #Returned as True if too many tags 
		lineNums = []      #Returned list for errors and line numbers
		lineNums.clear
		for line in range(0, len(self.vContent)):
			if self.vContent[line].endswith('.ts'):
				medSeg = True
			if self.vContent[line].startswith('#EXT-X-DISCONTINUITY-SEQUENCE'):
				count = count + 1
				if not medSeg:
					check = True
					lineNums.append('EXT-X-DISCONTINUITY-SEQUENCE found before first media segment on line= ' + str())
				else:
					lineNums.append('EXT-X-DISCONTINUITY-SEQUENCE found on line= ' + str())
		if count > 1:
			multTag = True
		logging.info("<<------------------------------++ Exiting vDiscontinuitySequence")
		return count, check, multTag, lineNums
		
	def vIFramesOnly(self, validator):
	#This method checks to see if a variant playlist contains the EXT-X-I-FRAMES-ONLY tag, and if it 
	#does, then raises a warning if the EXT-X-MAP tag is not in the file.
		logging.info("++------------------------------>> Entering vIFramesOnly")
		check = False  #Set to True when EXT-X-I-FRAMES-ONLY tag is found
		medSeg = False #Set to True when EXT-X-MAP tag is found
		lineNums = []      #Returned list for errors and line numbers
		lineNums.clear
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-I-FRAMES-ONLY'):
				check = True
			if self.vContent[line].startswith('#EXT-X-MAP'):
				medSeg = True
				lineNums.append('EXT-X-MAP missing on line= ' + str(line))
		logging.info("<<------------------------------++ Exiting vIFramesOnly")
		return check, medSeg, lineNums
		
	# BASIC DEFINITONS USED
	#suppliedURL 		 # The string for URL supplied by the command line or batch file
	#master = Bool 		 # True if a Master playlist, False if variant
	#playVersion         # Integer used to store playlist version, 0 if not used
	
	# RELEASE-2 ADDITIONS
	# ckHeader - A text string set by HeaderCheck() for checkHeader() results
	
	# OTHER ATTRIBUTES
	checkResults = []	 # Used to store the contents of check results

class VariantPlaylist(Playlist):
	# BASIC DEFINITIONS:
	# Has a list of URLs to media segments (or locally defined) that end in ".ts"
	# Has #EXT-X-PLAYLIST-TYPE the playlist type (LIVE, EVENT, VOD)
	# Has a header that starts with #EXTM3U
	# Has #EXT-X-STREAM-INF tag to indicate next URL identifies a playlist file
	# Has #EXT-MEDIA-SEQUENCE which tells the first URL.ts that appears in the file
	# Has #EXT-X-TARGETDURATION which specifies the maximum media file duration
	# Has #EXT-X-VERSION which is the compatibility version of the playlist file
	# Has #EXT-X-ENDLIST in VOD and possibly in EVENT
	
	# RELEASE-2 ADDITIONS:
	# vVersionCk = Text results of VersionCheck()
	# compCheckV2 = Text results Version 2+ if EXT-X-KEY:IV tag
	# compCheckV3 = Text results Version 3+ if floating point EXTINF values
	# compCheckV4 = Text results Version 4+ EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags
	# compCheckV5 = Text results Version 5+ using EXT-X-MAP
	# compCheckV6 = Text results Version 6 ->EXT-X-MAP using EXT-X-I-FRAMES-ONLY
	# compCheckV7 = Text results Version 7+ EXT-X-ALLOW-CACHE removed
	# vTagsResult = Text result from MixTagsCheck()
	# vResultTag = Text result from StreamInfCheck()
	# vSegTag = Text result of INDEPENDENT-SEGMENTS tags check in MediaMasterCheck()
	# vStartTag = Text result of START tags check in MediaMasterCheck()
	# vTimeTag = Text result of REQUIRED TIME-OFFSET tag check in MediaMasterCheck()
	# vTagCheck = Text result for EXT-X-TARGETDURATION Tag in TargetDurationCheck()
	# vMultiTag = Text result for Multiple EXT-X-TARGETDURATION Tags in TargetDurationCheck()
	# vDurCheck = Text result for EXTINF duration values in TargetDurationCheck()
	# vTCount = Text result (exists if) EXT-X-MEDIA-SEQUENCE is NOT present for MediaSequenceCheck()
	# vMedTagCheck = Text result of EXT-X-MEDIA-SEQUENCE appears before media segments in MediaSequenceCheck()
	# vMultiSeqTag = Text result (exists if) Multiple EXT-X-MEDIA-SEQUENCE tags found in MediaSequenceCheck()
	# vDSTCount = Text result (exists if) EXT-X-DISCONTINUITY-SEQUENCE is NOT present from DiscontinuitySequenceCheck()
	# vDSTagCheck = Text result EXT-X-DISCONTINUITY-SEQUENCE appears before media segments from DiscontinuitySequenceCheck()
	# vDSMultiCheck = Text result (exists if) Multiple EXT-X-DISCONTINUITY-SEQUENCE tags from DiscontinuitySequenceCheck()
	# vFrameCheck = Text result (exists if) EXT-X-I-FRAMES-ONLY tag NOT used from IFramesOnlyCheck()
	# vMediaSeg = Text result for EXT-X-MAP tag in IFramesOnlyCheck()
	# 
	
	# OTHER ATTRIBUTES:
	type = []  # EVENT,VOD,LIVE
	vContent = []     #List of content from the original URL
	verCkErrorLines = []  #Lists the lines tags were found for VersionCheck()
	verCompCkErrorLines = [] #Tracks which lines were errors for VerCompatCheck()
	vTagsErrorLines = []   #Tracks which lines were errors for MixTagsCheck()
	vStreamInfLines = []   #Tracks which lines were errors for StreamInfCheck()
	vMediaMasterLines = [] #Tracks which lines were errors for MediaMasterCheck()
	vTargetDurationLines = [] #Tracks which lines were errors for TargetDurationCheck()
	vMediaSequenceLines = [] #Tracks which lines were errors for MediaSequenceCheck()
	vDiscSequenceLines = []  #Tracks which lines were errors for DiscontinuitySequenceCheck()
	vIFramesOnlyLines = []  #Tracks which lines were errors for IFramesOnlyCheck()
	
	
class MasterPlaylist(Playlist):
	# BASIC DEFINITIONS:
	# Has a header that starts with #EXTM3U
	# Has a #EXT-X-STREAM-INF that has BANDWIDTH, RESOLUTION, & CODEC
	# Line after above is the URL.ts
	# Has a list of object references for each URL.ts media variant
	# They have to be able to create objects of VariantPlaylist
	
	# RELEASE-2 ADDITONS:
	# mVersionCk = Text results of VersionCheck()
	# compService = Text results of SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA in VerCompatCheck()
	# compProgram = Text results of PROGRAM-ID attribute for EXT-X-STREAM-INF removed
	# compCache = Text results of Version 7+ EXT-X-ALLOW-CACHE removed
	# mTagsResult = Text results of MixTagsCheck
	# mResultLine = Text result of EXT-X-STREAM-INF tag followed by URI
	# mResultBW = Text result of BANDWIDTH attribute present in tag EXT-X-STREAM-INF
	# pList.mBWidth = Text result of Bandwidth attribute present for IFrameCheck()
	# pList.mURI = Text result of URI attribute present for IFrameCheck()
	# mIDCheck = Text result of EXT-X-SESSION-DATA tag DATA-ID attribute from SessionDataCheck()
	# mJSONCk = Text result of URI attribute JSON formatted from SessionDataCheck()
	# mURICk = Text result of both VALUE and URI attribute from SessionDataCheck()
	# mURI = Text result of URI attribute from SessionDataCheck()
	# mSegTag = Text result of INDEPENDENT-SEGMENTS tags check in MediaMasterCheck()
	# mStartTag = Text result of START tags check in MediaMasterCheck()
	# mTimeTag = Text result of REQUIRED TIME-OFFSET tag check in MediaMasterCheck()
	#
	
	# OTHER ATTRIBUTES:
	variantList = []  #List of variant objects
	variantURLs = []  #List of URLs for each variant object
	mContent = []     #List of content from the original URL
	verCkErrorLines = [] #Tracks which lines were errors for VersionCheck()
	verCompCkErrorLines = [] #Tracks which lines were errors for VerCompatCheck()
	mTagsErrorLines = []  #List of error lines from MixTagsCheck()
	mStreamInfLines = []  #List of error lines from StreamInfCheck()
	mIFrameLines = []  #List of error lines from IFrameCheck()
	mSessionDataLines = [] #List of error lines from SessionDataCheck()
	mMediaMasterLines = [] #List of error lines from MediaMasterCheck()
	


## This is where the visitors (check hierarchy) are defined

class Visitor:
    def __str__(self):
        return self.__class__.__name__
		
class Validator(Visitor): pass
		
class HeaderCheck(Validator):   ## This check is universal to any playlist
	def visit(self, pList):
		logging.info("++---------->> Beginning HeaderCheck Validation")
		if pList.master:
			logging.info("++--------------->> HeaderCheck Master Object")
			pList.checkResults.append("<<-----Begin Master Header Check----->>")
			pList.checkResults.append('')
			result = pList.checkHeader(self)
			if result:
				pList.checkResults.append("PASSED: First line starts #EXTM3U")
				pList.ckHeader = "PASSED: First line starts #EXTM3U"
			else:
				pList.checkResults.append("FAILED: First line starts #EXTM3U")
				pList.ckHeader = "FAILED: First line should start with #EXTM3U"
			pList.checkResults.append('')
			pList.checkResults.append("<<-----End of Header Check----->>")
			pList.checkResults.append('')
			#Now we need to call HeaderCheck for all the Variant objects in pList.variantList
			for variant in range(0, len(pList.variantList)):
				vHCheck = HeaderCheck()
				pList.variantList[variant].accept(vHCheck)
		else:
			#In the event that a Master Playlist calls the for loop above, 
			logging.info("++--------------->> HeaderCheck Variant Object")
			pList.checkResults.append("<<-----Begin Media Header Check----->>")
			pList.checkResults.append('')
			pList.checkResults.append('Variant Playlist =' + pList.suppliedURL)
			result = pList.checkHeader(self)
			if result:
				pList.checkResults.append("PASSED: First line starts #EXTM3U")
				pList.ckHeader = "PASSED: First line starts #EXTM3U"
			else:
				pList.checkResults.append("FAILED: First line starts #EXTM3U")
				pList.ckHeader = "FAILED: First line should start with #EXTM3U"
			pList.checkResults.append('')
			pList.checkResults.append("<<-----End of Header Check----->>")
			pList.checkResults.append('')
		logging.info("++---------->> Leaving HeaderCheck Validation")
			
			
class VersionCheck(Validator):
	#This validator checks to see the number of EXT-X-VERSION tags, and extracts
	#the version number and assigns to the playlist.
	def visit(self, pList):
		logging.info("++------------------------->> Beginning VersionCheck Validation")
		pList.checkResults.append('<<-----Begin Version Checks----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		
		if pList.master:
			test, ver, errorLines = pList.masVersion(self)
			pList.playVersion = ver      #Attribute of the object to be used for compatibility
			if test:
				for line in range(0, len(errorLines)):
					pList.verCkErrorLines.append(errorLines[line])
				logging.info("++---------->> EXT-X-VERSION tag found on lines: %s", pList.verCkErrorLines)
				pList.checkResults.append('Master Playlist =' + pList.suppliedURL)
				pList.checkResults.append('EXT-X-VERSION test: Failed / multiple tags')
				pList.mVersionCk = 'EXT-X-VERSION test: Failed / multiple tags'
				logging.info("++---------->> HeaderCheck Master Validation FAILED")
			else:
				pList.checkResults.append('Master Playlist =' + pList.suppliedURL)
				pList.checkResults.append('PASSED: EXT-X-VERSION test')
				pList.mVersionCk = 'PASSED: EXT-X-VERSION test'
				pList.checkResults.append('VERSION = ' + str(ver))
				logging.info("++---------->> HeaderCheck Master Validation PASSED: " + str(pList.playVersion))
			#Now, the version of the variantList contents need to be checked
			for variant in range(0, len(pList.variantList)):
				verCheck = VersionCheck()
				pList.variantList[variant].accept(verCheck)
		else:
			test, ver, errorLines = pList.varVersion(self)
			pList.playVersion = ver      #Attribute of the object to be used for compatibility
			if test:
				for line in range(0, len(errorLines)):
					pList.verCkErrorLines.append(errorLines[line])
				logging.info("++---------->> EXT-X-VERSION tag found on lines: %s", pList.verCkErrorLines)
				pList.checkResults.append('Variant Playlist =' + pList.suppliedURL)
				pList.checkResults.append('EXT-X-VERSION test: Failed / multiple tags')
				pList.vVersionCk = 'EXT-X-VERSION test: Failed / multiple tags'
				logging.info("++---------->> HeaderCheck Variant Validation FAILED")
			else:
				pList.checkResults.append('Variant Playlist =' + pList.suppliedURL)
				pList.checkResults.append('EXT-X-VERSION test: Passed')
				pList.vVersionCk = 'EXT-X-VERSION test: Passed'
				pList.checkResults.append('VERSION = ' + str(ver))
				logging.info("++---------->> HeaderCheck Variant Validation PASSED: " + str(pList.playVersion))
		pList.checkResults.append('')
		pList.checkResults.append('<<-----End of Version Checks----->>')
				
class VerCompatCheck(Validator):
	#This validator checks the version number against the inclusion/exclusion of certain tags
	def visit(self, pList):
		logging.info("++------------------------->> Beginning Version Compatibility Check Validation")
		pList.checkResults.append('<<-----Begin Compatibility Checks----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		
		if pList.master:
			compatService, compatProgram, compatCache, errorLines = pList.mCompVersion(self)
			logging.info("++---------->> Master Version Compatibility Check")
			logging.info("++---------->> Master compatService = %s", compatService)
			logging.info("++---------->> Master compatProgram = %s", compatProgram)
			logging.info("++---------->> Master compatCache = %s", compatCache)
			pList.checkResults.append('Master Version Compatibility Checks for ' + pList.suppliedURL)
			#If there was an error, then load up the error line list
			if not compatService or not compatProgram or not compatCache:
				for line in range(0, len(errorLines)):
					pList.verCompCkErrorLines.append(errorLines[line])
			if compatService:
				pList.checkResults.append('PASSED: SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA')
				pList.compService = 'PASSED: SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA'
			else:
				pList.checkResults.append('ERROR: Version must be 7+ for SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA')
				pList.compService = 'ERROR: Version must be 7+ for SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA'
			if compatProgram:
				pList.checkResults.append('PASSED: PROGRAM-ID attribute for EXT-X-STREAM-INF removed')
				pList.checkResults.append('PASSED: PROGRAM-ID attribute for EXT-X-I-FRAME-STREAM-INF removed')
				pList.compProgram = 'PASSED: PROGRAM-ID attribute for EXT-X-STREAM and EXT-X-I-FRAME-STREAM-INF removed'
			else:
				pList.checkResults.append('WARNING: Version 6+ PROGRAM-ID attribute for EXT-X-STREAM-INF and EXT-X-I-FRAME-STREAM-INF are removed')
				pList.compProgram = 'WARNING: Version 6+ PROGRAM-ID attribute for EXT-X-STREAM-INF and EXT-X-I-FRAME-STREAM-INF are removed'
			if compatCache:
				pList.checkResults.append('PASSED: Version 7+ EXT-X-ALLOW-CACHE removed')
				pList.compCache = 'PASSED: Version 7+ EXT-X-ALLOW-CACHE removed'
			else:
				pList.checkResults.append('ERROR: Version 7+ EXT-X-ALLOW-CACHE is removed')
				pList.compCache = 'ERROR: Version 7+ EXT-X-ALLOW-CACHE is removed'
			#Now, the contents of the variantList need to be version compatibility checked
			for variant in range(0, len(pList.variantList)):
				versCheck = VerCompatCheck()
				pList.variantList[variant].accept(versCheck)
		else:   #Case where we have a Variant Playlist
			compCkV2, compCkV3, compCkV4, compCkV5, compCkV6, compCkV7, errorLines = pList.vCompVersion(self)
			logging.info("++---------->> Variant Version Compatibility Check")
			logging.info("++---------->> Variant compCkV2 = %s", compCkV2)
			logging.info("++---------->> Variant compCkV3 = %s", compCkV3)
			logging.info("++---------->> Variant compCkV4 = %s", compCkV4)
			logging.info("++---------->> Variant compCkV5 = %s", compCkV5)
			logging.info("++---------->> Variant compCkV6 = %s", compCkV6)
			logging.info("++---------->> Variant compCkV7 = %s", compCkV7)
			pList.checkResults.append('Variant Version Compatibility Checks for ' + pList.suppliedURL)
			if not compCkV2 or not compCkV3 or not compCkV4 or not compCkV5 or not compCkV6 or not compCkV7:
				for line in range(0, len(errorLines)):
					pList.verCompCkErrorLines.append(errorLines[line])
			if compCkV2:
				pList.checkResults.append('PASSED: Version 2+ if EXT-X-KEY:IV tag')
				pList.compCheckV2 = 'PASSED: Version 2+ if EXT-X-KEY:IV tag'
			else:
				pList.checkResults.append('ERROR: Must be 2+ if IV attribute of EXT-X-KEY:IV tag')
				pList.compCheckV2 = 'ERROR: Must be 2+ if IV attribute of EXT-X-KEY:IV tag'
			if compCkV3:
				pList.checkResults.append('PASSED: Version 3+ if floating point EXTINF values')
				pList.compCheckV3 = 'PASSED: Version 3+ if floating point EXTINF values'
			else:
				pList.checkResults.append('ERROR: Must be 3+ if floating point EXTINF values')
				pList.compCheckV3 = 'ERROR: Must be 3+ if floating point EXTINF values'
			if compCkV4:
				pList.checkResults.append('PASSED: Version 4+ EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags')
				pList.compCheckV4 = 'PASSED: Version 4+ EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags'
			else:
				pList.checkResults.append('ERROR: Version 4+ using EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags')
				pList.compCheckV4 = 'ERROR: Version 4+ using EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags'
			if compCkV5:
				pList.checkResults.append('PASSED: Version 5+ using EXT-X-MAP')
				pList.compCheckV5 = 'PASSED: Version 5+ using EXT-X-MAP'
			else:
				pList.checkResults.append('ERROR: Version 5+ using EXT-X-MAP')
				pList.compCheckV5 = 'ERROR: Version 5+ using EXT-X-MAP'
			if compCkV6:
				pList.checkResults.append('PASSED: Version 6 ->EXT-X-MAP using EXT-X-I-FRAMES-ONLY')
				pList.compCheckV6 = 'PASSED: Version 6 ->EXT-X-MAP using EXT-X-I-FRAMES-ONLY'
			else:
				pList.checkResults.append('ERROR: Version 6 ->EXT-X-MAP using EXT-X-I-FRAMES-ONLY')
				pList.compCheckV6 = 'ERROR: Version 6 ->EXT-X-MAP using EXT-X-I-FRAMES-ONLY'
			if compCkV7:
				pList.checkResults.append('PASSED: Version 7+ EXT-X-ALLOW-CACHE removed')
				pList.compCheckV7 = 'PASSED: Version 7+ EXT-X-ALLOW-CACHE removed'
			else:
				pList.checkResults.append('ERROR: Version 7+ EXT-X-ALLOW-CACHE removed')
				pList.compCheckV7 = 'ERROR: Version 7+ EXT-X-ALLOW-CACHE removed'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----End of Compatibility Checks----->>')
		pList.checkResults.append('')
		
class MixTagsCheck(Validator):
	#This Validator checks to see if Variant/Media tags are in a Master Playlist and vice versa
	def visit(self, pList):
		logging.info("++------------------------->> Mixed Tag Validation")
		pList.checkResults.append('<<-----Mixed Tags Checks----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			test, errorLines = pList.mMixCheck(self)
			if test:
				pList.checkResults.append('<<----- FAILED: Master Playlist contains Media/Variant tags ')
				for line in range(0, len(errorLines)):
					pList.mTagsErrorLines.append(errorLines[line])
				pList.mTagsResult = 'FAILED: Master Playlist contains Media/Variant tags'
			else:
				pList.checkResults.append('<<----- PASSED: Master Playlist only contains Master tags ')
				pList.mTagsResult = 'PASSED: Master Playlist only contains Master tags'
		else:
			test, errorLines = pList.vMixCheck(self)
			if test:
				pList.checkResults.append('<<----- FAILED: Media/Variant Playlist contains Master tags ')
				for line in range(0, len(errorLines)):
					pList.vTagsErrorLines.append(errorLines[line])
				pList.vTagsResult = 'FAILED: Media/Variant Playlist contains Master tags'
			else:
				pList.checkResults.append('<<----- PASSED: Media/Variant only contains Media/Variant tags ')
				pList.vTagsResult = 'PASSED: Media/Variant only contains Media/Variant tags'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----Mixed Tags Checks----->>')
		pList.checkResults.append('')
		
class StreamInfCheck(Validator):
	#This Validator checks the EXT-X-STREAM-INF tag in Master playlists, and 
	#checks to see if this is present (which is an ERROR) in variant playlists.
	def visit(self, pList):
		logging.info("++------------------------->> EXT-X-STREAM-INF Tag Validation")
		pList.checkResults.append('<<-----EXT-X-STREAM-INF Tag Checks----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			resultLine, resultBW, errorLines = pList.mStreamInf(self)
			if resultLine or not resultBW:
				for line in range(0, len(errorLines)):
					pList.mStreamInfLines.append(errorLines[line])
			if resultLine:
				pList.checkResults.append('<<----- FAILED: Master> EXT-X-STREAM-INF tag not followed by URI')
				pList.mResultLine = 'FAILED: Master> EXT-X-STREAM-INF tag not followed by URI'
			else:
				pList.checkResults.append('<<----- PASSED: EXT-X-STREAM-INF tags followed by URI')
				pList.mResultLine = 'PASSED: EXT-X-STREAM-INF tags followed by URI'
			if resultBW:
				pList.checkResults.append('<<----- PASSED: BANDWIDTH attribute present in tag')
				pList.mResultBW = 'PASSED: BANDWIDTH attribute present in tag'
			else:
				pList.checkResults.append('<<----- FAILED: BANDWIDTH attribute missing in tag')
				pList.mResultBW = 'FAILED: BANDWIDTH attribute missing in tag'
		else:
			resultTag, errorLines = pList.vStreamInf(self)
			if resultTag:
				pList.checkResults.append('<<----- FAILED: Variant> contains EXT-X-STREAM-INF tag')
				pList.vResultTag = 'FAILED: Variant> contains EXT-X-STREAM-INF tag'
				for line in range(0, len(errorLines)):
					pList.vStreamInfLines.append(errorLines[line])
			else:
				pList.vResultTag = 'PASSED: Variant EXT-X-STREAM-INF tag check'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----EXT-X-STREAM-INF Tag Checks----->>')
		pList.checkResults.append('')

class IFrameCheck(Validator):
	#This Validator checks the EXT-X-I-FRAME-STREAM-INF tag in a Master playlist,
	#and ensures the BANDWIDTH and URI attributes are present.
	def visit(self, pList):
		logging.info("++------------------------->> EXT-X-I-FRAME-STREAM-INF Tag Validation")
		pList.checkResults.append('<<-----EXT-X-I-FRAME-STREAM-INF Tag Validation----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			bWidth, uri, errorLines = pList.mIFrame(self)
			if not bWidth or not uri:
				for line in range(0, len(errorLines)):
					pList.mIFrameLines.append(errorLines[line])
			if not bWidth:
				pList.checkResults.append('<<-----FAILED: BANDWIDTH attribute missing in tag')
				pList.mBWidth = 'FAILED: BANDWIDTH attribute missing in tag'
			if not uri:
				pList.checkResults.append('<<-----FAILED: URI attribute missing')
				pList.mURI = 'FAILED: URI attribute missing'
			if bWidth and uri:
				pList.checkResults.append('<<-----PASSED: BANDWIDTH and URI tags present')
				pList.mBWidth = 'PASSED: Bandwidth attribute present'
				pList.mURI = 'PASSED: URI attribute present'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----EXT-X-I-FRAME-STREAM-INF Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ EXT-X-I-FRAME-STREAM-INF Tag Validation")
	
class SessionDataCheck(Validator):
	#This Validator checks the EXT-X-SESSION-DATA tag for the DATA-ID, URI, VALUE, and multiple
	#occurences of attributes.
	def visit(self, pList):
		logging.info("++------------------------->> EXT-X-SESSION-DATA Tag Validation")
		pList.checkResults.append('<<-----EXT-X-SESSION-DATA Tag Validation----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			idCheck, jsonCk, uriCk, multCk, errorLines = pList.mSessionData(self)
			if idCheck or jsonCk or uriCk or multCk:
				for line in range(0, len(errorLines)):
					pList.mSessionDataLines.append(errorLines[line])
			if idCheck:
				pList.checkResults.append('<<-----FAILED: EXT-X-SESSION-DATA tag missing DATA-ID attribute')
				pList.mIDCheck = 'FAILED: EXT-X-SESSION-DATA tag missing DATA-ID attribute'
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-SESSION-DATA::DATA-ID check')
				pList.mIDCheck = 'PASSED: EXT-X-SESSION-DATA::DATA-ID check'
			if jsonCk:
				pList.checkResults.append('<<-----FAILED: URI attribute not JSON formatted')
				pList.mJSONCk = 'FAILED: URI attribute not JSON formatted'
			else:
				pList.checkResults.append('<<-----PASSED: JSON formatting check')
				pList.mJSONCk = 'PASSED: JSON formatting check'
			if uriCk:
				pList.checkResults.append('<<-----FAILED: TAG may NOT have VALUE and URI attribute')
				pList.mURICk = 'FAILED: TAG may NOT have VALUE and URI attribute'
			else:
				pList.checkResults.append('<<-----PASSED: VALUE/URI check')
				pList.mURICk = 'PASSED: VALUE/URI check'
			if multCk:
				pList.checkResults.append('<<-----FAILED: Multiple DATA-ID attributes with same LANGUAGE')
				pList.mMultCk = 'FAILED: Multiple DATA-ID attributes with same LANGUAGE'
			else:
				pList.checkResults.append('<<-----PASSED: Multiple DATA-ID/LANGUAGE check')
				pList.mMultCk = 'PASSED: Multiple DATA-ID/LANGUAGE check'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----EXT-X-SESSION-DATA Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ EXT-X-SESSION-DATA Tag Validation")

class MediaMasterCheck(Validator):
	#This validator addresses the two tags that can appear in both a Media or Master playlist.
	#The EXT-X-INDEPENDENT-SEGMENTS tag is verified to only have one instance within a file.
	#The EXT-X-START tag is verified to appear only once, and that the TIME-OFFSET attribute is present.
	def visit(self, pList):
		logging.info("++------------------------->> Media & Master Tag Validation")
		pList.checkResults.append('<<-----Media/Master (Joint) Tag Validation----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			segTag, startTag, timeTag, errorLines = pList.mMediaMaster(self)
			pList.checkResults.append('<<----- Master Playlist: ' + pList.suppliedURL)
			if segTag or startTag or timeTag:
				for line in range(0, len(errorLines)):
					pList.mMediaMasterLines.append(errorLines[line])
			if segTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-INDEPENDENT-SEGMENTS tags found')
				pList.mSegTag = 'FAILED: Multiple EXT-X-INDEPENDENT-SEGMENTS tags found'
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-INDEPENDENT-SEGMENTS check')
				pList.mSegTag = 'PASSED: EXT-X-INDEPENDENT-SEGMENTS check'
			if startTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-START tags found')
				pList.mStartTag = 'FAILED: Multiple EXT-X-START tags found'
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START check')
				pList.mStartTag = 'PASSED: EXT-X-START check'
			if timeTag:
				pList.checkResults.append('<<-----FAILED: EXT-X-START:TIME-OFFSET attribute missing')
				pList.mTimeTag = 'FAILED: EXT-X-START:TIME-OFFSET attribute missing'
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START:TIME-OFFSET check')
				pList.mTimeTag = 'PASSED: EXT-X-START:TIME-OFFSET check'
			for variant in range(0, len(pList.variantList)):
				medMasCheck = MediaMasterCheck()
				pList.variantList[variant].accept(medMasCheck)
		else:
			segTag, startTag, timeTag, errorLines = pList.vMediaMaster(self)
			if segTag or startTag or timeTag:
				for line in range(0, len(errorLines)):
					pList.vMediaMasterLines.append(errorLines[line])
			pList.checkResults.append('<<----- Variant Playlist: ' + pList.suppliedURL)
			if segTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-INDEPENDENT-SEGMENTS tags found in variant')
				pList.vSegTag = 'FAILED: Multiple EXT-X-INDEPENDENT-SEGMENTS tags found in variant'
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-INDEPENDENT-SEGMENTS check')
				pList.vSegTag = 'PASSED: EXT-X-INDEPENDENT-SEGMENTS check'
			if startTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-START tags found in variant')
				pList.vStartTag = 'FAILED: Multiple EXT-X-START tags found in variant'
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START check')
				pList.vStartTag = 'PASSED: EXT-X-START check'
			if timeTag:
				pList.checkResults.append('<<-----FAILED: EXT-X-START:TIME-OFFSET attribute missing in variant')
				pList.vTimeTag = 'FAILED: EXT-X-START:TIME-OFFSET attribute missing in variant'
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START:TIME-OFFSET check')
				pList.vTimeTag = 'PASSED: EXT-X-START:TIME-OFFSET check'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----Media/Master (Joint) Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ Media & Master Tag Validation")
	
class TargetDurationCheck(Validator):
	#This check looks at the EXT-X-TARGETDURATION tag (required) and ensures that there is only one
	#instance in a Variant playlist.  It also looks at the EXTINF tag and ensures that the duration value for 
	#each media segment is less than or equal to the maximum value.
	def visit(self, pList):
		logging.info("++------------------------->> TargetDurationCheck Validation")
		pList.checkResults.append('<<-----TargetDurationCheck Tag Validation----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			for variant in range(0, len(pList.variantList)):
				varTargDurCheck = TargetDurationCheck()
				pList.variantList[variant].accept(varTargDurCheck)
		else:
			tagCheck, multiTag, durCheck, errorLines = pList.vTargetDuration(self)
			if not tagCheck or multiTag or durCheck:
				for line in range(0, len(errorLines)):
					pList.vTargetDurationLines.append(errorLines[line])
			pList.checkResults.append('<<----- Variant Playlist: ' + pList.suppliedURL)
			if tagCheck:
				pList.checkResults.append('<<-----PASSED: TARGETDURATION Tag is present')
				pList.vTagCheck = 'PASSED: TARGETDURATION Tag is present'
			else:
				pList.checkResults.append('<<-----FAILED: EXT-X-TARGETDURATION Tag is REQUIRED')
				pList.vTagCheck = 'FAILED: EXT-X-TARGETDURATION Tag is REQUIRED'
			if multiTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-TARGETDURATION Tags Found')
				pList.vMultiTag = 'FAILED: Multiple EXT-X-TARGETDURATION Tags Found'
			else:
				pList.vMultiTag = 'PASSED: No Multiple EXT-X-TARGETDURATION Tags'
			if durCheck:
				pList.checkResults.append('<<-----FAILED: EXTINF duration values greater then Maximum')
				pList.vDurCheck = 'FAILED: EXTINF duration values greater then Maximum'
			else:
				pList.checkResults.append('<<-----PASSED: DURATION for EXTINF tags less than MAX')
				pList.vDurCheck = 'PASSED: DURATION for EXTINF tags less than MAX'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----TargetDurationCheck Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ TargetDurationCheck Validation")
		
class MediaSequenceCheck(Validator):
	#This check looks to see if the optional EXT-X-MEDIA-SEQUENCE appears only once in the playlist
	#and if present after the first media-segment.ts in the playlist.
	def visit(self, pList):
		logging.info("++------------------------->> MediaSequenceCheck Validation")
		pList.checkResults.append('<<-----MediaSequenceCheck Tag Validation----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			for variant in range(0, len(pList.variantList)):
				varMedSeqCheck = MediaSequenceCheck()
				pList.variantList[variant].accept(varMedSeqCheck)
		else:
			tCount, tagCheck, multiTag, errorLines = pList.vMediaSequence(self)
			if not tagCheck or multiTag:
				for line in range(0, len(errorLines)):
					pList.vMediaSequenceLines.append(errorLines[line])
			pList.checkResults.append('<<-----Variant Playlist: ' + pList.suppliedURL)
			if tCount == 0:
				pList.checkResults.append('<<-----PASSED: EXT-X-MEDIA-SEQUENCE is NOT present')
				pList.vTCount = 'PASSED: EXT-X-MEDIA-SEQUENCE is NOT present'
			elif tagCheck:
				pList.checkResults.append('<<-----PASSED: EXT-X-MEDIA-SEQUENCE appears before media segments')
				pList.vMedTagCheck = 'PASSED: EXT-X-MEDIA-SEQUENCE appears before media segments'
			elif not tagCheck:
				pList.checkResults.append('<<-----FAILED: Media Segments appear before EXT-X-MEDIA-SEQUENCE tag')
				pList.vMedTagCheck = 'FAILED: Media Segments appear before EXT-X-MEDIA-SEQUENCE tag'
			elif multiTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-MEDIA-SEQUENCE tags not allowed')
				pList.vMultiSeqTag = 'FAILED: Multiple EXT-X-MEDIA-SEQUENCE tags not allowed'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----MediaSequenceCheck Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ MediaSequenceCheck Validation")
		
class DiscontinuitySequenceCheck(Validator):
	#This check looks to see if the optional EXT-X-DISCONTINUITY-SEQUENCE appears only once in the playlist
	#and if present after the first media-segment.ts in the playlist.
	def visit(self, pList):
		logging.info("++------------------------->> DiscontinuitySequenceCheck Validation")
		pList.checkResults.append('<<-----DiscontinuitySequenceCheck Tag Validation----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			for variant in range(0, len(pList.variantList)):
				varDisSeqCheck = DiscontinuitySequenceCheck()
				pList.variantList[variant].accept(varDisSeqCheck)
		else:
			tCount, tagCheck, multiTag, errorLines = pList.vDiscontinuitySequence(self)
			if not tagCheck or multiTag:
				for line in range(0, len(errorLines)):
					pList.vDiscSequenceLines.append(errorLines[line])
			pList.checkResults.append('<<-----Variant Playlist: ' + pList.suppliedURL)
			if tCount == 0:
				pList.checkResults.append('<<-----PASSED: EXT-X-DISCONTINUITY-SEQUENCE is NOT present')
				pList.vDSTCount = 'PASSED: EXT-X-DISCONTINUITY-SEQUENCE is NOT present'
			elif tagCheck:
				pList.checkResults.append('<<-----PASSED: EXT-X-DISCONTINUITY-SEQUENCE appears before media segments')
				pList.DSTagCheck = 'PASSED: EXT-X-DISCONTINUITY-SEQUENCE appears before media segments'
			elif not tagCheck:
				pList.checkResults.append('<<-----FAILED: Media Segments appear before EXT-X-DISCONTINUITY-SEQUENCE tag')
				pList.DSTagCheck = 'FAILED: Media Segments appear before EXT-X-DISCONTINUITY-SEQUENCE tag'
			elif multiTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-DISCONTINUITY-SEQUENCE tags not allowed')
				pList.vDSMultiCheck = 'FAILED: Multiple EXT-X-DISCONTINUITY-SEQUENCE tags not allowed'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----DiscontinuitySequenceCheck Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ DiscontinuitySequenceCheck Validation")
		
class IFramesOnlyCheck(Validator):
	#This validator checks to see if a variant playlist contains the EXT-X-I-FRAMES-ONLY tag, and if it 
	#does, then raises a warning if the EXT-X-MAP tag is not in the file.
	def visit(self, pList):
		logging.info("++------------------------->> IFramesOnlyCheck Validation")
		pList.checkResults.append('<<-----IFramesOnlyCheck Tag Validation----->>')
		pList.checkResults.append('')
		errorLines = []
		errorLines.clear
		if pList.master:
			for variant in range(0, len(pList.variantList)):
				iFrameOnlyCk = IFramesOnlyCheck()
				pList.variantList[variant].accept(iFrameOnlyCk)
		else:
			frameCheck, mediaSeg, errorLines = pList.vIFramesOnly(self)
			if not mediaSeg:
				for line in range(0, len(errorLines)):
					pList.vIFramesOnlyLines.append(errorLines[line])
			pList.checkResults.append('<<-----Variant Playlist: ' + pList.suppliedURL)
			if not frameCheck:
				pList.checkResults.append('<<-----PASSED: EXT-X-I-FRAMES-ONLY tag NOT used')
				pList.vFrameCheck = 'PASSED: EXT-X-I-FRAMES-ONLY tag NOT used'
			else:
				if mediaSeg:
					pList.checkResults.append('<<-----PASSED: EXT-X-I-FRAMES-ONLY used with media initializaion')
					pList.vMediaSeg = 'PASSED: EXT-X-I-FRAMES-ONLY used with media initializaion'
				else:
					pList.checkResults.append('<<-----WARNING: EXT-X-I-FRAMES-ONLY tag should accompany EXT-X-MAP')
					pList.vMediaSeg = 'WARNING: EXT-X-I-FRAMES-ONLY tag should accompany EXT-X-MAP'
		pList.checkResults.append('')
		pList.checkResults.append('<<-----IFramesOnlyCheck Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ IFramesOnlyCheck Validation")

####################################
#
# This funtion clears out playlist variables that are left over when
# multiple iterations are run successively.
def clearMaster(playL):
	logging.info("++----------------------------------->> Entering clearMaster")
	#PlayList generic attributes are zero-d out
	del playL.suppliedURL
	playL.checkResults.clear()
	del playL.playVersion
	
	# Address Master specific attributes and zero out
	playL.variantList.clear()
	playL.variantURLs.clear()
	playL.mContent.clear()
	logging.info("++----------------------------------->> Leaving clearMaster")
	return playL
#
# End of clearMaster
####################################

####################################
#
# This funtion clears out playlist variables that are left over when
# multiple iterations are run successively.
def clearVariant(playL):
	logging.info("++----------------------------------->> Entering clearVariant")
	#PlayList generic attributes are zero-d out
	del playL.suppliedURL
	playL.checkResults.clear()
	del playL.playVersion
	
	#Now Variant specific attributes are zero-d out
	#playL.type.clear()     - turn on when implemented
	playL.vContent.clear()
	logging.info("++----------------------------------->> Leaving clearVariant")
	return playL

#
# End of clearVariant
####################################

####################################
#
# This function is used to open a URL or file
def openURL(url):
	# valid = whether the URL given is in a valid format to access
	# web = keeps track of whether we have a web/URL or file/URL (local)
	# output is returned if it is a web/URL and fileHandle is returned if a file
	logging.info("++----------------------------------->> Entering openURL")
	logging.info("++---------->> Passed in URL: %s", url)
	# First test if the url has a valid extension .m3u8
	if url.endswith(".m3u8"):
			logging.info("++---------->> openURL Valid(m3u8) YES")
			valid = True
	elif url.endswith(".m3u"):
			logging.info("++---------->> openURL Valid(m3u) YES")
			valid = True
	else:
		logging.info("++---------->> openURL Valid(m3u8/m3u) NO")
		valid = False
	# If the given url starts with http:// then process as a web site
	web = False
	if url.startswith("http://") or url.startswith("https://"):
		logging.info("++---------->> Attempting openURL using http")
		try:
			response = requests.get(url)
			response.raise_for_status()
			if response.headers.get('content-type') == 'application/vnd.apple.mpegurl':
				valid = True
				logging.info("++---------->> openURL Valid via content-type= application/vnd.apple.mpegurl")
			elif response.headers.get('content-type') == 'audio/mpegurl':
				valid = True
				logging.info("++---------->> openURL Valid via content-type= audio/mpegurl")
			output = response.text.encode('ascii', 'ignore')
			web = True
			logging.info("++---------->> openURL: %s", url)
			logging.info("++---------->> The returned output= %s", output)
			logging.info("++---------->> The returned valid= %s", valid)
			logging.info("++---------->> The returned web= %s", web)
			return output, valid, web
		except requests.exceptions.HTTPError as e:
			print ("Error: ", e)
			logging.info("++---------->> openURL Error: %s", e)
			sys.exit(1)
	# If the given url does not start with http:// then presumably the
	# url is a local file so we will open with filehandle
	else:
		try:
			logging.info("++---------->> Attempting openURL using file-handle")
			fileHandle = open(url,'r+')
			logging.info("++---------->> The returned file handle= %s", fileHandle)
			logging.info("++---------->> The returned valid= %s", valid)
			logging.info("++---------->> The returned web= %s", web)
			return fileHandle, valid, web
		except FileNotFoundError as e:
			print("Error: ", e)
			logging.info("++--------->> The user gave a bad File: %s", e)
			sys.exit(1)
		except sys.OSError as e:
			print("Error: ", e)
			logging.info("++---------->> openURL OSError: %s", e)
			sys.exit(1)
#
# End of openURL
####################################

####################################
#
# This function creates MasterPlaylist objects
def createMaster(conList, uRL):
	logging.info("++------------------------->> Entering createMaster")
	logging.info("++--------------->> Master URL: %s", uRL)
	pList = MasterPlaylist()
	pList.master = True
	pList.mContent = []
	pList.suppliedURL = uRL
	for i in range(0, len(conList)):
		pList.mContent.append(conList[i]) #Initialize raw content in Master.content[]
	for i in range(0, len(pList.mContent)):
		#logging to verify the Master object has the correct content
		logging.info("++---------->> pList.content = %s", pList.mContent[i])
	for i in range(0, len(conList)):
		if '.m3u8' in conList[i]:  
			logging.info("++---------->> Found variant %s", conList[i])
			pList.variantURLs.append(conList[i])  #Collect list of variants
			#Before creating the variant we must open a connection to 
			#the variant URL and retrieve contents.
	for j in range(0, len(pList.variantURLs)):
		logging.info("++---------->> pList variantURLs: %s", pList.variantURLs[j])
	for i in range(0, len(pList.variantURLs)):		
		varRsc, validURL, web = openURL(pList.variantURLs[i])
		#Now if/else block for createPlaylist:
		if web == True:
			# Variant Resource can be loaded into an object, but must be decoded
			logging.info("++---------->> Web variant from createMaster:")
			varContents = varRsc.decode('utf-8')
			varContentList = list(varContents.splitlines())
			#Now we have the contents of the URL
			logging.info("++---------->> Created variant contentList of length: %s", len(varContentList))
			for k in range(0, len(varContentList)):
				logging.info("++---------->> varContentList: %s", varContentList[k])
			newVariant = createVariant(varContentList, pList.variantURLs[i])
			for z in range(0, len(newVariant.vContent)):
				logging.info("++---------->> newVariant vContent: %s", newVariant.vContent[z])
			pList.variantList.insert(i,newVariant)
		else:
			# Resource is the filehandle we got from openURL, and the lines can be read
			logging.info("++---------->> File variant from createMaster:")
			varContents = varRsc.read()
			varContentList = list(varContents.split("\n"))
			varRsc.close()
			logging.info("++---------->> Created contentList of length: %s", len(varContentList))
			for l in range(0, len(varContentList)):
				logging.info("++---------->> varContentList: %s", varContentList[l])
			newVariant = createVariant(varContentList, pList.variantURLs[i])
			for z in range(0, len(newVariant.vContent)):
				logging.info("++---------->> newVariant vContent: %s", newVariant.vContent[z])
			pList.variantList.insert(i,newVariant)
	for i in range(0, len(pList.variantList)):
		logging.info("++---------->> contents of pList.variantList: %s", pList.variantList[i])
	for j in range(0, len(pList.variantList)):
		logging.info("++---------->> variantObject: %s", j)
		variantObject = pList.variantList[j]
		for k in range(0, len(variantObject.vContent)):
			logging.info("++---------->> variantObject contents: %s", variantObject.vContent[k])
	logging.info("++------------------------->> Leaving createMaster")
	return pList
#
# End of createMaster
####################################

####################################
#
# This function creates VariantPlaylist objects
def createVariant(contenList, urL):
	logging.info("++------------------------->> Entering createVariant")
	logging.info("++--------------->> Handed-in URL: %s", urL)
	varList = VariantPlaylist()
	varList.master = False
	varList.vContent = []
	for i in range(0, len(contenList)):
		logging.info("++--------------->> Adding contents: %s", contenList[i])
		varList.vContent.append(contenList[i])
	for i in range(0, len(varList.vContent)):
		logging.info("++--------------->> Variant contents: %s", varList.vContent[i])
	varList.suppliedURL = str(urL)
	logging.info("++--------------->> Setting varURL: %s", varList.suppliedURL)
	logging.info("++------------------------->> Leaving createVariant")
	return varList
#
# End of createVariant
####################################

####################################
#
# This function is used to create Playlist Objects.  A MasterPlaylist
# will / can contain VariantPlaylist(s), but a VariantPlaylist will
# only have media files listed.  Both are subclasses of Playlist.
# This function creates both types.
#
def createPlaylist(rsrc, urlFlag, webFlag, URL):
	logging.info("++------------------------->> Entering createPlaylist")
	if webFlag == True:
	# Resource can be loaded into an object, but must be decoded
		logging.info("++---------->> Entered createPlaylist for Web URL:")
		contents = rsrc.decode('utf-8')
		contentList = list(contents.splitlines())
		#Now we have the contents of the URL
		logging.info("++---------->> Created contentList of length: %s", len(contentList))
		
	else:
	# Resource is the filehandle we got from openURL, and the lines can be read
		logging.info("++---------->> Entered createPlaylist for File URL:")
		contents = rsrc.read()
		contentList = list(contents.split("\n"))
		rsrc.close()
		logging.info("++---------->> Created contentList of length: %s", len(contentList))
		
	#Now the contentList is populated, and we need to create either a VariantPlaylist
	#or create a MasterPlaylist.  If we iterate through the contentList, and find a
	#.m3u8 extension, this would identify the playlist as a Master.  Otherwise, the
	#VariantPlaylist does not have any tag with .m3u8 in it.
	
	master = False
	for i in range(0, len(contentList)):
		if '.m3u8' in contentList[i]:
			master = True
	logging.info("++------------>> The playlist object was tested to be Master: %s", str(master))
	
	#Now we know whether the supplied resource was a Master or Variant playlist.  Next,
	#we create the object where a MasterPlaylist will create it's own VariantPlaylist(s).
	
	if master:
		logging.info("++--------------->> Master contentList")
		for i in range(0, len(contentList)):
			logging.info("++--------------->> contentList:" + contentList[i])
		playList = createMaster(contentList, URL)
	else:
		logging.info("++--------------->> Variant contentList")
		for i in range(0, len(contentList)):
			logging.info("++--------------->> contentList:" + contentList[i])
		playList = createVariant(contentList, URL)
	logging.info("++------------------------->> Leaving createPlaylist")
	return playList
#
# End of createPlaylist
####################################


####################################
#
# This is the main program function
def main(argv):
	outputFile = 'output.txt'  #Used for batch mode output to local disk
	
	## First check to see if there are enough inputs, if not provide syntax
	if len(sys.argv) < 3:
		print ("python3.6 HLSv1.py <format: batch> <batch-file-name>")
		print ("python3.6 HLSv1.py <format: command> <valid-URL>")
		sys.exit(-1)

	print('')
	print('')
	print('<<------------------Program Execution---------------------->>')
	print("++-------->> File Program:", sys.argv[0])
	print("++-------->> File FORMAT:", sys.argv[1])
	print("++-------->> File File/URL:", sys.argv[2])
	print('')
	print('')
	logging.info("++-------->> File Program: %s", sys.argv[0])
	logging.info("++-------->> File FORMAT: %s", sys.argv[1])
	logging.info("++-------->> File File/URL: %s", sys.argv[2])
	
	## Batch mode execution block
	if (sys.argv[1] == "batch"):
		logging.info("++---------->> Entered Batch mode:")
		validPlayL = False
		webURL = False
		#so, I need to try and open the file given which contains playlists
		url = sys.argv[2]
		batchFile, validPlayL, webURL = openURL(url)
		outFileHandle, pHold1, pHold2 = openURL(outputFile)  #pHold1 and pHold2 NOT used
		
		#If the user gave us a playlist then we only do this once
		if validPlayL:
			playlist = createPlaylist(batchFile, validPlayL, webURL, url)
			
			#We have a playlist, so run our checks in order
			hCheck = HeaderCheck()
			playlist.accept(hCheck)
			
			vCheck = VersionCheck()
			playlist.accept(vCheck)
			
			vCompCheck = VerCompatCheck()
			playlist.accept(vCompCheck)
			
			mixCheck = MixTagsCheck()
			playlist.accept(mixCheck)
			
			streamInf = StreamInfCheck()
			playlist.accept(streamInf)
			
			iFrame = IFrameCheck()
			playlist.accept(iFrame)
			
			sessDataCheck = SessionDataCheck()
			playlist.accept(sessDataCheck)
			
			mediaMasterCheck = MediaMasterCheck()
			playlist.accept(mediaMasterCheck)
			
			targetDurCheck = TargetDurationCheck()
			playlist.accept(targetDurCheck)
			
			medSeqCheck = MediaSequenceCheck()
			playlist.accept(medSeqCheck)
			
			discontinuitySequenceCheck = DiscontinuitySequenceCheck()
			playlist.accept(discontinuitySequenceCheck)
			
			iFrameOnlyCheck = IFramesOnlyCheck()
			playlist.accept(iFrameOnlyCheck)
			
			#Create a Header in the output file
			outFileHandle.write('<<##--------------------- Report ------------------------##>>\n')
			secondLine = ('The valid m3u8 check for the URL was: ', validPlayL)
			s2 = str(secondLine)
			outFileHandle.write(s2)
			outFileHandle.write('\n')
			thirdLine = ('The playlist was a Master =', playlist.master)
			s3 = str(thirdLine)
			outFileHandle.write(s3)
			outFileHandle.write('\n')
			fourthLine = ('The given URL was =', playlist.suppliedURL)
			s4 = str(fourthLine)
			outFileHandle.write(s4)
			outFileHandle.write('\n')
			
			#Now take the check results and print them to the output file
			for line in range(0, len(playlist.checkResults)):
				outFileHandle.write(playlist.checkResults[line])
				outFileHandle.write('\n')
			outFileHandle.write('<<##--------------- End of Report ---------------##>>')
			outFileHandle.close()
			batchFile.close()
		#Case where the user supplied a text file of playlist files
		else:
			#Create a Header in the output file
			outFileHandle.write('<<##--------------------- Report ------------------------##>>\n')
			secondLine = ('The valid m3u8 check for the URL was: ', validPlayL)
			s2 = str(secondLine)
			outFileHandle.write(s2)
			outFileHandle.write('\n')
			
			#Now process each line in the batch file containing playlist file URLs
			for line in batchFile:
				inputLine = line.strip('\n')
				playListFile, valPlayL, wURL = openURL(inputLine)
				playlist = createPlaylist(playListFile, valPlayL, wURL, inputLine)
				
				#Add formatting to the output file so we know about the file
				outFileHandle.write('<<----------Playlist Report---------->>\n')
				thirdLine = ('The playlist was a Master =', playlist.master)
				s3 = str(thirdLine)
				outFileHandle.write(s3)
				outFileHandle.write('\n')
				fourthLine = ('The given URL was =', playlist.suppliedURL)
				s4 = str(fourthLine)
				outFileHandle.write(s4)
				outFileHandle.write('\n')
				
				#We have a playlist, so run our checks in order
				hCheck = HeaderCheck()
				playlist.accept(hCheck)
				
				vCheck = VersionCheck()
				playlist.accept(vCheck)
				
				vCompCheck = VerCompatCheck()
				playlist.accept(vCompCheck)
				
				mixCheck = MixTagsCheck()
				playlist.accept(mixCheck)
				
				streamInf = StreamInfCheck()
				playlist.accept(streamInf)
				
				iFrame = IFrameCheck()
				playlist.accept(iFrame)
				
				sessDataCheck = SessionDataCheck()
				playlist.accept(sessDataCheck)
				
				mediaMasterCheck = MediaMasterCheck()
				playlist.accept(mediaMasterCheck)
				
				targetDurCheck = TargetDurationCheck()
				playlist.accept(targetDurCheck)
				
				medSeqCheck = MediaSequenceCheck()
				playlist.accept(medSeqCheck)
				
				discontinuitySequenceCheck = DiscontinuitySequenceCheck()
				playlist.accept(discontinuitySequenceCheck)
				
				iFrameOnlyCheck = IFramesOnlyCheck()
				playlist.accept(iFrameOnlyCheck)
				
				#Now print the results to the output file
				for line in range(0, len(playlist.checkResults)):
					outFileHandle.write(playlist.checkResults[line])
					outFileHandle.write('\n')
				
				#Now add some formatting to the output file
				outFileHandle.write('<<--------------------End of Individual Playlist-------------------->>\n')
				outFileHandle.write('\n')
				
				#Now close the playlist file handle
				playListFile.close()
			#Now indicate that the report is concluded
			outFileHandle.write('<<##--------------- End of Report ---------------##>>')
			
			#Close the output file and batchFile
			outFileHandle.close()
			batchFile.close()
	
	## Command line execution block
	elif (sys.argv[1] == "command"):
		execute = True
		url = sys.argv[2]
		logging.info("++---------->> Entered Command Line mode:")
		while execute:
			#Here is where the command line interaction goes.
			#It finishes up with a command line call to the user.
			#urlCheck(boolean) tells whether the given URL is tagged with a valid format, and
			#if this check fails the player has the right to reject the playlist.
			#webCheck(boolean) tells wheter the URL begins with http/https
			# 1) open the URL
			resource, urlCheck, webCheck = openURL(url)
			print('<<##--------------------- Report ------------------------##>>')
			print("The valid check for URL was: ", urlCheck)
			
			# 2) Create objects from the "resource"
			# If webCheck is True this was a URL on the web and
			# resource is populated.  If webCheck is False this
			# is a file on the computer, and we need to read lines.
			
			playlist = createPlaylist(resource, urlCheck, webCheck, url)
			
			## The visitor needs to decide what to do with the playlist, and main just 
			## needs to call the checks.  So, the check definition in Playlist() will
			## be different if the object is a Master or Variant.
			
			## Here is where the checks go in order:
				
			hCheck = HeaderCheck()
			playlist.accept(hCheck)
			
			vCheck = VersionCheck()
			playlist.accept(vCheck)
			
			vCompCheck = VerCompatCheck()
			playlist.accept(vCompCheck)
			
			mixCheck = MixTagsCheck()
			playlist.accept(mixCheck)
			
			streamInf = StreamInfCheck()
			playlist.accept(streamInf)
			
			iFrame = IFrameCheck()
			playlist.accept(iFrame)
			
			sessDataCheck = SessionDataCheck()
			playlist.accept(sessDataCheck)
			
			mediaMasterCheck = MediaMasterCheck()
			playlist.accept(mediaMasterCheck)
			
			targetDurCheck = TargetDurationCheck()
			playlist.accept(targetDurCheck)
			
			medSeqCheck = MediaSequenceCheck()
			playlist.accept(medSeqCheck)
			
			discontinuitySequenceCheck = DiscontinuitySequenceCheck()
			playlist.accept(discontinuitySequenceCheck)
			
			iFrameOnlyCheck = IFramesOnlyCheck()
			playlist.accept(iFrameOnlyCheck)

			
			## Here we need to print out the contents of the checks:
			#print('<<--------------->>')
			print('The playlist was a Master =', playlist.master)
			print('The given URL was =', playlist.suppliedURL)
			for line in range(0, len(playlist.checkResults)):
				print(playlist.checkResults[line])
			
			print('<<##--------------- End of Report ---------------##>>')
			print('')
			print('')
			
			## Now we are at the end of the loop.  Ask for another input
			## to continue the process, or the user can end.

			userResponse = input("Enter the next valid URL -or- end: ")
			
			if userResponse == 'end':
				execute = False
				logging.info("<<----------++ Leaving Command Line mode:")
			else:
				url = userResponse
				logging.info("++---------->> URL given: %s", userResponse)
			if playlist.master:
				playlist = clearMaster(playlist)
			else:
				playlist = clearVariant(playlist)
		#End of the while execute: block, and end of command line block
	
	## Case where the Format specified is wrong
	else:
		print("++-------->> File FORMAT:", sys.argv[1] + " should be either command or batch")
		sys.exit(-1)
#
# End of the main program function
####################################

if __name__ == "__main__":
	main(sys.argv[1:])

