"""Independent Python coefficient construction; system GMP is arithmetic only."""
import ctypes,ctypes.util
from collections import Counter
class _MPZ(ctypes.Structure):
 _fields_=[('alloc',ctypes.c_int),('size',ctypes.c_int),('limbs',ctypes.POINTER(ctypes.c_ulong))]
_lib=ctypes.CDLL(ctypes.util.find_library('gmp'))
_ptr=ctypes.POINTER(_MPZ);_g={}
for _name,_args in [('init',[_ptr]),('clear',[_ptr]),('set_str',[_ptr,ctypes.c_char_p,ctypes.c_int]),('setbit',[_ptr,ctypes.c_ulong]),('mul',[_ptr,_ptr,_ptr]),('fdiv_r_2exp',[_ptr,_ptr,ctypes.c_ulong]),('fdiv_r',[_ptr,_ptr,_ptr]),('sub_ui',[_ptr,_ptr,ctypes.c_ulong]),('get_str',[ctypes.c_void_p,ctypes.c_int,_ptr])]:
 _fn=getattr(_lib,'__gmpz_'+_name);_fn.argtypes=_args;_fn.restype=ctypes.c_int if _name=='set_str' else None;_g[_name]=_fn
class _Z:
 def __init__(self,n=0):
  self.value=_MPZ();_g['init'](ctypes.byref(self.value));assert _g['set_str'](ctypes.byref(self.value),str(n).encode(),10)==0
 def __del__(self):_g['clear'](ctypes.byref(self.value))
 def bit(self,k):_g['setbit'](ctypes.byref(self.value),k)
 def ref(self):return ctypes.byref(self.value)
def integer_polynomial_count(rows,bins):
 den=500**len(rows);mins=[min(row) for row in rows];cut=bins-sum(mins)
 if cut<=0:return 0,den
 if sum(max(row) for row in rows)<bins:return den,den
 stride=den.bit_length()+1;polynomials=[]
 for row,lo in zip(rows,mins):
  p=_Z()
  for k,n in Counter(x-lo for x in row if x-lo<cut).items():
   for b in range(n.bit_length()):
    if n>>b&1:p.bit(k*stride+b)
  polynomials.append(p)
 while len(polynomials)>1:
  nxt=[]
  for k in range(0,len(polynomials),2):
   if k+1==len(polynomials):nxt.append(polynomials[k]);continue
   p=_Z();_g['mul'](p.ref(),polynomials[k].ref(),polynomials[k+1].ref());_g['fdiv_r_2exp'](p.ref(),p.ref(),cut*stride);nxt.append(p)
  polynomials=nxt
 modulus=_Z();modulus.bit(stride);_g['sub_ui'](modulus.ref(),modulus.ref(),1);p=_Z();_g['fdiv_r'](p.ref(),polynomials[0].ref(),modulus.ref())
 buffer=ctypes.create_string_buffer(len(str(den))+2);_g['get_str'](buffer,10,p.ref());numerator=int(buffer.value);assert 0<=numerator<=den
 return numerator,den
