"""Small LV2 buffer driver shared by offline checks and the no-audio editor."""
import ctypes as C
import json
from pathlib import Path

PANEL_KNOBS=('time','size','shape','pitch','density','time_amount','size_amount',
             'shape_amount','pitch_amount','feedback','mix','reverb')

class Descriptor(C.Structure): pass
Instantiate = C.CFUNCTYPE(C.c_void_p, C.POINTER(Descriptor), C.c_double, C.c_char_p, C.POINTER(C.c_void_p))
Connect = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32, C.c_void_p)
Action = C.CFUNCTYPE(None, C.c_void_p)
Run = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32)
Extension = C.CFUNCTYPE(C.c_void_p,C.c_char_p)
Descriptor._fields_ = [('uri', C.c_char_p), ('instantiate', Instantiate), ('connect', Connect),
    ('activate', Action), ('run', Run), ('deactivate', Action), ('cleanup', Action), ('extension', Extension)]
MapFunction = C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_char_p)
class Map(C.Structure): _fields_=[('handle',C.c_void_p),('map',MapFunction)]
class Feature(C.Structure): _fields_=[('uri',C.c_char_p),('data',C.c_void_p)]
Store = C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32)
Retrieve = C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.POINTER(C.c_size_t),C.POINTER(C.c_uint32),C.POINTER(C.c_uint32))
Save = C.CFUNCTYPE(C.c_uint32,C.c_void_p,Store,C.c_void_p,C.c_uint32,C.POINTER(C.c_void_p))
Restore = C.CFUNCTYPE(C.c_uint32,C.c_void_p,Retrieve,C.c_void_p,C.c_uint32,C.POINTER(C.c_void_p))
class StateInterface(C.Structure): _fields_=[('save',Save),('restore',Restore)]

class Instance:
    def __init__(self, bundle, spec, quantum=128):
        self.spec, self.quantum = spec, quantum
        self.library = C.CDLL(str(Path(bundle) / 'mala.so'))
        self.knob_function=getattr(self.library,'mala_knob_response',None)
        if self.knob_function:
            self.knob_function.argtypes=[C.c_uint32,C.c_float]
            self.knob_function.restype=C.c_float
        self.library.lv2_descriptor.argtypes = [C.c_uint32]
        self.library.lv2_descriptor.restype = C.POINTER(Descriptor)
        self.dp = self.library.lv2_descriptor(0)
        self.d = self.dp.contents
        assert self.d.uri == b'urn:beebo-hector-lab:mala-preview'
        self.urids={}; self.map_callback=MapFunction(self.map_uri)
        self.map=Map(None,self.map_callback)
        self.map_feature=Feature(b'http://lv2plug.in/ns/ext/urid#map',C.cast(C.pointer(self.map),C.c_void_p))
        self.features=(C.c_void_p*2)(C.cast(C.pointer(self.map_feature),C.c_void_p).value,None)
        self.handle = self.d.instantiate(self.dp, 48000., str(bundle).encode(), self.features)
        if not self.handle: raise ValueError('Mala instantiation failed')
        self.controls, self.buffers = {}, {}
        for i, p in enumerate(spec):
            if 'audio' in p or 'cv' in p:
                storage = (C.c_float * (quantum + 8))()
                self.buffers[p['symbol']] = storage
                self.d.connect(self.handle, i, storage)
            else:
                storage = C.c_float(p.get('default', 0))
                self.controls[p['symbol']] = storage
                self.d.connect(self.handle, i, C.byref(storage))
    def set(self, symbol, value):
        p = next(p for p in self.spec if p['symbol'] == symbol)
        if p.get('control') == 'Output': raise ValueError('Read-only status')
        if not p['min'] <= value <= p['max']: raise ValueError('Control range')
        self.controls[symbol].value = value
    def run(self, count=None):
        self.d.run(self.handle, self.quantum if count is None else count)
    def knob_target(self,symbol,position):
        if symbol not in PANEL_KNOBS or not self.knob_function: raise ValueError('Panel response unavailable')
        law=2 if symbol=='pitch' else 1 if symbol.endswith('_amount') else 0
        return self.knob_function(law,position)
    def knob_position(self,symbol,value,enabled):
        p=next(p for p in self.spec if p['symbol']==symbol)
        if not enabled or symbol not in PANEL_KNOBS:return (value-p['min'])/(p['max']-p['min'])
        if symbol not in ('pitch',)+PANEL_KNOBS[5:9]:return max(0,min(1,value))
        if value<=p['min']:return 0.
        if value>=p['max']:return 1.
        # Find both edges of an exact plateau; restore its centre without
        # quantizing any saved semitone/attenuation target back through the law.
        def bound(strict):
            lo,hi=0,65536
            while lo<hi:
                mid=(lo+hi)//2;v=self.knob_target(symbol,mid/65536)
                if (v>value if strict else v>=value):hi=mid
                else:lo=mid+1
            return lo
        first,last=bound(False),bound(True)
        return min(1,((first+last-1)/2 if last>first else first)/65536)
    def map_uri(self, handle, uri):
        if uri not in self.urids: self.urids[uri]=len(self.urids)+1
        return self.urids[uri]
    def state_interface(self):
        address=self.d.extension(b'http://lv2plug.in/ns/ext/state#interface') if self.d.extension else 0
        if not address: raise ValueError('Plugin has no saved-buffer interface')
        return C.cast(address,C.POINTER(StateInterface)).contents
    def save_state(self):
        state={}
        @Store
        def store(handle,key,data,size,kind,flags):
            uri=next(k for k,v in self.urids.items() if v==key).decode()
            type_uri=next(k for k,v in self.urids.items() if v==kind).decode()
            state[uri]=(C.string_at(data,size),type_uri,flags)
            return 0
        result=self.state_interface().save(self.handle,store,None,0,None)
        if result: raise ValueError('Plugin state save failed: '+str(result))
        return state
    def restore_state(self, state, check=True):
        memory={}
        for uri,(data,kind,flags) in state.items():
            memory[self.map_uri(None,uri.encode())]=(C.create_string_buffer(data),len(data),self.map_uri(None,kind.encode()),flags)
        @Retrieve
        def retrieve(handle,key,size,kind,flags):
            if key not in memory: return None
            data,n,t,f=memory[key];size[0]=n;kind[0]=t;flags[0]=f
            return C.addressof(data)
        result=self.state_interface().restore(self.handle,retrieve,None,0,None)
        if result and check: raise ValueError('Plugin state restore failed: '+str(result))
        return result
    def close(self):
        if self.handle: self.d.cleanup(self.handle); self.handle = None
