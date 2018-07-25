# Python-HLS
Http Live Streaming Validator written in Python3.6

There are many validators available out on the web (specifically from Apple etc.), but this is my version in Python.  It is an exercise in learning Python code for me, as the original version was written in Java.  I have implemented all of the tag definition checks as specified in the Apple Developers Guide (or, at least as interpreted by me).

Right now, the command line version is all that is implemented which is run like so:
   '>python HLSv1.py command filename/URL.m3u8'
   
When the program runs a logging file named Hlsv1.log is created in the same directory which can be perused for debugging purposes.  In successive iterations I will be adding the loop for batch mode, and adding objects to make the output report in a nicer format.  If you have some ideas, or notice a bug feel free to contact me at jhuckestein@awardsolutions.com and I would be happy to entertain requests.
