This is DJMIXED.  The main code lives here.  


_updated March 2015_

ARCHIVED CODE:  This repository is kept here for historical purposes only. 
The extension itself works with all SPSS versions that I currently have
access to (v19 to v22), but keeping the installers working with the many
SPSS versions that are currently around is simply too much work for the
limited number of users we have.

Google code is going to shut down in Summer 2015, so this source code will
move to my Github account: see https://github.com/dirkjot?tab=repositories


== Introduction ==

This is a python extension for SPSS to facilitate the use of mixed models. 
Mixed models are powerful, modern regression models that can handle multiple
random effects (random factors) in one model.  They are therefore a natural
solution to a common problem in the psychology of language
(psycholinguistics):  How to analyse data which has a random effect for
participants (subjects) and a random effect for items (words)?  

A [http://dx.doi.org/10.3758/s13428-011-0145-1 paper] on this extension has
been published in Behavioral Research Methods in Fall 2011.  Feel free to
ask me for an offprint.  Shy of that, just look at FilesRelatedToThePaper
which also contain a manual for the extension.  
 

For the truly curious: The files are under the Source tab, try the Trunk
directory and the Installation directory.  Some files provided here are part
of the SPSS plugin framework, these files are hard to find on the SPSS site
and released under the
[https://code.google.com/p/djmixed/source/browse/installation/SPSS%20Freeware%20License%20Agreement.pdf
SPSS-freeware-licence].

Dirk Janssen
University of Kent

== NEWS ==

*August 2011*:  I have abandoned the painful and pretty unworkable spss
*extension files (SPE) and wrote my own installer.  It was a ton of work but
*installation should now be a breeze.  Drawback for now:  It only works on
*SPSS 19.0.  *Release 19.3*

*August 2011*:  There was a small problem with the code, so that
*interactions were shown on the BY clause of the MIXED command.  SPSS
*doesn't like that.  It has now been fixed. 

*July 2010*: The paper has been accepted by Behavioral Research Methods.

*May 2010*: An improved version with extra features (release 49).

