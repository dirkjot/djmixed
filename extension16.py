"""Helper routines for EXTENSION command"""

# History
# 12-Oct-2007 JKP Initial version
# 14-Nov-2007 Changed to handle Unicode mode
# 21-Feb-2008 Correct error msg for int, float out of range
# 27-Jun-2008  Add checkrequiredparams function
# 12-Jul -2008  Add processcmd function to handle general execution pattern
# 08-aug-2008 Eliminate dependence on spssaux module to improve script efficiency
# 12-aug-2008 Provide for optional VariableDict object in processcmd
# 26-dec-2008 floatex fix for comma decimal

__author__  =  'spss'
__version__ =  '1.3.3'
version = __version__


import spss
import inspect, sys


ok1600 = spss.GetDefaultPlugInVersion()[-3:] >= '160'

class Template(object):
	"""Define a syntax element

	kwd is the keyword being defined.  It will always be made upper case, since that is how SPSS delivers keywords.
	kwd should be '' for tokens passed from a subcommand with IsArbitrary=True..
	subc is the subcommand for the keyword.  If omitted, it defaults to the (one) anonymous subcommand.
	This class does not support repeating subcommands.
	ktype is the keyword type.  Keyword type is one of
	"bool" : true,false,yes,no
	If the keyword is declared as LeadingToken in the XML and treated as bool here, the presence or absense of the keyword
	  maps to True or False
	"str" : string or quoted literal with optional enumeration of valid choices.  Always converted to lower case.
	"int" : integer with optional range constraints
	"float" : float with optional range constraints
	"literal" : arbitrary string with no case conversion or validation
	"varname" : arbitrary, unvalidated variable name or syntactical equivalent (such as a dataset name)
	"existingvarlist" : list of variable names including support for TO and ALL.
	
	str, literal, varname, and existingvarlist are mapped to Unicode if SPSS is in Unicode mode; otherwise they are
	assumed to be code page.

	var is the Python variable name to receive the value.  If None, the lower-cased kwd value is used.  var should be
	unique across all the subcommands.  If there are duplicates, the last instance wins.  If kwd == '', var must be specified.
	vallist is the list of permitted values.  If omitted, all values of the proper type are legal.
	  string values are checked in upper case.  Literals are left as written.
	  For numbers, 0-2 values can be specified for any value, lower limit, upper limit.  To specify
	  only an upper limit, give a lower limit of None.
	islist is True if values is a list (multiples) (SPSS keywordList or VariableNameList or NumberList)
	  If islist, the var to receive the parsed values will get a list.
	  existingvarlist is a list of existing variable names.  It supports SPSS TO and ALL conventions.
	  """
	ktypes = ["bool", "str", "int", "float", "literal", "varname", "existingvarlist"]

	def __init__(self, kwd, subc='', var=None, ktype="str", islist=False, vallist=None):
		if not ktype in Template.ktypes:
			raise ValueError, "option type must be in " + " ".join(Template.ktypes)
		self.ktype = ktype
		self.kwd = kwd
		self.subc = subc
		if var is None:
			self.var = kwd.lower()
		else:
			self.var = var
		self.islist = islist
		if _isseq(vallist):
			self.vallist = [u(v) for v in vallist]
		else:
			self.vallist = [u(vallist)]
		if ktype == "bool" and vallist is None:
			self.vallist = ["true", "false", "yes", "no"]
		elif ktype in  ["int", "float"]:
			if ktype == "int":
				self.vallist=[-2**31+1, 2**31-1]
			else:
				self.vallist = [-1e308, 1e308]
			try:
				if len(vallist) == 1:
					self.vallist[0] = vallist[0]
				elif len(vallist) == 2:
					if not vallist[0] is None:
						self.vallist[0] = vallist[0]
					self.vallist[1] = vallist[1]
			except:
				pass   # if vallist is None, len() will raise an exception
	def parse(self, item):
		key, value = item.items()[0]
		if key == 'TOKENLIST':
			key = ''   #tokenlists are anonymous, i.e., they have no keyword
		if not _isseq(value):
			value = [value]   # SPSS will have screened out invalid lists
		value = [u(v) for v in value]
		kw = self.subcdict[subc][key]  # template for this keyword
		return key, value

class ExtExistingVarlist(Template):
	"""type existingvarlist"""

	def __init__(self, kwd, subc='', var=None, islist=True):
		super(ExtExistingVarlist, self).__init__(kwd=kwd, subc=subc,var=var, islist=islist)

	def parse(self, item):
		pass

