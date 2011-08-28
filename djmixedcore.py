# djmixed.py,  dirk p. janssen spring 2009
# $Id$
#
# windows users: either install this in c:\Python25\Lib\site-packages
# or set PYTHONPATH to the directory where this lives.



# 
# From Idle:  import sys; sys.path.append(r'c:\\flash2\\schrijf\\twicerandom\\djmixed'); import djmixed

# xpath references:
# http://www.zvon.org/xxl/XPathTutorial/General/examples.html
# http://www.w3.org/TR/xpath
# http://en.wikipedia.org/wiki/XPath_1.0
# name() is not @name,  /BBB  =^=  /*[name()='BBB']



# LONG TERM ADDITIONS/WISHES
# - the program should check whether numeric predictors are used, as string preds are possible in MIXED but not
#   supported here (yet)
# - unify treatment of spss errors and warnings
# - check equality of residual variances with a levene or so.
# - interaction plots?
# 


# TODO check whether to use updated versions of extension for later spss versions,
# or shall i simply not bother?

import spss, spssaux, extension16
import djstats
import textwrap
import random, re, os

__author__ = "dirk p. janssen"
__version__ = "$Id$: spam 41c 29Aug11 spam eggs ham".split()
__version__ = "Revision: %s at %s" % (__version__[2], __version__[3]) 
print """Importing DJMIXED by Dirk P. Janssen, %s """ % __version__
print """Reading python files from """, os.path.abspath(__file__)


# globals
modelnumber = 1
currentmodel = None
# each model has an OMS handle, which is stored in this set
modelhandles = set()  
pluginversion = spss.GetDefaultPlugInVersion()


# developer settings
DEBUG = True
DEBUG = False


class DjmixedFatal(Exception):
  pass


def longstring(paragraph, joiner=' '):
  """Returns the text from paragraph (typically the product of a
  triple-quote) and reformats it into one long string, removing
  newlines, indentation spacing and trailing spaces"""
  return joiner.join(map(lambda x: x.strip(), paragraph.split('\n')))


def xpastring(paragraph):
  """no spaces whatsoever"""
  return longstring(paragraph, '')


def blockstring(paragraph, width=75):
  """complete reformat the paragraph to have separated lines of only
  'width' characters."""
  text = longstring(paragraph)
  return textwrap.fill(text, width)


def cmdsyntax(paragraph):
  """convert a block quoted (indented) spss command to unindented, keeping the lines"""
  return longstring(paragraph, '\n')


#  this should wrap for spss 16, but not for 17:
if pluginversion.startswith('spss16'):
  def footnote(paragraph):
    return blockstring(paragraph)
else:  
  def footnote(paragraph):
    return longstring(paragraph)


class Bunch(object):
  """Use an object as a collection of stuff, with the additional
  luxury of creating it from the named arguments given to init"""
  def __init__(self, **kwds):
    self.__dict__.update(kwds)
    


def transpose(lists):
  """transpose a list of lists, from the cookbook online """
  # this does nice magic with splices:
  # *lists:  a map with multiple arguments takes one item from each
  #   of the argument lists each time
  # *row:  given multiple argument lists, a lambda x,y,z is expected, with
  #   as many parameters as there are lists.  but lambda =^= def, so *row works
  # list(row): row is already a list but we require a list of lists
  # 
  return map(lambda *row: list(row), *lists)


def mysubmit(spsscmd, silent=True):
  if silent:
    try:
      spss.SetOutput("off")
      ##  This doesn't work when called from SPSS, but is useful for unittests
      spss.Submit(spsscmd)
    finally:
      spss.SetOutput("on")
  else:
    spss.Submit(spsscmd)
    

# this should be joined with the above, but not sure of the implications right now
def silentsubmit(spsscmd):
  try:
    error = spss.Submit(cmdsyntax("""
    OMS  
      /DESTINATION  format=oxml xmlworkspace='silent' viewer=no
      /TAG='silent' .
    %s 
    OMSEND tag='silent'. """ % spsscmd))
  except spss.errMsg.SpssError, v:
    error = ('SpssError', v)
  return error
               



def startmodel(name, message=True, output='SPLIT'):
  """Start the analysis of a model named 'name'

  Contrary to what the user may think, this actually only
  starts a OMS output block with certain output copied to OXML, and
  output stored under xmlworkspace 'name'."""
  global currentmodel, modelhandles
  
  if name is None or name=='':
    raise DjmixedFatal('Name argument mandatory for startmodel')
  if currentmodel is not None:
    print "Startmodel triggered Stopmodel for '%s'" % currentmodel
    stopmodel(currentmodel)
  if name in modelhandles:
      """remove previous output under same name"""
      spss.DeleteXPathHandle(name)
      modelhandles.remove(name)
      print "Removed old model by this name"

  if message or output=='split':
    spss.StartProcedure('DJMIXED.StartModel')
    #print "Starting model '%s'" % name
    spss.TextBlock("StartModel", "Starting model '%s'" % name ) 
    spss.EndProcedure()

  # Add viewer=NO to /dest line to surpress normal output
  # Simply ignore the seemingly required spss command select (as in
  # 'select tables' here, which is the way to get everything

  viewer = 'no' if output.lower() == 'none' else 'yes'
  # DONE:  remove the /IF from this so we capture actually everything
  # certainly make the viewer always yes when debugging, for which we need a flag.
  #   OMS /IF commands='Mixed' 
  cmd = cmdsyntax(r"""
  OMS
      /DESTINATION  format=oxml xmlworkspace='%s' viewer=%s
      /TAG='%s' """ % (name, viewer, name) )
  spss.Submit(cmd)
  currentmodel = name
  modelhandles.add(name)
  

