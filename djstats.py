# djdistributions.py
#
# To avoid importing 45M of scipy, I provide the option of using the
# library that scipy uses directly.
#
# This library is cephes, see www.netlib.org/cephes
# see http://pylab.sourceforge.net/packages for an overview of functions
# it provides.
# As far as I can reconstruct, cephes has been packaged for python
# by the numpy or numerical python team, thanks!!
# The library lives in _cephes.so (about 0.9M) or _cephes.pyd (1.9M)
#
# $Revision$
#
# Being lazy, I only wrap those function that I need
# which is currently ONE


import sys, os

try:
  import _cephes as cephes
except ImportError:
  """when unpacking an extension bundle, spss leaves non-python files in a directory with the 
  name of the bundle. so we temporarily add that name and then reload.  sigh """
  newdirs = [os.path.join(x, 'djmixed') for x in sys.path if 'SPSSInc' in x ]
  # TODO this only works when code is placed under SPSS, obviously
  sys.path.extend(newdirs)
  try:
    import _cephes as cephes
    sys.path[-(len(newdirs)):] = []
  except ImportError:
      """ if all fails, we see if scipy is present """
      sys.path[-(len(newdirs)):] = []
      try:
        import scipy.special._cephes as cephes
      except ImportError:
        raise ImportError("Could not find the _cephes.pyd library (or equivalent)")




#####  pchisq(value, df)  -> probability
# compare to scipy.stats.chi2.cdf(value, df) -> probability
# that routine returns the lower tail, ie the area between 0..value
# which is identical to R: pchisq(value, df)


def pchisq(value, df, lowertail=True):
  if lowertail:
    return cephes.chdtr(df, value)
  else:
    return cephes.chdtrc(df, value)



if __name__ == '__main__':
  pass