class ExtBool(Template):
	"type boolean"

	def __init__(self, kwd, subc='', var=None, islist=False):
		super(ExtBool, self).__init__(kwd=kwd, subc=subc, var=var, islist=islist)
	def parse(self, item):
		key, value = super(ExtBool, self).parse(item)

def setnegativedefaults(choices, params):
	"""Add explicit negatives for omitted choices if any were explicitly included.

    choices is the sequence or set of choices to consider
    params is the parameter dictionary for the command."""

	choices = set(choices)
	p = set(params)
	if p.intersection(choices):    # something was selected
		for c in choices:
			params[c] = params.get(c, False)


class Syntax(object):
	"""Validate syntax according to template and build argument dictionary."""

	def __init__(self, templ):
		"""templ is a sequence of one or more Template objects."""

		# Syntax builds a dictionary of subcommands, where each entry is a parameter dictionary for the subcommand.
		
		self.unicodemode = ok1600 and spss.PyInvokeSpss.IsUTF8mode()
		if self.unicodemode:
			self.unistr = unicode
		else:
			self.unistr = str

		self.subcdict = {}
		for t in templ:
			if not t.subc in self.subcdict:
				self.subcdict[t.subc] = {}
			self.subcdict[t.subc][t.kwd] = t
		self.parsedparams = {}

	def parsecmd(self, cmd, vardict=None):
		"""Iterate over subcommands parsing each specification.

		cmd is the command specification passed to the module Run method via the EXTENSION definition.
		vardict is used if an existingvarlist type is included to expand and validate the variable names.  If not supplied,
		names are returned without validation."""

		for sc in cmd.keys():
			for p in cmd[sc]:   #cmd[sc] is a subcommand, which is a list of keywords and values
				self.parseitem(sc, p, vardict)

	def parseitem(self, subc, item, vardict=None):
		"""Add parsed item to call dictionary.  

		subc is the subcommand for the item 
		item is a dictionary containing user specification.

		subc and item will already have been basically checked by the SPSS EXTENSION parser, so we can take it from there.
		If an undefined subcommand or keyword occurs (which should not happen if the xml and Template specifications are consistent), 
		a dictionary exception will be raised.
		The parsedparams dictionary is intended to be passed to the implementation as **obj.parsedparams."""

		key, value = item.items()[0]
		if key == 'TOKENLIST':
			key = ''   #tokenlists are anonymous, i.e., they have no keyword
		#value = value[0]   # value could be a list
		if not _isseq(value):
			value = [value]   # SPSS will have screened out invalid lists
		value = [u(v) for v in value]
		try:
			kw = self.subcdict[subc][key]  # template for this keyword
		except KeyError, e:
			print "A keyword was used that is defined in the extension xml for this command but not in the extension module Syntax definition:", e
			raise
		if kw.ktype in ['bool', 'str']:
			value = [self.unistr(v).lower() for v in value]
			if not kw.vallist[0] is None:
				for v in value:
					if not v in kw.vallist:
						raise AttributeError, "Invalid value for keyword: " + key + ": " + v
			if kw.ktype == "str":
				self.parsedparams[kw.var] = getvalue(value, kw.islist)
			else:
				self.parsedparams[kw.var] = getvalue(value, kw.islist) in ["true", "yes", None]
		elif kw.ktype in ["varname", "literal"]:
			self.parsedparams[kw.var] = getvalue(value, kw.islist)
		elif kw.ktype in ["int", "float"]:
			if kw.ktype == "int":
				value = [int(v) for v in value]
			else:
				value = [float(v) for v in value]
			for v in value:
				if not (kw.vallist[0] <= v <= kw.vallist[1]):
					raise ValueError, "Value for keyword: %s is out of range" % kw.kwd
			self.parsedparams[kw.var] = getvalue(value, kw.islist)
		elif kw.ktype in ['existingvarlist']:
			self.parsedparams[kw.var] = getvarlist(value, kw.islist, vardict)

def getvalue(value, islist):
	"""Return value or first element.  If empty sequence, return None"""
	if islist:
		return value
	else:
		try:
			return value[0]
		except:
			return None

def getvarlist(value, islist, vardict):
	"""Return a validated and expanded variable list.

	value is the tokenlist to process.
	islist is True if the keyword accepts multiples
	vardict is used to expand and validate the names.  If None, no expansion or validation occurs"""

	if not islist and len(value) > 1:
		raise ValueError, "More than one variable specified where only one is allowed"
	if vardict is None:
		return value
	else:
		v = vardict.expand(value)
		if islist:
			return v
		else:
			return v[0]
		return 

