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

##Begin package import section
import sys
import json
import logging
import requests



##End package import section

##Set up logging for the program
logging.basicConfig(filename='Hlsv1.log', level=logging.DEBUG)


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
		
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-VERSION:'):
				versionInstance += 1
				version = int(self.mContent[line].strip('#EXT-X-VERSION:'))
		logging.info("++---------->> Number of EXT-X-VERSION tags found = %s", versionInstance)
		logging.info("++---------->> Version of Master object = %s", version)
		logging.info("++---------->> Leaving version check for Master object")
		return multiple, version
				
		
	def varVersion(self, validator):
		# A playlist file must not contain more than one EXT-X-VERSION tag (ERROR)
		
		logging.info("++---------->> Beginning version check for Variant object")
		multiple = False      #Assumed false unless versionInstance > 1
		versionInstance = 0   #integer for number of EXT-X-VERSION tags found
		version = 0           #integer for extracted version number
		
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-VERSION:'):
				versionInstance += 1
				version = int(self.vContent[line].strip('#EXT-X-VERSION:'))
		if versionInstance > 1:
			multiple = True
		logging.info("++---------->> Number of EXT-X-VERSION tags found = %s", versionInstance)
		logging.info("++---------->> Version of Variant object = %s", version)
		logging.info("++---------->> Leaving version check for Variant object")
		return multiple, version
		
	def mCompVersion(self, validator):
		# 1) Must be 7+ if Master has SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA (ERROR)
		# 2) If 6+ PROGRAM-ID attribute for EXT-X-STREAM-INF and EXT-X-I-FRAME-STREAM-INF removed (WARNING)
		# 3) If 7+ EXT-X-ALLOW-CACHE removed
		
		logging.info("++------------------------------>> Entering mCompVersion")
		compService = True  #Validation status for 1) - SERVICE values for INSTREAM-ID
		compProgram = True  #Validation status for 2) - PROGRAM-ID attribute
		compCache = True    #Validation status for 3) - EXT-X-ALLOW-CACHE
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-MEDIA'):
				if 'INSTREAM-ID' and 'SERVICE' in self.mContent[line]:
					if self.playVersion < 7:
						compService = False
			elif self.mContent[line].startswith('#EXT-X-STREAM-INF'):
				if self.playVersion < 6 and 'PROGRAM-ID' in self.mContent[line]:
					compProgram = False
			elif self.mContent[line].startswith('#EXT-X-I-FRAME-STREAM-INF'):
				if self.playVersion < 6 and 'PROGRAM-ID' in self.mContent[line]:
					compProgram = False
			elif self.playVersion >= 7:
				if 'EXT-X-ALLOW-CACHE' in self.mContent[line]:
					compCache = False
		logging.info("++------------------------------>> Leaving mCompVersion")
		return compService, compProgram, compCache
	
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
		
		#Fist iterate through the list to find if certain tags exist
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-I-FRAMES-ONLY'):
				iFrames = True
		#Now iterate through the list and make our checks
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-KEY:IV'):
				check2 = False
			elif self.vContent[line].startswith('#EXTINF:'):
				tag = self.vContent[line].strip('#EXTINF:')
				if self.playVersion < 3 and '.' in tag:   #Decimals not allowed below version-3
					if tag.find('.') < 3:    #EXTINF:<duration>,<title> and title could have period
						check3 = False
			elif self.vContent[line].startswith('#EXT-X-BYTERANGE:') and self.playVersion < 4:
				check4 = False
			elif self.vContent[line].startswith('#EXT-X-I-FRAMES-ONLY') and self.playVersion < 4:
				check4 = False
			elif self.vContent[line].startswith('#EXT-X-MAP'):
				if iFrames:
					if self.playVersion < 5:
						check5 = False
				else:
					if self.playVersion < 6:
						check6 = False
			elif self.vContent[line].startswith('#EXT-X-ALLOW-CACHE') and self.playVersion >= 7:
				check7 = False
			logging.info("++------------------------------>> Leaving vCompVersion")
			return check2, check3, check4, check5, check6, check7
			
	def mMixCheck(self, validator):
	#This check determines if Master Playlists contain Media or Variant tags
		logging.info("++------------------------------>> Entering mMixCheck")
		mixedTags = False
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXTINF:') or self.mContent[line].startswith('#EXT-X-BYTERANGE:'):
				mixedTags = True
			elif self.mContent[line].startswith('#EXT-X-DISCONTINUITY:') or self.mContent[line].startswith('#EXT-X-KEY:'):
				mixedTags = True
			elif self.mContent[line].startswith('EXT-X-MAP:') or self.mContent[line].startswith('#EXT-X-PROGRAM-DATE-TIME:'):
				mixedTags = True
			elif self.mContent[line].startswith('#EXT-X-DATERANGE:') or self.mContent[line].startswith('#EXT-X-TARGETDURATION:'):
				mixedTags = True
			elif self.mContent[line].startswith('#EXT-X-MEDIA-SEQUENCE:') or self.mContent[line].startswith('#EXT-X-ENDLIST:'):
				mixedTags = True
			elif self.mContent[line].startswith('#EXT-X-PLAYLIST-TYPE:') or self.mContent[line].startswith('#EXT-X-I-FRAMES-ONLY:'):
				mixedTags = True
			elif self.mContent[line].startswith('#EXT-X-DISCONTINUITY-SEQUENCE:'):
				mixedTags = True
		return mixedTags
		logging.info("++------------------------------>> Exiting  mMixCheck")
			
	def vMixCheck(self, validator):
	#This check determines if Variant/Media playlists contain Master tags
		logging.info("++------------------------------>> Entering vMixCheck")
		mixedTags = False
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-MEDIA:') or self.vContent[line].startswith('#EXT-X-STREAM-INF:'):
				mixedTags = True
			if self.vContent[line].startswith('#EXT-X-I-FRAME-STREAM-INF:') or self.vContent[line].startswith('#EXT-X-SESSION-DATA:'):
				mixedTags = True
			if self.vContent[line].startswith('#EXT-X-SESSION-KEY:'):
				mixedTags = True
		return mixedTags
		logging.info("++------------------------------>> Exiting  vMixCheck")
		
	def mStreamInf(self, validator):
	#This check looks to see if the EXT-X-STREAM-INF tag in a master playlist is
	#followed by a URI line, and if the BANDWIDTH attribute is present.
		logging.info("++----------------------------->> Entering mStreamInf")
		nextLine = False  #Will be set true if next line does not contain .m3u8
		bwAttr = True     #Will be set to false if no ATTRIBUTE in tag
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-STREAM-INF:'):
				if self.mContent[line].count('BANDWIDTH') < 1:
					bwAttr = False
				if  not self.mContent[line + 1].endswith('.m3u8'):
					nextLine = True
		logging.info("++----------------------------->> Exiting mStreamInf")
		return nextLine, bwAttr
		
	def vStreamInf(self, validator):
	#This check looks to see if the EXT-X-STREAM-INF tag is present in a variant file.
	#This is a violation, and an ERROR.
		logging.info("++----------------------------->> Entering vStreamInf")
		checkV = False
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-STREAM-INF:'):
				checkV = True
		logging.info("++----------------------------->> Exiting vStreamInf")
		return checkV
	
	def mIFrame(self, validator):
	#This check applies to Master Playlists and if this tag is used it must have
	#a BANDWIDTH and URI attribute
		logging.info("++----------------------------->> Entering mIFrame")
		bwAttr = True
		uriAttr = True
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-I-FRAME-STREAM-INF:'):
				if self.mContent[line].count('BANDWIDTH') < 1:
					bwAttr = False
				if self.mContent[line].count('URI') < 1:
					uriAttr = False
		logging.info("<<-----------------------------++ Exiting mIFrame")
		return bwAttr, uriAttr
		
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
		possibleMults = [] #list of possible multiples
		dIDList = []       #Used to keep track of DATA-ID values for multiple tags
		langList = []      #Used to keep track of LANGUAGE values for multiples
		iterList = []      #Working list used for parsing possible multiple tags
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-SESSION-DATA'):
				#If you have the tag DATA-ID must be present
				if not 'DATA-ID' in self.mContent[line]:
					dCheck = True
				#If you have a VALUE it must be json formatted
				if 'VALUE' in self.mContent[line]:
					if 'URI' in self.mContent[line]:
						uri = True
				if 'URI' in self.mContent[line]:
					if not '.json' in self.mContent[line]:
						json = True
				#VALUE not found, so URI must be present
				elif not 'URI' in self.mContent[line]:
					missing = True
				tagList.append(self.mContent[line])
		if len(tagList) > 0:  #If no tags found not an issue
			logging.info("++------------------->> mSessionData possible multiples")
			#Filter out all of the possible multiple DATA-ID:LANGUAGE tags
			for l in range(0, len(tagList)):
				if 'DATA-ID' in tagList[l] and 'LANGUAGE' in tagList[l]:
					possibleMults.append(tagList[l])
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
						
			logging.info("<<-------------------++ mSessionData possible multiples")
		logging.info("<<-----------------------------+++ Exiting mSessionData")
		return dCheck, json, uri, multiples
		
	
	#def mSessionKey(self, validator):
		#A Master Playlist MUST NOT contain more than one EXT-X-SESSION-KEY tag with the same
		#METHOD, URI, IV, KEYFORMAT, and KEYFORMATVERSIONS attribute values.  No example in spec.
		
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
		for line in range(0, len(self.mContent)):
			if self.mContent[line].startswith('#EXT-X-INDEPENDENT-SEGMENTS'):
				segCount += 1
			elif self.mContent[line].startswith('#EXT-X-START'):
				startCount += 1
				if 'TIME-OFFSET' not in self.mContent[line]:
					tOffset = True
		if segCount > 1:
			segments = True
		if startCount > 1:
			start = True
		logging.info("<<------------------------------++ Exiting mMediaMaster")
		return segments, start, tOffset
		
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
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-INDEPENDENT-SEGMENTS'):
				segCount += 1
			elif self.vContent[line].startswith('#EXT-X-START'):
				startCount += 1
				if 'TIME-OFFSET' not in self.vContent[line]:
					tOffset = True
		if segCount > 1:
			segments = True
		if startCount > 1:
			start = True
		logging.info("<<------------------------------++ Exiting vMediaMaster")
		return segments, start, tOffset
		
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
		for line in range(0, len(self.vContent)):
			if self.vContent[line].startswith('#EXT-X-TARGETDURATION'):
				check = True
				count = Count + 1
				maxDuration = float(self.vContent[line].strip('#EXT-X-TARGETDURATION:'))
				if count > 1:
					multTag = True
			if self.vContent[line].startswith('#EXTINF:'):
				duration = float(self.vContent[line].strip('#EXTINF:'))
				if duration > maxDuration:
					durationCheck = True
		logging.info("<<------------------------------++ Exiting vTargetDuration")
		return check, multTag, durationCheck
	
	
	
						 # Can't specify a string as it will be null, so lists could be used
	#suppliedURL = []	 # The URL supplied by the command line or batch file
	#master = Bool 		 # True if a Master playlist, False if variant
	#playVersion         # Integer used to store playlist version, 0 if not used
	checkResults = []	 # Used to store the contents of check results

