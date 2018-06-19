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
		if self.content[0] == '#EXTM3U':
			check = True
		return check
		
	def masVersion(self, validator):
		# A playlist file must not contain more than one EXT-X-VERSION tag (ERROR)
		
		logging.info("++---------->> Beginning version check for Master object")
		multiple = False      #boolean result for check 1)
		versionInstance = 0   #integer for number of EXT-X-VERSION tags found
		version = 0           #integer for extracted version number
		
		for line in range(0, len(self.content)):
			if self.content[line].startswith('#EXT-X-VERSION:'):
				versionInstance += 1
				version = int(self.content[line].strip('#EXT-X-VERSION:'))
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
		
		for line in range(0, len(self.content)):
			if self.content[line].startswith('#EXT-X-VERSION:'):
				versionInstance += 1
				version = int(self.content[line].strip('#EXT-X-VERSION:'))
		if versionInstance > 1:
			multiple = True
		logging.info("++---------->> Number of EXT-X-VERSION tags found = %s", versionInstance)
		logging.info("++---------->> Version of Variant object = %s", version)
		logging.info("++---------->> Leaving version check for Variant object")
		return multiple, version
		
		
						 # Can't specify a string as it will be null, so lists were chosen
	content = []         # A list of the original content of the URL
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
	
	
class MasterPlaylist(Playlist):
	# Has a header that starts with #EXTM3U
	# Has a #EXT-X-STREAM-INF that has BANDWIDTH, RESOLUTION, & CODEC
	# Line after above is the URL.ts
	# Has a list of object references for each URL.ts media variant
	# They have to be able to create objects of VariantPlaylist
	
	variantList = []  #List of variant objects
	variantURLs = []  #List of URLs for each variant object


## This is where the visitors (check hierarchy) are defined

class Visitor:
    def __str__(self):
        return self.__class__.__name__
		
class Validator(Visitor): pass
class MasterValidator(Validator): pass
	
class VariantValidator(Validator): pass 
	
		
class headerCheck(Validator):   ## This check is universal to any playlist
	def visit(self, pList):
		result = pList.checkHeader(self)
		pList.checkResults.append("First line #EXTM3U= " + str(result))
		
class versionCheck(Validator):
	#This validator checks to see the number of EXT-X-VERSION tags, and extracts
	#the version number and assigns to the playlist.
	def visit(self, pList):
		if pList.master:
			test, ver = pList.masVersion(self)
			pList.playVersion = ver      #Attribute of the object to be used for compatibility
			if test:
				pList.checkResults.append('EXT-X-VERSION test: Failed / multiple tags')
			else:
				pList.checkResults.append('EXT-X-VERSION test: Passed')
		else:
			test, ver = pList.varVersion(self)
			pList.playVersion = ver      #Attribute of the object to be used for compatibility
			if test:
				pList.checkResults.append('EXT-X-VERSION test: Failed / multiple tags')
			else:
				pList.checkResults.append('EXT-X-VERSION test: Passed')

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
	# First test if the url has a valid extension .m3u8
	if url.endswith(".m3u8"):
			logging.info("++---------->> openURL Valid(m3u8) YES")
			valid = True
	else:
		logging.info("++---------->> openURL Valid(m3u8) NO")
		valid = False
	# If the given url starts with http:// then process as a web site
	web = False
	if url.startswith("http://") or url.startswith("https://"):
		try:
			response = requests.get(url)
			response.raise_for_status()
			output = response.text.encode('ascii', 'ignore')
			web = True
			logging.info("++---------->> openURL: %s", url)
			return output, valid, web
		except requests.exceptions.HTTPError as e:
			print ("Error: ", e)
			logging.info("++---------->> openURL Error: %s", e)
			sys.exit(1)
	# If the given url does not start with http:// then presumably the
	# url is a local file so we will open with filehandle
	else:
		try:
				fileHandle = open(url,'r')
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
	pList = MasterPlaylist()
	pList.master = True         
	for i in range(0, len(conList)):
			pList.content.append(conList[i]) #Initialize raw content
			if '.m3u8' in conList[i]:  
				pList.variantURLs.append(conList[i])  #Collect list of variants
				#Before creating the variant we must open a connection to 
				#the variant URL and retrieve contents.
				varRsc, validURL, web = openURL(conList[i])
				#Now if/else block for createPlaylist:
				if web == True:
					# Variant Resource can be loaded into an object, but must be decoded
					logging.info("++---------->> Web variant from createMaster:")
					varContents = varRsc.decode('utf-8')
					print("contents =", varContents)
					varContentList = list(varContents.splitlines())
					#Now we have the contents of the URL
					logging.info("++---------->> Created variant contentList of length: %s", len(varContentList))
				else:
					# Resource is the filehandle we got from openURL, and the lines can be read
					logging.info("++---------->> File variant from createMaster:")
					varContents = varRsc.read()
					varContentList = list(varContents.split("\n"))
					varRsc.close()
					logging.info("++---------->> Created contentList of length: %s", len(varContentList))
					print("contentList is: ", varContentList)
				
				#Now the variant object can be created and appended to the 
				#variantList in the MasterPlaylist.
				pList.variantList.append(createVariant(varContentList, conList[i]))
	pList.suppliedURL = str(uRL)     
	return pList
	


