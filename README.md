# Python-HLS
Http Live Streaming Validator written in Python3.6

There are many validators available out on the web (specifically from Apple etc.), but this is my version in Python.  It is an exercise in learning Python code for me, as the original version was written in Java as part of SWENG861 at Penn State (and a big thank you to Professor Rodini, Dr. LaPlante, and Dr. Sangwan for all of the knowledge they imparted).  I have implemented all of the tag definition checks as specified in the Apple Developers Guide (or, at least as interpreted by me).

Right now, the command line version is run like so:
   '>python HLSv1.py command filename/URL.m3u8'
   '>python HLSv1.py batch somefile.txt'  : where somefile is a list of playlist files or URLs
   
When the program runs a logging file named Hlsv1.log is created in the same directory which can be perused for debugging purposes.  The program will run in batch mode if "command" is substituted with "batch", and a valid text file with playlist URLs is given.  In successive iterations I will be changeing the report structure, and adding objects to make the output report in a nicer format.  If you have some ideas, or notice a bug feel free to contact me at jhuckestein@awardsolutions.com and I would be happy to entertain requests.

Release Road-Map:
   1) HLSv1.py - Basic program with all the pertinent checks : Completed
   2) HLSv2.py - Expaned checks and object attributes for determining line numbers for failures etc.: Completed (see HLSv2.one for class                    diagram)
   3) HLSv3.py - Development of a nicer appearance and more organized report structure: Currently under development
