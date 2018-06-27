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
			
		
			
	
						 # Can't specify a string as it will be null, so lists were chosen
	#content = []         # A list of the original content of the URL
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
	vContent = []
	
	
class MasterPlaylist(Playlist):
	# Has a header that starts with #EXTM3U
	# Has a #EXT-X-STREAM-INF that has BANDWIDTH, RESOLUTION, & CODEC
	# Line after above is the URL.ts
	# Has a list of object references for each URL.ts media variant
	# They have to be able to create objects of VariantPlaylist
	
	variantList = []  #List of variant objects
	variantURLs = []  #List of URLs for each variant object
	mContent = []


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

####################################
#
# This class is used to create a validation report, and contains master results.
# class MasterValidationReport():
	
	# ## Mapping schema to the dictionary:
	# #givenURL =                 # Applies to every entry
	# #Header =                   # #EXTM3U on Master first line (ERROR)
	# #properStreamBW = 	   	  # Master: #EXT-X-STREAM-INF has BANDWIDTH (ERROR)
	# #properStreamRES =          # Master: #EXT-X-STREAM-INF has RESOLUTION (WARNING)
	# #properStreamCOD =          # Master: #EXT-X-STREAM-INF has CODECS (WARNING)
	# #properTSformat =           # Master: /URL.ts follows #EXT-X-STREAM-INF (ERROR)
	# #properEnd =                # Master: /URL.ts end in .m3u8 (contains due to format variations:ERROR) 
	
	# ## Because strings are immutable, a dictionary data structure was chosen with the
	# ## keys defined above
	# dict = {}.fromkeys(['givenURL', 'Header', 'properStreamBW', 'properStreamRES' \
	              # 'properStreamCOD', 'properTSformat', 'properEnd'])
	
	# errorLines = []            # Master: Lines that have errors
	# variantList = []           # Master: List of variants in file
	# variantReportList = []     # Master: List of variant validation reports
	# masterContents = []        # Master list of raw content

#
# End of ValidationReport
####################################


####################################
#
# This class is used to create a validation report, and contains variant results
# class VariantValidationReport():
	
	# ## Mapping schema to the dictionary:
	# # givenURL =                  # Applies to every playlist
	# # type =                      # Variant: #EXT-X-PLAYLIST-TYPE: EVENT,VOD,LIVE (WARNING)
	# # Header =                    # #EXTM3U on Variant first line (ERROR)
	# # properTSformat =            # Variant: /URL.ts follows #EXT-X-STREAM-INF (ERROR)
	# # properTsEnd =               # Variant: URL ends in .ts (contains due to format variations : ERROR))
	# # properSequence =            # Variant: Has #EXT-MEDIA-SEQUENCE (ERROR)
	# # properTarget =              # Variant: Has #EXT-X-TARGETDURATION (ERROR)
	# # properVersion =             # Variant: Has #EXT-X-VERSION (WARNING)
	# # properENDList =             # Variant: Has #EXT-X-ENDLIST in VOD (ERROR)
	
	# ## Because strings are immutable, a dictionary data structure was chosen with the
	# ## keys defined above
	# dict = {}.fromkeys(['givenURL', 'type', 'Header', 'properTSformat', 'properTsEnd', \
	               # 'properSequence', 'properTarget', 'properVersion', 'properENDList'])
	
	# variantContents = []        # Variant list of raw content
	
	
#
# End of class VariantValidationReport
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

			
			## Here we need to print out the contents of the checks:
			#print('<<--------------->>')
			print('The playlist was a Master =', playlist.master)
			print('The given URL was =', playlist.suppliedURL)
			for line in range(0, len(playlist.checkResults)):
				print(playlist.checkResults[line])
			# This print block is not needed, because the CheckHeader is validating the
			# variants correctly, but saving the results to the Master.checkResults[] -
			# though I am not sure why.  I suspect it has something to do with visitor pattern.
			# if playlist.master:
				# for variant in range(0, len(playlist.variantList)):
					# for l in range(0, len(variant.checkResults)):
						# print(variant.checkResults[l])
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