def stopmodel(name=None, message=True, modelerror=None):
  # check for error code like in spssaux
  """Stop the analysis of a model, with optional model name

  This ends the OMS output block.  If 'message' is False, no written
  feedback is produced.  If 'modelerror' is set, complaints about an
  error with the model are generated (regardless of 'message').  If
  'modelerror' is None, the GetLastErrorLevel is checked and a
  carefully phrased note produced if a warning was logged. """
  global currentmodel
  notchecked = list().append("not checked")
  if name is None or name=='' or name=='*':
    name = currentmodel
  elif name !=currentmodel:
    spss.Submit(r"""omsend.""" % name)
    raise DjmixedFatal('Name argument of stopmodel does not match last startmodel')
  
  if modelerror is None:
    errorlevel = spss.GetLastErrorLevel()
  else:
    errorlevel = notchecked 
  spss.Submit(r"""omsend tag='%s'.""" % name)

  xpa = xpastring("""//command[@command='Mixed']/@text""")
  analyses = spss.EvaluateXPath(name, '/outputTree', xpa)
  outputweird = ""
  if len(analyses)==0:
    outputweird = blockstring("""No MIXED output found: Did your commands succeed?""")
  elif len(analyses)>1:
    outputweird = blockstring("""Multiple MIXED outputs found: Please review your syntax""")


  if message or modelerror  or errorlevel >= 2 or outputweird:
    spss.StartProcedure('DJMIXED.StopModel')
    #print "Ending model '%s'" % name
    if modelerror:
      # modelerror was set by a catch after a submit, so this is serious
      spss.TextBlock("Error", blockstring("""An ERROR
      was issued by the mixed model syntax.  You should carefully
      inspect the output to determine whether the model is valid.
      It is possible, but unlikely, that SPSS made a problem of a harmless matter.""") )
    if errorlevel == 2:
      # MAYBE filter out the covtype changed to ID warnings
      spss.TextBlock("Warning", blockstring("""A warning was issued by previous commands,
      there MAY be a problem with the model.  Alternatively, SPSS made a problem of a harmless
      matter (like changing the covtype to 'id') or an unrelated command issued a warning
      and the model is fine.""") )
    elif errorlevel!=notchecked and errorlevel > 2:
      spss.TextBlock("SPSS Error",
                     blockstring("""SPSS raised a serious error (errorlevel=%s). """) % \
                     errorlevel )
    if outputweird:
      spss.TextBlock("Error", outputweird)
    if message:
      spss.TextBlock("StopModel", "Ending model '%s'" % name)
    spss.EndProcedure()
  currentmodel = None


def getm2llr(name, verbose=False):
  """Utility function to obtain 2LLR

  Optionally prints the value of the -2LLR from the Information Criteria table, mostly
  for testing purposes."""
  # TODO add a [1] or [Last] here and to all xpaths.
  xpa = xpastring("""//pivotTable[@subType='Information Criteria']
    //dimension[@axis='row']
    //category[@text="-2 Log Likelihood"]
    /cell/@text""")
  m2llr = spss.EvaluateXPath(name, '/outputTree', xpa)[0]
  if verbose:
    print m2llr
  return m2llr


def getaic(name, verbose=False):
  """Utility function to obtain AIC"""
  xpa = xpastring("""//pivotTable[@subType='Information Criteria']
    //dimension[@axis='row']
    //category[@text="Akaike's Information Criterion (AIC)"]
    /cell/@text""") # ' single quote to fool python-mode
  aic = spss.EvaluateXPath(name, '/outputTree', xpa)[0]
  if verbose:
    print aic
  return aic


def getnumparameters(name, verbose=False):
  xpa = xpastring("""//pivotTable[@subType='Model Dimension']
    //dimension[@axis='row']//category[@text="Total"]
    //dimension[@axis='column']//category[@text="Number of Parameters"]
    /cell/@text""")
  df = spss.EvaluateXPath(name, '/outputTree', xpa)[0]
  if verbose:
    print df
  return df


def getrandomparameters(name, verbose=False):
  xpa = xpastring("""//pivotTable[@subType='Model Dimension']
    //group[@text='Random Effects']
    //dimension[@axis=\'column\']/category[@text="Number of Parameters"]
    /cell/@text""")
  params = spss.EvaluateXPath(name, '/outputTree', xpa)
  # first we check whether there are any random effects
  if len(params)>0:
    params = [ int(p) for p in params ]
  else:
    params = list([0])
  if verbose:
    print params
  return params


def getallvarnames(strmethod=None, labels=False):
  """Return a list with all variable names from the spss dataset; if
  labels is set, return a list of variable name/variable label tuples"""

  res = list()
  for n in range(spss.GetVariableCount()):
    name = spss.GetVariableName(n)
    if strmethod:
        # this can be operator.methodcaller in python 2.6
        name = str.__dict__[strmethod](name)
    if labels:
      label = spss.GetVariableLabel(n)
      res.append((name, label))
    else:
      res.append(name)
  return res



class ModelComparison(object):
  def __init__(self, title1, title2):
    self.name1 = title1
    self.name2 = title2
    if invalidhandlewarning((self.name1, self.name2)):
      raise DjmixedFatal('Model not found')

  def getallparams(self):
    self.fit1 = getm2llr(self.name1)
    self.fit2 = getm2llr(self.name2)
    self.aic1 = getaic(self.name1) 
    self.aic2 = getaic(self.name2)
    self.npar1 = getnumparameters(self.name1)
    self.npar2 = getnumparameters(self.name2)
    self.nrandom1 = sum(getrandomparameters(self.name1))
    self.nrandom2 = sum(getrandomparameters(self.name2))


  def swapparams(self, inspssproc=True):
    if inspssproc:
      spss.TextBlock("Warning",
""" Warning: Model A has more parameters than model B but Model A
    should be nested within Model B.  The models have been switched
    around to allow this routine to continue but care should be taken
    with the interpretation of the outcomes.""")
    (self.name1, self.name2) = (self.name2, self.name1)
    (self.fit1, self.fit2) = (self.fit2, self.fit1)
    (self.aic1, self.aic2) = (self.aic2, self.aic1)
    (self.npar1, self.npar2) = (self.npar2, self.npar1)


  def samemodeltest(self, inspssproc=True):
      if self.npar1 == self.npar2 and self.aic1 == self.aic2 and self.fit1 == self.fit2:
        if inspssproc:
          spss.TextBlock("Error", blockstring(
            """The two models appear to be identical because they have the same
            number of parameters, the same AIC value and the same -2 Log
            Likelihood value.  """))
        #if __debug__: print "DEBUG", self.name1,self.fit1, \
        #   self.npar1, self.name2,self.fit2,self.npar2
        raise DjmixedFatal("Models are identical")


  def convergencetest(self):
    """Test both models for convergence, produce warning message if appropriate"""

    wronglist = list()
    xpa = "//pivotTable[@subType='Warnings']//dimension[@axis='row']//category/cell/@text"
    errmsg = spss.EvaluateXPath(self.name1, '/outputTree', xpa)
    re_errmsg = re.compile("convergence has not been achieved|final Hessian matrix is not positive definite")
    if errmsg and re_errmsg.search(errmsg):
      wronglist.append(self.name1)
    errmsg = spss.EvaluateXPath(self.name2, '/outputTree', xpa)
    if errmsg and re_errmsg.search(errmsg):
      wronglist.append(self.name2)
    if wronglist:
      return longstring("""SPSS output seems to indicate
      that model(s) '%s' did not converge.  If this is correct, the
      comparison presented here is invalid. """) % ','.join(wronglist)
      # full mesg is 'Iteration was terminated but convergence has not been achieved. The MIXED procedure continues despite this warning. Subsequent results produced are based on the last iteration. Validity of the model fit is uncertain.' 
      # full mesg is 'The final Hessian matrix is not positive definite although all convergence criteria are satisfied. The MIXED procedure continues despite this warning. Validity of subsequent results cannot be ascertained.'
      # MAYBE also use spss.GetLastErrorLevel()



  def make_numeric(self):
    # MAYBE: add better error reporting here, see cookbook ch8
    try:
      self.fit1 = float(self.fit1)
      self.fit2 = float(self.fit2)
      self.aic1 = float(self.aic1)
      self.aic2 = float(self.aic2)
      self.npar1 = int(self.npar1)
      self.npar2 = int(self.npar2)
    except ValueError, v:
      spss.TextBlock("Fatal","Error: ValueError in conversion")
      raise DjmixedFatal(longstring("""Conversion of fit index or number of
          parameters to numerical value failed"""), v)



