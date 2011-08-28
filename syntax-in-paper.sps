** spss syntax to go with DP Janssen (submitted)  .
** "Twice random, once mixed: Applying mixed models to simultaneously analyze random effects
   of language and participants" .

** $Revision$ .

* open the data file tw-set1d-spss.sav, this may be in a different place for you .
* this file contains 2004 cases.
get file='C:\flash2\schrijf\twicerandom\data1\tw-set1d-spss.sav'.
* get file='e:\flash\schrijf\twicerandom\data1\tw-set1d-spss.sav'.
dataset name tw.

* optional
extension /specification command="C:\Program Files\SPSSInc\SPSS16\extensions\djmixed.xml" .


*** PART 1 : One simple model (interaction model) **** .


MEANS TABLES=rt BY morph BY priming
  /CELLS MEAN COUNT STDDEV.


** model 1 : all main, interaction .
DJMIXED /MIXEDMODEL
              DV = rt
              PREDICTORS = priming morph priming*morph
              PPS = Participant
              ITEMS = Word
              NAME = 'interaction' .

DJMIXED /MODELSUMMARY
              NAME = 'interaction' .

*** PART 2 : step wise regression and model comparison **** .

** model 2 : null model .
DJMIXED /MIXEDMODEL
              DV = rt
              PPS = Participant
              ITEMS = Word
              NAME = 'null'  .


DJMIXED /MODELSUMMARY
              NAME = 'null' .

** model 3 : main effects.
DJMIXED /MIXEDMODEL
              DV = rt
               PREDICTORS = priming morph
             PPS = Participant
              ITEMS = Word
              NAME = 'main effects'  .

DJMIXED /MODELSUMMARY
              NAME = 'main effects' .

DJMIXED /COMPAREMODELS
            NAME1='null'   NAME2='main effects'.

DJMIXED /COMPAREMODELS
            NAME1='main effects' NAME2='interaction'   .




*** PART 3 :  post hocs and contrasts **** .

DJMIXED /MIXEDMODEL
             DV = rt
             PREDICTORS = form
             PPS = Participant
             ITEMS = Base
             NAME = 'posthoc on form'
             POSTHOC = form  .

DJMIXED /MODELSUMMARY
              NAME = 'posthoc on form' .

DJMIXED /MIXEDMODEL
             DV = rt
             PREDICTORS = form
             PPS = Participant
             ITEMS = Base
             NAME = 'contrast on form'
             CONTRAST = form | 0 1 -1 | 1 -0.5 -0.5   .



*** PART 4 : regression diagnostics and transforms **** .

DJMIXED /MIXEDMODEL
              DV = rt
              PREDICTORS = priming morph priming*morph
              PPS = Participant
              ITEMS = Word
              NAME = 'interaction'
              PLOT = residuals equalvariance
              OUTPUT = full .


compute logrt = ln(rt-100) .
execute.
DJMIXED /MIXEDMODEL
              DV = logrt
              PREDICTORS = priming morph
              PPS = Participant
              ITEMS = Word
              NAME = 'log main effects'
              PLOT = residuals
              OUTPUT = full .
DJMIXED /MIXEDMODEL
              DV = logrt
              PREDICTORS = priming morph priming*morph
              PPS = Participant
              ITEMS = Word
              NAME = 'log interaction'
              PLOT = residuals
              OUTPUT = full  .

DJMIXED /COMPAREMODELS
            NAME1='log main effects' NAME2='log interaction'   .






*** online appendix ****

* model with random factor for participant adjusting the effect of priming .

DJMIXED /STARTMODEL  NAME='model4' .
MIXED rt  BY morph priming
   /FIXED=  morph priming morph*priming
   /RANDOM= Intercept  Priming  | SUBJECT(Participant) COVTYPE(VC)
   /RANDOM= Intercept | SUBJECT(Word) COVTYPE(VC)
   /METHOD= ML
   /PRINT=SOLUTION  TESTCOV   G
   /CRITERIA=CIN(95) MXITER(10000) MXSTEP(50) SCORING(1) SINGULAR(0.000000000001)
    HCONVERGE(0, ABSOLUTE) LCONVERGE(0, ABSOLUTE) PCONVERGE(0.000001, ABSOLUTE) .
DJMIXED /STOPMODEL  NAME='*' .

** NOT CORRECT, COMPARISON INVOLVES TWO MODELS WHICH DIFFER IN RANDOM COMPONENTS ONLY .
DJMIXED /comparemodels NAME1='interaction' NAME2='model4' .

DJMIXED /comparemodels NAME1='interaction' NAME2='model4' type=random  .


*** EXTRA  **** .


* alternatively, you can call via python .
begin program python.
import DJMIXED
DJMIXED.mixedmodel(dv='rt', predictors='priming morph', pps='participant', items='word', name='main effects' )
DJMIXED.modelsummary('main effects')
DJMIXED.comparemodels('main effects', 'interaction')
end program.

* secondly, you can also use python but stay closer to the spss syntax .
begin program python.
DJMIXED.Runpy('MIXEDMODEL',
              dv = 'rt' ,
              predictors = 'priming morph priming*morph ',
              pps = 'Participant',
              items = 'Word',
              name = 'interaction' , output='full' )
DJMIXED.Runpy('MODELSUMMARY', name='interaction' )
end program.