def checkrequiredparams(implementingfunc, params, exclude=None):
	"""Check that all required parameters were supplied.  Raise exception if not
	
	implementingfunc is the function that will be called with the output of the parse.
	params is the parsed argument specification as returned by extension.Syntax.parsecmd
	exclude is an optional list of arguments to be ignored in this check.  Typically it would include self for a class."""
	
	args, junk, junk, deflts = inspect.getargspec(implementingfunc)
	if not exclude is None:
		for item in exclude:
			args.remove(item)
	args = set(args[: len(args) - len(deflts)])    # the required arguments
	omitted = args - set(params)
	if omitted:
		raise ValueError("The following required parameters were not supplied:\n" + ", ".join(omitted))
	
def processcmd(oobj, args, f, excludedargs=None, lastchancef = None, vardict=None):
	"""Parse arguments and execute implementation function.
	
	oobj is the Syntax object for the command.
	args is the Run arguments after applying
		args = args[args.keys()[0]]
	f is the function to call to execute the command
	Whatever f returns, if anything, is returned by this function.
	excludedargs is an optional list of arguments to be ignored when checking for required arguments.
	lastchancef is an optional function that will be called just before executing the command and passed
	the parsed parameters object
	Typically it would include self for a class.
	vardict, if supplied, is passed to the parser for variable validation"""
	
	
	try:
		oobj.parsecmd(args, vardict=vardict)
		# check for missing required parameters
		args, junk, junk, deflts = inspect.getargspec(f)
		if deflts is None:   #getargspec definition seems pretty dumb here
			deflts = tuple()
		if not excludedargs is None:
			for item in excludedargs:
				args.remove(item)
		args = set(args[: len(args) - len(deflts)])    # the required arguments
		omitted = [item for item in args if not item in oobj.parsedparams]
		if omitted:
			raise ValueError, "The following required parameters were not supplied:\n" + ", ".join(omitted)
		if not lastchancef is None:
			lastchancef(oobj.parsedparams)
		return f(**oobj.parsedparams)
	except:
		# Exception messages are printed here, but the exception is not propagated, and tracebacks are suppressed,
		# because as an Extension command, the Python handling should be suppressed.
		print "Error:", sys.exc_info()[1]
		sys.exc_clear()
		
def floatex(value, format=None):
	"""Return value as a float if possible after addressing format issues

    value is a (unicode) string that may have a locale decimal and other formatting decorations.
    raise exception if value cannot be converted.
	format is an optional format specification such as "#.#".  It is used to disambiguate values
	such as 1,234.  That could be either 1.234 or 1234 depending on whether comma is a
	decimal or a grouping symbol.  Without the format, it will be treated as the former.
    This function cannot handle date formats.  Such strings will cause an exception.
	A sysmis value "." will cause an exception."""

	try:
		return float(value)
	except:
		if format == "#.#":
			#  comma must be the decimal and  no other decorations may be present
			value = value.replace(",", ".")
			return float(value)
		# maybe a comma decimal or COMMA format
		lastdot = value.rfind(".")
		lastcomma = value.rfind(",")
		if lastcomma > lastdot:  # handles DOT format and F or E with comma decimal
			value = value.replace(".", "")
			value = value.replace(",", ".")
		elif lastdot > lastcomma:  # truly a dot decimal format
			value = value.replace(",", "")   # handles COMMA format	    
		v = value.replace(",", ".")
		try:
			return float(v)
		except:
			# this is getting annoying.  Maybe a decorated format.  "/" is included below
			# to ensure that conversion will fail for date formats

			v = "".join([c for c in value if c.isdigit() or c in ["-", ".", "+", "e","E", "/"]])
			return float(v)   # give up if this fails

# The following routines are copied from spssaux in order to avoid the need to import that entire module
def u(txt):
	"""Return txt as Unicode or unmodified according to the SPSS mode"""
	
	if not ok1600 or not isinstance(txt, str):
		return txt
	if spss.PyInvokeSpss.IsUTF8mode():
		if isinstance(txt, unicode):
			return txt
		else:
			return unicode(txt, "utf-8")
	else:
		return txt

def _isseq(obj):
	"""Return True if obj is a sequence, i.e., is iterable.
	
	Will be False if obj is a string, Unicode string, or basic data type"""
	
	# differs from operator.isSequenceType() in being False for a string
	
	if isinstance(obj, basestring):
		return False
	else:
		try:
			iter(obj)
		except:
			return False
		return True