def invalidhandlewarning(handlelist):
  """This function generates a detailed warning if there any invalid
  handle names in the handlelist.  It returns False if there was no
  warning, True if there was. """
  inlist = spss.GetHandleList()
  res = list()
  for h in handlelist:
    if not h in inlist:
      res.append(" '%s'" % h )
  if res:
    res = ','.join(res)
    spss.TextBlock("Error", blockstring(""" Error: One or more
    invalid model names (handles) were specified.
    The following model names were not found among the presently defined
    models: \n  %s """) % res)
    return True
  else:
    return False



def comparemodels(name1, name2):
  """Do a standard likelihood ratio test (LRT) on two models """
  # MAYBE report on model difference in terms of parameters, and while at it, catch the
  # case where comparerandommodels should be used instead.
  spss.StartProcedure("DJMIXED.CompareModels")

  try:
    mc = ModelComparison(name1, name2)
    mc.getallparams()
    if mc.npar1 > mc.npar2:
      mc.swapparams()
    mc.samemodeltest()
    mc.make_numeric()

    chisqvalue = mc.fit1 - mc.fit2
    chisqdf = mc.npar2 - mc.npar1
    chisqpval = djstats.pchisq(chisqvalue, chisqdf, lowertail=False)
    # if chisqpval < 0.05:
    #   bestmodel = "Model 2"
    # else:
    #   bestmodel = "Model 1"
    # 
    # ### OLD
    # table = spss.BasePivotTable("Likelihood Ratio Test",
    #     "djmixed_comparemodels",
    #     caption= footnote("""Comparison of two mixed models with LRT. 
    #     A significant result indicates that the more 
    #     complex Model 2 is a better fit than the 
    #     simpler Model 1."""))
    # convwarn = mc.convergencetest()
    # if convwarn:
    #   table.TitleFootnotes(convwarn)     
    # table.SimplePivotTable(rowdim="", coldim="",
    #     rowlabels=("Model 1 name", "Model 2 name",
    #                "-2LLR for Model 1", "AIC for Model 1", "Number of Parameters for Model 1",
    #                "-2LLR for Model 2", "AIC for Model 2", "Number of Parameters for Model 2",
    #                "Chi-square value", "Chi-square df","p-value", 
    #                "LRT Best model  (alpha=0.05)"),
    #     collabels = ["Value"], 
    #     cells = (mc.name1, mc.name2, mc.fit1, mc.aic1, mc.npar1, 
    #              mc.fit2, mc.aic2, mc.npar2,
    #              chisqvalue, chisqdf, chisqpval, bestmodel ) )
    # 
    # ### NEW

    alpha = 0.05
    def bestmodel(comp):
      #if isinstance(comp, bool):
      #if isinstance(comp, (bool, numpybool_)):
      # SHOOT numpy, it has its own bool variant
      #
      # Lesson: do not check for type but ducktype with try/execpt
      if comp == True:
        return 'A'
      elif comp == False:
        return 'B'
      else:
        return comp  

    cells = [[mc.name1, mc.fit1, mc.aic1, mc.npar1, ' ',        ' ',     ' ' ],
             [mc.name2, mc.fit2, mc.aic2, mc.npar2, ' ',        ' ',     ' ' ],
             [' '     , ' '    , ' ',     ' ',      chisqvalue, chisqdf, chisqpval]]
    comparison = [' ', mc.fit1<mc.fit2, mc.aic1<mc.aic2, mc.npar1<mc.npar2,
                 ' ', ' ',  chisqpval>=alpha]

    comparison = [ bestmodel(x) for x in  comparison ]
    cells.append(comparison)
    cells = transpose(cells)

    table = spss.BasePivotTable('Compare Models', 'OMS subtype')
    table.SimplePivotTable(  \
      rowlabels = ['Model Name', '-2LL',  'AIC', 'Number of Parameters', 
            'Chi-squared', 'Df', 'p-value' ],
      collabels = ['Model A','Model B', 'LRT','Best'],
      cells =  cells )

    assumptions = footnote("""
    Assumptions: 1/ Model A is nested within Model B, which makes Model B
    a more complex model (more parameters).  2/ Model A and Model B do
    not only differ in random effects (use 'comparerandommodels' for comparing
    models that only differ in random effects).
    The LRT (likelihood ratio test) evaluates the improved fit
    of Model B against the lower number of parameters of Model A and
    suggests which model is best based on a Chi-Squared test (with
    alpha=%f).""" % alpha)
    convwarn = mc.convergencetest()
    if convwarn:
       table.TitleFootnotes(str(convwarn) + '\n' + assumptions)
    else:
       table.TitleFootnotes(assumptions)
    

    
  finally:
    spss.EndProcedure()



                   
      


