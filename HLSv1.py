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
		except sys.OSError as e:
				print("Error: ", e)
				logging.info("++---------->> openURL OSError: %s", e)
				sys.exit(1)

#
# End of openURL
####################################

####################################
#
# This function is used to create Playlist Objects.  A MasterPlaylist
# will / can contain VariantPlaylist(s), but a VariantPlaylist will
# only have media files listed.  Both are subclasses of Playlist.
# This function creates both types.
#
def createPlaylist(rsrc, urlFlag, webFlag):
	if webFlag == True:
	# Resource can be loaded into an object
		logging.info("++---------->> Entered createPlaylist for Web URL:")
		#print("++-------->> Headers for the URL:  ", rsrc.headers)
		#print("++-------->> Encoding for the URL:  ", rsrc.encoding)
		#print("++-------->> Text for the URL:  ", rsrc.text)
		#print("++-------->> Status code for the URL:  ", rsrc.status_code)
		#print("++-------->> Content for the URL:  ", rsrc.content)
		# I suspect that these resource fields have not been populated
		# because I am downloading a .m3u8 file instead of an actual web
		# page.  This comes across as raw text and will probably need to 
		# be parsed or something.
		
		#The below works and creates a good file.  So, maybe retrieve
		#the file from the web, and then create the object where all
		#objects would be created from disk?
		fileHandle = open('OutputResource.txt','w')
		fileHandle.write(rsrc.decode('utf-8'))
		fileHandle.close()
		
	else:
	# Resource is the filehandle
		logging.info("++---------->> Entered createPlaylist for File URL:")
		


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
			# 1) open the URL
			resource, urlCheck, webCheck = openURL(url)
			print(resource)
			print("The valid check for URL was: ", urlCheck)
			
			# 2) Create objects from the "resource"
			# If webCheck is True this was a URL on the web and
			# resource is populated.  If webCheck is False this
			# is a file on the computer, and we need to read lines.
			
			playlist = createPlaylist(resource, urlCheck, webCheck)
				
			
			
			
			
			
			
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