class VariantPlaylist(Playlist):
	# Has a list of URLs to media segments (or locally defined) that end in ".ts"
	# Has #EXT-X-PLAYLIST-TYPE the playlist type (LIVE, EVENT, VOD)
	# Has a header that starts with #EXTM3U
	# Has #EXT-X-STREAM-INF tag to indicate next URL identifies a playlist file
	# Has #EXT-MEDIA-SEQUENCE which tells the first URL.ts that appears in the file
	# Has #EXT-X-TARGETDURATION which specifies the maximum media file duration
	# Has #EXT-X-VERSION which is the compatibility version of the playlist file
	# Has #EXT-X-ENDLIST in VOD and possibly in EVENT
	type = []  # EVENT,VOD,LIVE
	vContent = []     #List of content from the original URL
	
	
class MasterPlaylist(Playlist):
	# Has a header that starts with #EXTM3U
	# Has a #EXT-X-STREAM-INF that has BANDWIDTH, RESOLUTION, & CODEC
	# Line after above is the URL.ts
	# Has a list of object references for each URL.ts media variant
	# They have to be able to create objects of VariantPlaylist
	
	variantList = []  #List of variant objects
	variantURLs = []  #List of URLs for each variant object
	mContent = []     #List of content from the original URL


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
			else:
				pList.checkResults.append("FAILED: First line starts #EXTM3U")
			pList.checkResults.append('')
			pList.checkResults.append("<<-----End of Header Check----->>")
			pList.checkResults.append('')
			#Now we need to call HeaderCheck for all the Variant objects in pList.variantList
			for variant in range(0, len(pList.variantList)):
				#for i in range(0, len(pList.variantList[variant].vContent)):
					#print(pList.variantList[variant].vContent[i])
				vHCheck = HeaderCheck()
				nr = pList.variantList[variant].accept(vHCheck)
				#print('Result of variant check = ', nr)
		else:
			#In the event that a Master Playlist calls the for loop above, 
			logging.info("++--------------->> HeaderCheck Variant Object")
			pList.checkResults.append("<<-----Begin Media Header Check----->>")
			pList.checkResults.append('')
			pList.checkResults.append('Variant Playlist =' + pList.suppliedURL)
			result = pList.checkHeader(self)
			if result:
				pList.checkResults.append("PASSED: First line starts #EXTM3U")
			else:
				pList.checkResults.append("FAILED: First line starts #EXTM3U")
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
		if pList.master:
			test, ver = pList.masVersion(self)
			pList.playVersion = ver      #Attribute of the object to be used for compatibility
			if test:
				pList.checkResults.append('Master Playlist =' + pList.suppliedURL)
				pList.checkResults.append('EXT-X-VERSION test: Failed / multiple tags')
				logging.info("++---------->> HeaderCheck Master Validation FAILED")
			else:
				pList.checkResults.append('Master Playlist =' + pList.suppliedURL)
				pList.checkResults.append('PASSED: EXT-X-VERSION test')
				pList.checkResults.append('VERSION = ' + str(ver))
				logging.info("++---------->> HeaderCheck Master Validation PASSED: " + str(pList.playVersion))
			#Now, the version of the variantList contents need to be checked
			for variant in range(0, len(pList.variantList)):
				verCheck = VersionCheck()
				pList.variantList[variant].accept(verCheck)
		else:
			test, ver = pList.varVersion(self)
			pList.playVersion = ver      #Attribute of the object to be used for compatibility
			if test:
				pList.checkResults.append('Variant Playlist =' + pList.suppliedURL)
				pList.checkResults.append('EXT-X-VERSION test: Failed / multiple tags')
				logging.info("++---------->> HeaderCheck Variant Validation FAILED")
			else:
				pList.checkResults.append('Variant Playlist =' + pList.suppliedURL)
				pList.checkResults.append('EXT-X-VERSION test: Passed')
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
		if pList.master:
			compatService, compatProgram, compatCache = pList.mCompVersion(self)
			logging.info("++---------->> Master Version Compatibility Check")
			logging.info("++---------->> Master compatService = %s", compatService)
			logging.info("++---------->> Master compatProgram = %s", compatProgram)
			logging.info("++---------->> Master compatCache = %s", compatCache)
			pList.checkResults.append('Master Version Compatibility Checks for ' + pList.suppliedURL)
			if compatService:
				pList.checkResults.append('PASSED: SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA')
			else:
				pList.checkResults.append('ERROR: Version must be 7+ for SERVICE values for INSTREAM-ID attribute of EXT-X-MEDIA')
			if compatProgram:
				pList.checkResults.append('PASSED: PROGRAM-ID attribute for EXT-X-STREAM-INF removed')
				pList.checkResults.append('PASSED: PROGRAM-ID attribute for EXT-X-I-FRAME-STREAM-INF removed')
			else:
				pList.checkResults.append('WARNING: Version 6+ PROGRAM-ID attribute for EXT-X-STREAM-INF and EXT-X-I-FRAME-STREAM-INF are removed')
			if compatCache:
				pList.checkResults.append('PASSED: Version 7+ EXT-X-ALLOW-CACHE removed')
			else:
				pList.checkResults.append('ERROR: Version 7+ EXT-X-ALLOW-CACHE is removed')
			#Now, the contents of the variantList need to be version compatibility checked
			for variant in range(0, len(pList.variantList)):
				versCheck = VerCompatCheck()
				pList.variantList[variant].accept(versCheck)
		else:   #Case where we have a Variant Playlist
			compCkV2, compCkV3, compCkV4, compCkV5, compCkV6, compCkV7 = pList.vCompVersion(self)
			logging.info("++---------->> Variant Version Compatibility Check")
			logging.info("++---------->> Variant compCkV2 = %s", compCkV2)
			logging.info("++---------->> Variant compCkV3 = %s", compCkV3)
			logging.info("++---------->> Variant compCkV4 = %s", compCkV4)
			logging.info("++---------->> Variant compCkV5 = %s", compCkV5)
			logging.info("++---------->> Variant compCkV6 = %s", compCkV6)
			logging.info("++---------->> Variant compCkV7 = %s", compCkV7)
			pList.checkResults.append('Variant Version Compatibility Checks for ' + pList.suppliedURL)
			if compCkV2:
				pList.checkResults.append('PASSED: Version 2+ if EXT-X-KEY:IV tag')
			else:
				pList.checkResults.append('ERROR: Must be 2+ if IV attribute of EXT-X-KEY:IV tag')
			if compCkV3:
				pList.checkResults.append('PASSED: Version 3+ if floating point EXTINF values')
			else:
				pList.checkResults.append('ERROR: Must be 3+ if floating point EXTINF values')
			if compCkV4:
				pList.checkResults.append('PASSED: Version 4+ EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags')
			else:
				pList.checkResults.append('ERROR: Version 4+ using EXT-X-BYTERANGE or EXT-X-I-FRAMES-ONLY tags')
			if compCkV5:
				pList.checkResults.append('PASSED: Version 5+ using EXT-X-MAP')
			else:
				pList.checkResults.append('ERROR: Version 5+ using EXT-X-MAP')
			if compCkV6:
				pList.checkResults.append('PASSED: Version 6 ->EXT-X-MAP using EXT-X-I-FRAMES-ONLY')
			else:
				pList.checkResults.append('ERROR: Version 6 ->EXT-X-MAP using EXT-X-I-FRAMES-ONLY')
			if compCkV7:
				pList.checkResults.append('PASSED: Version 7+ EXT-X-ALLOW-CACHE removed')
			else:
				pList.checkResults.append('ERROR: Version 7+ EXT-X-ALLOW-CACHE removed')
		pList.checkResults.append('')
		pList.checkResults.append('<<-----End of Compatibility Checks----->>')
		pList.checkResults.append('')
		