def comparerandommodels(name1, name2):
  """Do a likelihood ratio test (LRT) on two models, using a chisquare mixture to 
  account for that fact that they only differ in random parameters """
  spss.StartProcedure("DJMIXED.CompareRandomModels")
  
  try:    # massive try to always do spss.endprocedure
    mc = ModelComparison(name1, name2)
    mc.getallparams()
    if mc.nrandom1==0 or mc.nrandom2==0:
      spss.TextBlock("Error", blockstring("""Error:
    This routine is only appropriate for the comparison of two
    models that have the same fixed effects, differ in their random
    effects and have more than one random effect in each model.  One
    of the models fails this last requirement."""))
      raise DjmixedFatal('No random effects in either model')
      
    if mc.npar1 > mc.npar2:
      mc.swapparams()
    mc.samemodeltest()
    mc.make_numeric()

    chisqvalue = mc.fit1 - mc.fit2
    chisqpval1 = djstats.pchisq(chisqvalue, mc.nrandom1, lowertail=False)
    chisqpval2 = djstats.pchisq(chisqvalue, mc.nrandom2, lowertail=False)
    chisqpval = 0.5* chisqpval1 + 0.5* chisqpval2
    chisqdf = str(mc.nrandom1) + "," + str(mc.nrandom2)

    if chisqpval < 0.05:
      bestmodel = "Model 2"
    else:
      bestmodel = "Model 1"


    spss.TextBlock("Note",
""" Note: This routine is only appropriate for the comparison of two
    models that have the same fixed effects and differ their random
    effects only.  This routine uses a chi-squared mixture to obtain
    the correct statistics for this special case (Stram and Lee, 1994).  
    Comparison of any other types of models should be done with the 
    function 'comparemodels' instead.""")


    # MAYBE this output table could be made prettier by grouping 
    table = spss.BasePivotTable("Likelihood Ratio Test - Using chi-square mixture",
        "djmixed_comparerandommodels",
        caption=footnote("""Comparison of two mixed models with 
           LRT, where the mixed models only differ 
           in the random effects.  A significant result 
           indicates that the more complex Model 2 is a 
           better fit than the simpler Model 1."""))
    table.SimplePivotTable(rowdim="", coldim="",
        rowlabels=("Model 1 name", "Model 2 name",
                   "-2LLR for Model 1", "AIC for Model 1", 
                   "Number of Random Parameters for Model 1",
                   "Total number of Parameters for Model 1",
                   "-2LLR for Model 2", "AIC for Model 2", 
                   "Number of Random Parameters for Model 2", 
                   "Total number of Parameters for Model 2",
                   "Chi-square value", "Chi-square df","p-value",
                   "Best model (alpha=0.05)"),
        collabels = ["Value"], 
        cells = (mc.name1, mc.name2,
                 mc.fit1,mc.aic1, mc.nrandom1, mc.npar1,
                 mc.fit2, mc.aic2, mc.nrandom2, mc.npar2,
                 chisqvalue, chisqdf, chisqpval, bestmodel ) )
  finally:
    spss.EndProcedure()





def explode_interactions(predictors):
  """Scan the predictor (string) and write out an R-style interaction
  with all main effects syntax for each shorthand interaction, but use
  SPSS syntax in the product: 'A**B C' becomes 'A B A*B C'"""

  pass
  # MAYBE, this would be a nice addition

def fullfactorial(preds):
  """return a list with all n-way interactions added, input and output
  are space separated strings"""
  def innerff(plist):
    if len(plist)==1:
      return plist
    else:
      assert(len(plist)>0)
      restff = innerff(plist[1:])
      me = plist[0]
      res = [me]
      for p in restff:
        res.append(p)
        res.append(me+"*"+p)
      return res
  predlist = preds.split()
  return ' '.join(innerff(predlist))

      

def mixedmodel_spssparse(argstring):
  """helper for mixedmodel_spss, takes large string with all arguments
  (spss style) and returns a dictionary"""

  argstring = argstring.strip()
  validarguments = "dv predictors pps items stepwise name output plot".split()
  quotes = "'\""
  res = dict()
  argstring = argstring.replace(',', ' ').replace('/', ' ').replace('=', ' = ')
  arglist = argstring.split()
  print "ARGLIST",arglist
  # remove spss syntax remainders if present
  if arglist[0].upper()=='DJMIXED':
    del arglist[0]
  if arglist[0].upper()=='MIXEDMODEL':
    del arglist[0]
  if arglist[-1]==".":
    del arglist[-1]
  # parse it
  equalsigns = [ i for (i,x) in enumerate(arglist) if x=='=' ]
  varlist = [ arglist[i-1].lower() for i in equalsigns ]
  firstvaluesindex = [ i+1 for i in equalsigns ]
  lastvaluesindex = [ i-1 for i in equalsigns[1:] ] + [len(arglist)]
  valuelist = [ arglist[f:l] for (f,l) in zip(firstvaluesindex, lastvaluesindex) ]
  for var, val in zip(varlist, valuelist):
    if var not in validarguments:
      raise DjmixedFatal("Argument not recognised: %s " % var)
    if val[0][0]==val[-1][-1] and val[0][0] in quotes:
      val[0] = val[0][1:]
      val[-1] = val[-1][:-1]
    if len(val)==1:
      val = val[0]
    res[var] = val 
  return res
  

def mixedmodel_spss(argstring):
  """Construct an spss mixed model from the argument string, which
  holds spss-like syntax similar to the 'djmixed /mixedmodel ...' spss extension command

  The syntax is very flexible: Commas and slashes are removed, spaces
  are not significant, and the equal signs are used to parse the
  input.  Potential valid inputs include: 
   1. DV = rt, PREDICTORS=a b,   PPS=sub 
   2. /dv = rt /predictors=a b /pps=sub
   3. dv=rt  predictors=a,b  pps=sub      """
  #
  res = mixedmodel_spssparse(argstring)
  mixedmodel(**res)


def reparsepredictors(predictors):
  """Join all interactions into one word (a * b -> a*b) to produce a
  standardized list of actual predictors; Produce a list of all main
  effects that are mentioned or involved in interaction terms"""
  star = '*'
  predictors = predictors[:]
  while star in predictors:
    pos = predictors.index(star)
    predictors[pos-1:pos+2] = [''.join(predictors[pos-1:pos+2])]

  #mainpredictors = list(set(filter(lambda x: x!=star, predictors)))
  mainpredictors = set()
  for p in predictors:
    if not star in p:
      mainpredictors.add(p)
    else:
      for ppart in p.split(star):
        mainpredictors.add(ppart)
  
  return (' '.join(predictors), 
          ' '.join(mainpredictors))