#
# End of createMaster
####################################

####################################
#
# This function creates VariantPlaylist objects
def createVariant(contenList, urL):
	varList = VariantPlaylist()
	varList.master = False    
	for i in range(0, len(contenList)):
			varList.content.append(contenList[i])
	varList.suppliedURL = str(urL)   
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
	
	if webFlag == True:
	# Resource can be loaded into an object, but must be decoded
		logging.info("++---------->> Entered createPlaylist for Web URL:")
		contents = rsrc.decode('utf-8')
		print("contents =", contents)
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
		print("contentList is: ", contentList)
		
	#Now the contentList is populated, and we need to create either a VariantPlaylist
	#or create a MasterPlaylist.  If we iterate through the contentList, and find a
	#.m3u8 extension, this would identify the playlist as a Master.  Otherwise, the
	#VariantPlaylist does not have any tag with .m3u8 in it.
	
	master = False
	for i in range(0, len(contentList)):
		if '.m3u8' in contentList[i]:
			master = True
		#print("contentList was ", str(i), ": ", contentList[i])
	logging.info("++------------>> The playlist object was test to be Master: %s", str(master))
	#print("Master test was: ", str(master))
	
	#Now we know whether the supplied resource was a Master or Variant playlist.  Next,
	#we create the object where a MasterPlaylist will create it's own VariantPlaylist(s).
	
	if master:
		playList = createMaster(contentList, URL)
	else:
		playList = createVariant(contentList, URL)
		
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

	print("++-------->> File Program:", sys.argv[0])
	print("++-------->> File FORMAT:", sys.argv[1])
	print("++-------->> File File/URL:", sys.argv[2])
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
			#urlCheck(boolean) tells whether the given URL ends with .m3u8
			#webCheck(boolean) tells wheter the URL begins with http/https
			# 1) open the URL
			resource, urlCheck, webCheck = openURL(url)
			#print(resource)
			print("The valid check for URL was: ", urlCheck)
			
			# 2) Create objects from the "resource"
			# If webCheck is True this was a URL on the web and
			# resource is populated.  If webCheck is False this
			# is a file on the computer, and we need to read lines.
			
			playlist = createPlaylist(resource, urlCheck, webCheck, url)
			
			#print out the contents of the newly created playlist for debugging
			for i in range(0, len(playlist.content)):
				print(str(i), " content =", playlist.content[i])
			
			
			## So, is this where I need to place a block which looks at whether
			## playlist is a master, and call various checks depending upon the
			## type of playlist that is encountered.
			
			## The visitor needs to decide what to do with the playlist, and main just 
			## needs to call the checks.  So, the check definition in Playlist() will
			## need to know what to do if the object is a Master or Variant.
			
			## Here is where the checks go in order:
				
			hCheck = headerCheck()
			playlist.accept(hCheck)
			
			vCheck = versionCheck()
			playlist.accept(vCheck)

			
			## Here we need to print out the contents of the checks:
			print('The playlist was a Master =', playlist.master)
			print('The given URL was =', playlist.suppliedURL)
			for line in range(0, len(playlist.checkResults)):
				print(playlist.checkResults[line])
			
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