class MixTagsCheck(Validator):
	#This Validator checks to see if Variant/Media tags are in a Master Playlist and vice versa
	def visit(self, pList):
		logging.info("++------------------------->> Mixed Tag Validation")
		pList.checkResults.append('<<-----Mixed Tags Checks----->>')
		pList.checkResults.append('')
		if pList.master:
			test = pList.mMixCheck(self)
			if test:
				pList.checkResults.append('<<----- FAILED: Master Playlist contains Media/Variant tags ')
			else:
				pList.checkResults.append('<<----- PASSED: Master Playlist only contains Master tags ')
		else:
			test = pList.vMixCheck(self)
			if test:
				pList.checkResults.append('<<----- FAILED: Media/Variant Playlist contains Master tags ')
			else:
				pList.checkResults.append('<<----- PASSED: Media/Variant only contains Media/Variant tags ')
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
		if pList.master:
			resultLine, resultBW = pList.mStreamInf(self)
			if resultLine:
				pList.checkResults.append('<<----- FAILED: Master> EXT-X-STREAM-INF tag not followed by URI')
			else:
				pList.checkResults.append('<<----- PASSED: EXT-X-STREAM-INF tags followed by URI')
			if resultBW:
				pList.checkResults.append('<<----- PASSED: BANDWIDTH attribute present in tag')
			else:
				pList.checkResults.append('<<----- FAILED: BANDWIDTH attribute missing in tag')
		else:
			resultTag = pList.vStreamInf(self)
			if resultTag:
				pList.checkResults.append('<<----- FAILED: Variant> contains EXT-X-STREAM-INF tag')
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
		if pList.master:
			bWidth, uri = pList.mIFrame(self)
			if not bWidth:
				pList.checkResults.append('<<-----FAILED: BANDWIDTH attribute missing in tag')
			if not uri:
				pList.checkResults.append('<<-----FAILED: URI attribute missing')
			if bWidth and uri:
				pList.checkResults.append('<<-----PASSED: BANDWIDTH and URI tags present')
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
		if pList.master:
			idCheck, jsonCk, uriCk, multCk = pList.mSessionData(self)
			if idCheck:
				pList.checkResults.append('<<-----FAILED: EXT-X-SESSION-DATA tag missing DATA-ID attribute')
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-SESSION-DATA::DATA-ID check')
			if jsonCk:
				pList.checkResults.append('<<-----FAILED: URI attribute not JSON formatted')
			else:
				pList.checkResults.append('<<-----PASSED: JSON formatting check')
			if uriCk:
				pList.checkResults.append('<<-----FAILED: TAG may NOT have VALUE and URI attribute')
			else:
				pList.checkResults.append('<<-----PASSED: VALUE/URI check')
			if multCk:
				pList.checkResults.append('<<-----FAILED: Multiple DATA-ID attributes with same LANGUAGE')
			else:
				pList.checkResults.append('<<-----PASSED: Multiple DATA-ID/LANGUAGE check') 
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
		if pList.master:
			segTag, startTag, timeTag = pList.mMediaMaster(self)
			pList.checkResults.append('<<----- Master Playlist: ' + pList.suppliedURL)
			if segTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-INDEPENDENT-SEGMENTS tags found')
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-INDEPENDENT-SEGMENTS check')
			if startTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-START tags found')
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START check')
			if timeTag:
				pList.checkResults.append('<<-----FAILED: EXT-X-START:TIME-OFFSET attribute missing')
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START:TIME-OFFSET check')
			for variant in range(0, len(pList.variantList)):
				medMasCheck = MediaMasterCheck()
				pList.variantList[variant].accept(medMasCheck)
		else:
			segTag, startTag, timeTag = pList.vMediaMaster(self)
			pList.checkResults.append('<<----- Variant Playlist: ' + pList.suppliedURL)
			if segTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-INDEPENDENT-SEGMENTS tags found in variant')
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-INDEPENDENT-SEGMENTS check')
			if startTag:
				pList.checkResults.append('<<-----FAILED: Multiple EXT-X-START tags found in variant')
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START check')
			if timeTag:
				pList.checkResults.append('<<-----FAILED: EXT-X-START:TIME-OFFSET attribute missing in variant')
			else:
				pList.checkResults.append('<<-----PASSED: EXT-X-START:TIME-OFFSET check')
		pList.checkResults.append('')
		pList.checkResults.append('<<-----Media/Master (Joint) Tag Validation----->>')
		pList.checkResults.append('')
		logging.info("<<-------------------------++ EXT-X-SESSION-DATA Tag Validation")
	
	
	

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
			fileHandle = open(url,'r')
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
	
	#Note: eventually I will need to add other attributes
	#regarding Variant playlists etc.


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