def createdesignvariable(mainpredictors):
  """Return spss syntax that sets up a `designcell' variable, which
  has a different (consequetive) value for each cell of the design, as
  defined by crossing all main predictors.  Predictors can be numeric
  or string."""

  mainpredictors = mainpredictors.split() # it was a spss style space separated list
  res = list()
  for p in mainpredictors:
    vardict = spssaux.VariableDict(pattern=p+"$") # necessary as the API is retardedly case sensitive
    if vardict.numvars != 1:
      raise DjmixedFatal("Looked for predictor '%s' but found %d matches. " %(p, vardict.numvars))
    if vardict[0].VariableType==0: # numeric
      format = vardict[0].VariableFormat
      res.append("rtrim(ltrim(string(%s, %s)))" % (p, format))
    else:
      res.append("rtrim(ltrim(%s))" % p)
  res = "compute designcell=concat(" + ','.join(res) + ").\nexecute."
  vardict = spssaux.VariableDict(pattern="designcell$")
  if vardict.numvars==0:
    res = "string designcell (A64).\n" + res
  elif vardict[0].VariableType != 64:
    res = "delete variables designcell.\nstring designcell (A64).\n" + res
  return res
  
def splitsublist(src, sep):
  """divide list items from src into sublist at items that equal sep"""
  res = list()
  sub = list()
  for item in src:
    if item==sep:
      res.append(sub)
      sub = list()
    else:
      sub.append(item)
  if sub:
    res.append(sub)
  return res


def mixedmodel(dv, predictors=None, pps=None, items=None, 
               stepwise=None, name=None, output='SPLIT', posthoc=None,
               contrast=None, plot=None, modeltype=None):
  """Construct spss mixed model syntax from arguments, pythonic syntax

  The list of predictors is (changed) either a string or a list of
  strings. This command does not do any error checking (ie. whether dv
  is an existing variable and valid syntactically).  The command also
  has a number of intentional limitations, write your own mixed syntax
  directly for all cases not covered here."""
  global modelnumber

  #if stepwise:
  #  mixedmodelstepwise(dv, predictors, pps, items, stepwise, name, output)

  output = output.lower()
  if plot:
    plot = [ x.lower() for x in plot ]
  cmd = list(); precmd = list()
  cmd.append("MIXED %s" % dv )
  if predictors and predictors!='None':
    if isinstance(predictors, str):
      predictors, mainpredictors = reparsepredictors(predictors.split())
    else:
      predictors, mainpredictors = reparsepredictors(predictors)
    if modeltype and modeltype.lower()=="fullfactorial":
      predictors = fullfactorial(mainpredictors)
    cmd.append(" BY " + mainpredictors) 
  else:
    """no predictors mentioned"""
    predictors = mainpredictors = ""
  cmd.append(" /FIXED= %s | SSTYPE(3)" % predictors)
  if pps:
    cmd.append(" /RANDOM=INTERCEPT | SUBJECT(%s) COVTYPE(VC)" % pps)
  if items:
    cmd.append(" /RANDOM=INTERCEPT | SUBJECT(%s) COVTYPE(VC)" % items)
  if posthoc:
    if isinstance(posthoc, str):  
      posthoc = [posthoc]
    for v in posthoc:
      cmd.append(""" /EMMEANS = tables(%s) compare adj(sidak)""" % v)
  if contrast:
    contrast = splitsublist(contrast, '|')
    varname = contrast.pop(0)[0]
    msg = [ ' ' + varname + ' ' + ' '.join(coefs) for coefs in contrast ]
    msg = " /TEST 'contrasts on %s' " % varname  + ';'.join(msg)
    cmd.append(msg)
  if plot:
    # only residuals and equalvariance are options for now
    varnames = getallvarnames(strmethod='lower')
    delvars = [ x for x in ('predicted','residual') if x in varnames ]
    if delvars:
      precmd.append( "DELETE VARIABLES %s ." % ' '.join(delvars) )
    cmd.append("  /SAVE PRED(predicted) RESID(residual)")
    
  cmd.append(""" /METHOD=ML
/PRINT=SOLUTION  TESTCOV  COVB
/CRITERIA=CIN(95) MXITER(10000) MXSTEP(50) SCORING(1) SINGULAR(0.000000000001)
HCONVERGE(0, ABSOLUTE) LCONVERGE(0, ABSOLUTE) PCONVERGE(0.000001, ABSOLUTE) . """)

  if plot:
    if 'zresidual' in varnames:
      precmd.append("DELETE VARIABLES Zresidual .")
    cmd.append(cmdsyntax(""" 
      DESCRIPTIVES VARIABLES=residual  (Zresidual)  /SAVE ."""))
    if 'residuals' in plot:
      cmd.append(cmdsyntax(""" 
        EXAMINE VARIABLES=residual /PLOT =    histogram npplot .
        GRAPH  /SCATTERPLOT(bivar)=predicted WITH Zresidual .    """))
    if 'equalvariance' in plot:
      precmd.append(createdesignvariable(mainpredictors))
      cmd.append(cmdsyntax(""" 
        GGRAPH 
          /GRAPHDATASET NAME="graphdataset" VARIABLES=Zresidual designcell
            MISSING=LISTWISE REPORTMISSING=NO 
          /GRAPHSPEC SOURCE=INLINE. 
        BEGIN GPL 
          SOURCE: s=userSource(id("graphdataset")) 
          DATA: Zresidual=col(source(s), name("Zresidual")) 
          DATA: designcell=col(source(s), name("designcell"), unit.category()) 
          GUIDE: axis(dim(1), label("Zscore of Residuals")) 
          GUIDE: axis(dim(2), label("Frequency")) 
          GUIDE: legend(aesthetic(aesthetic.color.interior), label("designcell")) 
          ELEMENT: line(position(summary.count(bin.rect(Zresidual))),
            color.interior(designcell), missing.wings()) 
        END GPL.
        """)) # line -> area.stack for a pretty plot which is not as useful


  cmd = precmd + cmd
  cmd = "\n".join(cmd)

  if not name:
    name = 'model%02d' % modelnumber
    modelnumber += 1
  # remove surrounding quotes if present:
  elif name[0]==name[-1] and name[0] in "\"'":
    name = name[1:-1]

  if output=='split':
    error = silentsubmit(cmdsyntax("""
    OUTPUT NAME NAME=djmain .
    OUTPUT ACTIVATE djdetails ."""))
    if error:
      error = silentsubmit("OUTPUT NEW NAME=djdetails .\nOUTPUT ACTIVATE djdetails .")
      if error:
        print "Could not create new output, split may not work well"      

  if output=='full' or output=='split':
    print "== Submitting DJMIXED MIXEDMODEL '%s' == " % name
    print cmd

  startmodel(name, message=False, output=output)
  try:
    mysubmit(cmd, silent=False)  # produce output, but startmodel may OMS it away
    errlevel = spss.GetLastErrorLevel()
    # need to account for exceptions here, as wrong syntax will throw        
  except spss.errMsg.SpssError, v:
    # MAYBE need to have a way to signal that model error here
    # if we submit pre/main/post cmd separately, we can at least see where the error
    # occurred.  or we resplit cmd on periods and submit in parts.   
    stopmodel(name, message=True, modelerror=True)
    spss.Submit("omsend.")
    # cannot reraise for some reason
    print "ERROR:\nSPSS signalled the following error while processing this command:\n%s" % \
          v
  else:
    stopmodel(name, message=False, modelerror=False)
  if output=='split':
    error = silentsubmit("OUTPUT ACTIVATE djmain .")
    # print "Back to djmain" 
  
  
  if output=='none':
    spss.StartProcedure('DJMIXED.MixedModel')
    try:
      print "Submitted model '%s'" % name
      print cmd
    finally:
      spss.EndProcedure()

  if output=='split':
    print "Automatically calling 'modelsummary' because split output was requested"
    spss.StartProcedure('DJMIXED.ModelSummary.Auto')
    try:
      copywarnings(name)
      fixedeffects_table(name)
      randomeffects_table(name)
    finally:
      spss.EndProcedure()




