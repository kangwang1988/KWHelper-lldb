import os
import errno
import time
import lldb

def _evalNoneObjRetExprValueWithLang(expr):
  # print expr
  frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
  expr_options = lldb.SBExpressionOptions()
  language=lldb.eLanguageTypeObjC_plus_plus
  expr_options.SetLanguage(language)  # requires lldb r210874 (2014-06-13) / Xcode 6
  value = frame.EvaluateExpression(expr, expr_options)
  printErrors = True
  print expr
  print "[KWLM]"
  print value
  return value

def _evalObjRetExprValueWithLang(expr):
  expr='(id)(' + expr + ')'
  return _evalNoneObjRetExprValueWithLang(expr);
  
def _evalBooleanRetExprValueWithLang(expr):
    value = _evalNoneObjRetExprValueWithLang(expr).GetValue()
    if value == 'false':
        return 0
    else:
        return 1
  
def _isKindOfClass(obj,className):
    expr = '(BOOL)[(id)%s isKindOfClass:(Class)%s]' %(obj,className)
    return (_evalBooleanRetExprValueWithLang(expr))
 
def _wrtData2File(filePath,dataAddr,dataLen):
    address = int(dataAddr.GetValue(), 16)
    length = int(dataLen.GetValue(),16)
    if not (address or length):
        print 'Could not get image data.'
    process = lldb.debugger.GetSelectedTarget().GetProcess()
    error = lldb.SBError()
    mem = process.ReadMemory(address, length, error)
    if error is not None and str(error) != 'success':
        print error
    else:
        txtFile = open(filePath, 'wb')
        txtFile.write(mem)
        txtFile.close()
    return filePath

def _data2SaveOfTxt(text):
    return _evalObjRetExprValueWithLang('(void*)[(id)' + text + ' dataUsingEncoding:4]').GetValue()
    
def _data2SaveOfImg(img):
    return _evalObjRetExprValueWithLang('(void*)UIImageJPEGRepresentation((id)'+img+',1.f)').GetValue()
    
def _data2SaveOfView(view):

    width = _evalNoneObjRetExprValueWithLang('((CGRect)[(id)'+view+' bounds]).size.width').GetValue()
    height = _evalNoneObjRetExprValueWithLang('((CGRect)[(id)'+view+' bounds]).size.height').GetValue()
    opaque = _evalBooleanRetExprValueWithLang('[(UIView*)'+view+' isOpaque]')
    expr = 'eobjc (void)UIGraphicsBeginImageContextWithOptions(CGSizeMake('+width+','+height+')' + ', %d, 0.0)' %(opaque)
    lldb.debugger.HandleCommand(expr)
    lldb.debugger.HandleCommand('eobjc (void)[(id)[(id)' + view + ' layer] renderInContext:(void *)UIGraphicsGetCurrentContext()]')

    frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
    result = frame.EvaluateExpression('(UIImage *)UIGraphicsGetImageFromCurrentImageContext()')
    image = None
    if result.GetError() is not None and str(result.GetError()) != 'success':
      print result.GetError()
    else:
      image = result.GetValue()

    lldb.debugger.HandleCommand('eobjc (void)UIGraphicsEndImageContext()')
    print image
    return _data2SaveOfImg(image)

def wrtObj2File(obj):
  ext='.dat'
  data=None
  if _isKindOfClass(obj.GetValue(),'[NSString class]'):
      ext='.txt'
      data = _data2SaveOfTxt(obj.GetValue())
  elif _isKindOfClass(obj.GetValue(),'[UIImage class]'):
      ext='.jpg'
      data = _data2SaveOfImg(obj.GetValue())
  elif _isKindOfClass(obj.GetValue(),'[UIView class]'):
      ext='.jpg'
      data = _data2SaveOfView(obj.GetValue())
  else:
      return
  objDirectory = '/tmp/xcode_lldb_plugin/'
  objFileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime()) + ext
  objFilePath = objDirectory + objFileName
  try:
    os.makedirs(objDirectory)
  except OSError as e:
    if e.errno == errno.EEXIST and os.path.isdir(objDirectory):
      pass
    else:
      raise
  if obj.GetValue() is None:
      return
  dataAddr = _evalObjRetExprValueWithLang('(void*)[(id)' + data + ' bytes]')
  dataLen = _evalObjRetExprValueWithLang('(NSUInteger)[(id)' + data + ' length]')
  filePath = _wrtData2File(objFilePath,dataAddr,dataLen)
  if os.path.isfile(filePath):
      os.system('open ' + filePath)
  return