re_spurious = re.compile('The covariance structure for random effect with only one level will be changed to Identity.')

def copywarnings(model):
  xpa = xpastring("""//pivotTable[@subType='Warnings']
     //cell/@text""")
  match = spss.EvaluateXPath(model, '/outputTree', xpa)
  for warn in match:
    if not re_spurious.search(warn):
      spss.TextBlock("Warning", "SPSS issued the following warning: \n" + warn)
               


def relatedbetas(nonredundants, fterm):
  """return a list of nonredundant effects that are related to this fixed term"""
  star = '*'
  res = list()
  fparts = [ p.strip() for p in fterm.split() if p != star ]
  fparts = set(fparts)
  
  for nr in nonredundants:
    nrparts = set()
    for x in nr.split():
      if x!=star:
        if re.match('\w+$', x):
          nrparts.add(x)          
        else:
          match = re.match('\[(\w+)=\w+]$', x)
          if match:
            nrparts.add(match.group(1))
    if fparts == nrparts:
      res.append(nr)
  # print "Related betas for '%s': " % fterm, res
  return res

  



def fixedeffects_table(model):
  star = '*'
  cells = list()
  pivot = spss.BasePivotTable('Fixed Effects','djmixed_modelsummary_fixed')
  xpa = xpastring("""//pivotTable[@subType='Tests of Fixed Effects']
      /dimension[@axis='row']
      /category/@text""")
  fixedterms = spss.EvaluateXPath(model,'/outputTree',xpa)
  # now retrieving all names of NON-redundant parameter estimates
  xpa = xpastring("""//pivotTable[@subType='Parameter Estimates']/dimension[@axis='row']
    /category[not(./dimension/category[1]/cell/footnote/note[contains(@text,'redundant')])]/@text""")
  nonredundants = spss.EvaluateXPath(model,'/outputTree',xpa)

  if len(fixedterms)==0:
    raise DjmixedFatal("""Fixedeffectstable: No fixed effect terms were found in the model's
    output, please make sure the model ran without errors.""")

  for fterm in fixedterms:
    # we could also read the whole line with this, but this is more dependent on the output
    # xpa = xpastring("""//pivotTable[@subType='Parameter Estimates']
    # /dimension[@axis='row']/
    # /category[@text='%s']
    # /dimension//*/@text""" % fterm )
    # line = spss.EvaluateXPath(model,'/outputTree',xpa)
    # # * ['Estimate', '623.781437', 'Std. Error', '16.979185', 'df', '83.714', 't', '36.738', 'Sig.', '.000', 
    # # '95% Confidence Interval', 'Lower Bound', '590.014779', 'Upper Bound', '657.548096']
    # line = dict([ (line[i], line[i+1]) for i in range(0,9,2) ])
    

     
    xpa = xpastring("""//pivotTable[@subType='Tests of Fixed Effects']
       /dimension[@axis='row']
       /category[@text='%s']
       /*/category[@text='F']/cell/@text""" % fterm)
    fval = spss.EvaluateXPath(model,'/outputTree',xpa)[0]
    xpa = xpastring("""//pivotTable[@subType='Tests of Fixed Effects']
       /dimension[@axis='row']
       /category[@text='%s']
       /*/category[@text='Sig.']/cell/@text""" % fterm)
    pval = spss.EvaluateXPath(model,'/outputTree',xpa)[0]

    # if fterm.find(star) < 0:
    #   re_fterm = '^\[%s=\w+]$' % fterm
    #   betas =  [ x for x in nonredundants if x==fterm or  re.search(re_fterm, x) ]
    # else:
    #   # interaction term, this assumes a * b (with spaces)
    #   parts = [ r'\b'+p.strip()+r'\b' for p in fterm.split() if p != star ]
    #   betas = [x for x in nonredundants if all(map(lambda part: re.search(part,x), parts)) ]
    betas = relatedbetas(nonredundants, fterm)
    if len(betas)==1:
      xpa = xpastring("""//pivotTable[@subType='Parameter Estimates']
         /dimension[@axis='row']/category[@text='%s']
         /*/category[@text='Estimate']/cell/@text""" % betas[0])
      beta = spss.EvaluateXPath(model,'/outputTree',xpa)[0]
    else:
      if len(betas)==0:
        print longstring("""STRANGE:  found zero non-redundant parameters for effect '%s', 
          continueing but something may be wrong.""" % fterm )
      beta = '--'
    cells.append((fterm, beta, fval, pval))
 
  # print dict(
  pivot.SimplePivotTable(
      rowdim="",
      coldim="Model name: "+ model,
      rowlabels=map(lambda x:str(x+1), range(len(fixedterms))), 
      collabels=('Model Term', # 'Comparison', MAYBE
                 'beta','F','p'),
      cells=cells)



def randomeffects_table(model):
  cells = list()
  footnotes = list()
  pivot = spss.BasePivotTable('Random Effects','djmixed_modelsummary_random')
  # MAYBE this is not an ideal xpath for this, the * should be category or group
  # prolly /*[name()='category' or name()='group']
  xpa = xpastring("""//pivotTable[@subType='Covariance Parameter Estimates']
      /dimension[@axis='row']/*/@text""")
  randomterms = spss.EvaluateXPath(model,'/outputTree',xpa)
  # ['Residual', 'Intercept [subject = Participant]', 'Intercept [subject = Word]']

  # the xml structure of residual is different from the other ones, sigh.
  # also residual should be last
  # the 'variance' refers to variance components, if you use covtype(un) you get the familiar 
  # listing of UN(1,2) etc here, which we cannot grok.

  if not 'Residual' in randomterms:
    raise DjmixedFatal("""Randomeffectstable:  No 'residual' term was found in the model's
    output, please make sure the model ran without errors.""")
  for rterm in randomterms:
    if rterm == 'Residual':
      continue
    # parse name
    match = re.match('(\w+) \[subject = (\w+)]$', rterm)
    if not match:
      raise DjmixedFatal("""Randomeffectstable:  No 'subject' term was found in the model's
    output, please make sure the model ran without errors.""")
    rtermnice, rtermwithin = match.group(1), match.group(2)
    # retrieve values
    xpa = xpastring("""//pivotTable[@subType='Covariance Parameter Estimates']
      /dimension[@axis='row']/group[@text="%s"]
      //*/@text""" % rterm )
    line = spss.EvaluateXPath(model,'/outputTree',xpa)
    # ['Variance', 'Statistics', 'Estimate', '5627.489502', 'Std. Error', '1466.568900', 'Wald Z', '3.837', 
    #  'Sig.', '.000', '95% Confidence Interval', 'Lower Bound', '3376.639870', 'Upper Bound', '9378.743161']
    re_redundant = re.compile('This covariance parameter is redundant')
    match = [ n for n,i in enumerate(line) if re.match(re_redundant, i) ]
    if match:
      for n in match: 
        del line[n]
      footnotes.append("Model term '%s [%s]' is redundant. " % (rtermnice, rtermwithin) )      
    line[0:2] = (line[1], line[0])
    line = dict([ (line[i], line[i+1]) for i in range(0,9,2) ])
    if line['Statistics'] != 'Variance':
      spss.TextBlock("Error", blockstring("""For this function to work, every random effect must be 
        of type 'id' or type 'vc'.  This problem was encountered when reading random effect '%s'. """ % rterm) )
      return
    
    cells.append((rtermnice, rtermwithin,  # pretty HACK y:
                  spss.CellText.Number(float(line['Estimate']),  spss.FormatSpec.Coefficient),
                  line['Wald Z'], line['Sig.'] ))

  # due to spss weirdness this is parsed slightly differently

  rterm = 'Residual'
  xpa = xpastring("""//pivotTable[@subType='Covariance Parameter Estimates']
      /dimension[@axis='row']
      /category[@text="%s"]//*/@text""" % rterm)
  line = spss.EvaluateXPath(model,'/outputTree',xpa)
  line = dict([ (line[i], line[i+1]) for i in range(1,8,2) ])
  rtermnice = 'Error'
  rtermwithin = '--'
  cells.append((rtermnice, rtermwithin, 
                spss.CellText.Number(float(line['Estimate']),  spss.FormatSpec.Coefficient),
                line['Wald Z'], line['Sig.'] ))

  pivot.SimplePivotTable(
      rowdim="",
      coldim="Model name: "+ model,
      rowlabels=map(lambda x:str(x+1), range(len(randomterms))), 
      collabels=('Model Term', 'Adjustment for', 'Variance', 'Wald Z', 'p'), 
      cells=cells)
  if footnotes:
    pivot.TitleFootnotes('\n'.join(footnotes))



def modelsummary(model):
  """Give a nice tabular overview of a model, similar to the tables in
  the paper (for example set1m4)"""

  # MAYBE add * for model name, same as previous
  if invalidhandlewarning([model]):
    raise DjmixedFatal('Model not found') 
    # we could just return here but we raise elsewhere
  spss.StartProcedure("DJMIXED.modelsummary")
  try:
    copywarnings(model)
    fixedeffects_table(model)
    randomeffects_table(model)
  finally:
    spss.EndProcedure()


  
  

# def mixedmodelstepwise(dv, predictors=None, pps=None, items=None, 
#   stepwise="order", name=None, output=True):
# 
#   """Construct spss mixed model syntax from arguments, using stepwise
#   evaluation of the predictors
#   """
#   #
#   global modelnumber
# 
#   try:
# 
#     cmd = list()
#     cmd.append("MIXED %s" % dv )
#     if predictors:
#       cmd.append(" BY " + predictors + " " + pps + " " + items)
#     cmd.append(" /FIXED= %s | SSTYPE(3)" % predictors)
#     if pps:
#       cmd.append(" /RANDOM=INTERCEPT | SUBJECT(%s) COVTYPE(VC)" % pps)
#     if items:
#       cmd.append(" /RANDOM=INTERCEPT | SUBJECT(%s) COVTYPE(VC)" % items)
#     cmd.append("""   /METHOD=ML
#    /PRINT=SOLUTION TESTCOV
#    /CRITERIA=CIN(95) MXITER(10000) MXSTEP(50) SCORING(1) SINGULAR(0.000000000001)
#     HCONVERGE(0, ABSOLUTE) LCONVERGE(0, ABSOLUTE) PCONVERGE(0.000001, ABSOLUTE) . """)
#     cmd = "\n".join(cmd)
# 
#     if not name:
#       name = 'model%02d' % modelnumber
#       modelnumber += 1
# 
#     print "Submitting model '%s'" % name
#     print cmd
# 
#     startmodel(name, message=False)
#     try:
#       spss.Submit(cmd)
#     finally:
#       stopmodel(name, message=False)
#   finally:
#     pass
# 




def removemodel(name, message=True):
  """there currenlty is no spss syntax for this"""
  global currentmodel, modelhandles
  if name is None:
    raise DjmixedFatal('Name argument mandatory for removemodel')
  if currentmodel is not None:
    print "Auto-Ending model '%s'" % currentmodel
    currentmodel = None
  spss.DeleteXPathHandle(name)
  modelhandles.remove(name)
  if message:
    spss.StartProcedure('DJMIXED.RemoveModel')
    #print "Removing model '%s'" % name
    spss.TextBlock("RemoveModel", "Removing model '%s'" % name ) 
    spss.EndProcedure()

  
  
def remove_all_oxml():
  global currentmodel, modelhandles
  if currentmodel is not None:
    print "Auto-Ending model '%s'" % currentmodel
    currentmodel = None
  for name in modelhandles:
    spss.DeleteXPathHandle(name)
  modelhandles.clear()
 
  
  


def Run(args):
  """This function will be called by SPSS when the DJMIXED command has
  been read, with the baroque spss nested argument dictionary as the
  one argument """

  #print "ARGS", args
  templates = list()
  defaults = dict()

  # A startmodel
  templates +=  [extension16.Template(
          subc="STARTMODEL", kwd="NAME", 
          var="name", islist = False, ktype="literal")]

  # B stopmodel, with last as LeadingToken, doesn't work 
  templates +=  [extension16.Template(
          subc="STOPMODEL", kwd="NAME", 
          var="name", islist = False, ktype="literal")]
  
  templates +=  [extension16.Template(
          subc="STOPMODEL", kwd="LAST", 
          var="stoplast", islist = False, ktype="bool")]
  defaults['STOPMODEL','stoplast']=False 


  
  # C comparemodels
  ## TODO rename this to compare, have this output 2 columns, one with values
  ## for m1 one for m2.  that way we can extend this to multiple comparisons and 
  ## it will look better.  actually, have models in rows instead.
  templates +=  [extension16.Template(
          subc="COMPAREMODELS", kwd="NAME1", 
          var="compm1", islist = False, ktype="literal")]
  templates +=  [extension16.Template(
          subc="COMPAREMODELS", kwd="NAME2", 
          var="compm2", islist = False, ktype="literal")]

  # C optional
  templates +=  [extension16.Template(
          subc="COMPAREMODELS", kwd="TYPE", 
          var="comptype", islist = False, ktype="literal", 
          vallist=['fixed','random'])]
  defaults['COMPAREMODELS','comptype']='fixed' 


  # modelsummary
  templates +=  [extension16.Template(
          subc='MODELSUMMARY', kwd="NAME",
          var="name", islist=False, ktype="literal") ]

  # D mixedmodel
  # def mixedmodel(dv, predictors=None, pps=None, items=None, name=None):
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="DV", 
          var="dv", islist = False, ktype="varname")]
  defaults['MIXDEDMODEL','DV']=None
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="PREDICTORS", 
          var="predictors", islist = True, ktype="literal")]
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="PPS", 
          var="pps", islist = False, ktype="varname")]
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="ITEMS", 
          var="items", islist = False, ktype="varname")]
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="NAME", 
          var="name", islist = False, ktype="literal")]
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="OUTPUT", 
          var="output", islist = False, ktype="literal",
          vallist=['none','split','full'] )]
  defaults['MIXDEDMODEL','OUTPUT']='split'
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="POSTHOC", 
          var="posthoc", islist = True, ktype="existingvarlist")]
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="CONTRAST", 
          var="contrast", islist = True, ktype="literal")]
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="PLOT", 
          var="plot", islist = True, ktype="literal",
          vallist=['residuals' 'equalvariance'] )]
  templates +=  [extension16.Template(
          subc="MIXEDMODEL", kwd="MODELTYPE", 
          var="modeltype", islist = False, ktype="literal",
          vallist=['fullfactorial','maineffects'] )]

  cmdname = args.keys()[0]
  assert(cmdname == 'DJMIXED')
  subcommands = args[cmdname].keys()
  if '' in subcommands:  
    subcommands.remove('')
  if len(subcommands) != 1:
    # MAYBE we could actually relax this but we'd have to define an order as
    # the user supplied order will not be honored by the dictonairy
    raise DjmixedFatal(longstring("""Incorrect number of subcommands given:
    Expected exactly 1 and found %d subcommand: %s """) %
                 (len(subcommands), subcommands) )
  subcommand = subcommands[0]

  declaration = extension16.Syntax(templates)
  declaration.parsecmd(args[cmdname], vardict = spssaux.VariableDict())
  parseddict = declaration.parsedparams

  # add defaults to dict
  for (subc, keyword),value in defaults.items():
    if subc == subcommand and not keyword in parseddict:
      parseddict[keyword]=value

  # print "PARSED:", parseddict
  # print "SUBC:", subcommand
  Runpy(subcommand, **parseddict)



  

def Runpy(subcommand, **argdict):
  """This is the python equivalent of Run, but with subcommand string
  as the first argument and keyword arguments following
  this. Despatching is done from here."""
  # TODO all python subcommands should check presence of required parameters

  try:
    args = Bunch(**argdict)
    if subcommand=='STARTMODEL':  
      startmodel(args.name)
    elif subcommand=='STOPMODEL': 
      if args.name:
        stopmodel(args.name)
      else:
        stopmodel()
    elif subcommand=='COMPAREMODELS': 
      if args.comptype.lower()=='fixed':
        comparemodels(args.compm1, args.compm2)
      else:
        comparerandommodels(args.compm1, args.compm2)
    elif subcommand=='MODELSUMMARY':
      modelsummary(args.name)
    elif subcommand=="MIXEDMODEL":
      mixedmodel(**argdict) 
    else:
      DjmixedFatal("Unrecognised subcommmand '%s'" % subcommand )
  except DjmixedFatal, e:
    print "=================================================================="
    print "An error occurred in DJMIXED"
    print "[Version information: %s]" % __version__
    print e
    if DEBUG:
      print "------------------------------------------------------------------"
      import traceback
      tb = sys.exc_info()[2]
      traceback.print_exception(e.__class__, e, tb)
      print "------------------------------------------------------------------"
      raise
    print "=================================================================="
    # TODO one day , make this nicer with a pivottable etc.
    # the problem is what procedure output this should be etc.
    
  
