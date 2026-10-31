#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real full editor QML and Mala bridge; host engine state is a numeric fixture."""
import json, sys, time
from pathlib import Path
from PySide2.QtCore import QObject,Property,Signal,Slot,QUrl,QPointF,Qt,QEvent
from PySide2.QtGui import QGuiApplication,QMouseEvent
from PySide2.QtQml import QQmlApplicationEngine
from PySide2.QtQuick import QQuickWindow
import argparse,shutil
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'build/qt-check')
OUT=parser.parse_args().output.resolve();OUT.mkdir(parents=True,exist_ok=True)
FIXTURE=OUT/'fixture';FIXTURE.mkdir(exist_ok=True)
shutil.copytree(ROOT/'ui/qml/mala',FIXTURE/'mala',dirs_exist_ok=True)
if __import__('platform').machine() not in ['aarch64','arm64']:
    for p in (FIXTURE/'mala').glob('*.qml'):
        p.write_text(p.read_text().replace('/usr/lib/aarch64-linux-gnu/','/usr/lib/x86_64-linux-gnu/'))
(FIXTURE/'Harness.qml').write_text('''import QtQuick 2.11
import QtQuick.Controls 2.4
import QtQuick.Controls.Material 2.4
import "mala"
ApplicationWindow {
 width:1280;height:720;visible:true
 flags:Qt.Tool | Qt.FramelessWindowHint | Qt.BypassWindowManagerHint
 Material.theme:Material.Dark;Material.background:"#10191e"
 FirmwarePanel { objectName:"panel";effect_id:"/main/mala1" }
}
''')
sys.path.insert(0,str(ROOT/'ui'))
from mala_407 import MalaHub,Control,SPEC,INPUTS

app=QGuiApplication([])
def number(v):
    return Control(dict(name='value',default=v,min=0,max=100),None)
effects={}
for name in ['/main/mala1','/main/mala2']:
    effects[name]=dict(effect_type='mala',enabled=number(1),
        controls={s:Control(p,None) for s,p in SPEC.items() if s in INPUTS},
        broadcast_ports={s:Control(p,None) for s,p in SPEC.items() if s not in INPUTS})
class Knobs(QObject):
    def __init__(self):super().__init__();self.calls=[];self.parameters=[]
    @Slot(str,bool)
    def set_bypass(self,name,enabled):self.calls.append([name,enabled])
    def ui_knob_change(self,name,symbol,value):
        self.parameters.append([name,symbol,value]);effects[name]['controls'][symbol].update(value)
class Response:
    def position(self,s,v,enabled):return (v-SPEC[s]['min'])/(SPEC[s]['max']-SPEC[s]['min'])
class Transport:
    def set_broadcast(self,*args):pass
class Loading:value=False
knobs=Knobs();hub=MalaHub(effects,{},knobs,Transport(),Loading(),Response())
hub.created('/main/mala1')
class Selected(QObject):
    def __init__(self):super().__init__();self.backs=0
    @Slot()
    def back_action(self):self.backs+=1
selected=Selected()
class Patch(QObject):
    selected_effect=Property(QObject,lambda s:selected,constant=True)
    in_spotlight=Property(bool,lambda s:True,constant=True)
patch=Patch()
engine=QQmlApplicationEngine();warnings=[]
engine.warnings.connect(lambda rows:warnings.extend(e.toString() for e in rows))
ctx=engine.rootContext()
for k,v in dict(malaHub=hub,currentEffects=effects,knobs=knobs,patch_single=patch,dspLoad=number(.37)).items():ctx.setContextProperty(k,v)
engine.load(QUrl.fromLocalFile(str(FIXTURE/'Harness.qml')))
assert engine.rootObjects(),warnings
w=engine.rootObjects()[0]
def settle():
    end=time.monotonic()+.35
    while time.monotonic()<end:app.processEvents();time.sleep(.002)
def find(name):
    item=w.findChild(QObject,name);assert item,name;return item
def click_at(x,y):
    p=QPointF(x,y)
    for event,buttons in [(QEvent.MouseButtonPress,Qt.LeftButton),(QEvent.MouseButtonRelease,Qt.NoButton)]:
        app.sendEvent(w,QMouseEvent(event,p,Qt.LeftButton,buttons,Qt.NoModifier))
        app.processEvents()
    settle()
def click(item):
    click_at(item.property('x')+item.property('width')/2,item.property('y')+item.property('height')/2)
settle()
panel=find('panel');back=find('mala_firmware_back');settings=find('mala_settings_button');bypass=find('mala_firmware_bypass')
items=[back,settings,find('mala_footer_status'),find('mala_cpu_meter'),find('mala_map_midi'),bypass]
assert all(a.property('x')+a.property('width')<=b.property('x') for a,b in zip(items,items[1:])),[(i.objectName(),i.property('x'),i.property('width')) for i in items]
assert back.property('x')==24 and bypass.property('x')==1100
assert not knobs.calls and not knobs.parameters and not bypass.property('highlighted')
assert w.grabWindow().save(str(OUT/'mala-footer-active.png'))
click(bypass)
assert knobs.calls==[['/main/mala1',False]]
assert not bypass.property('highlighted'),'Highlight must wait for backend acknowledgement'
effects['/main/mala1']['enabled'].update(0);settle()
assert bypass.property('highlighted')
assert w.grabWindow().save(str(OUT/'mala-footer-bypassed.png'))
click(bypass);assert knobs.calls[-1]==['/main/mala1',True]
effects['/main/mala1']['enabled'].update(1);settle();assert not bypass.property('highlighted')
# Changes made through the patch screen must remain reflected in this editor.
effects['/main/mala1']['enabled'].update(0);settle();assert bypass.property('highlighted')
effects['/main/mala1']['enabled'].update(1);settle();assert not bypass.property('highlighted')
assert effects['/main/mala2']['enabled'].value==1
count=len(knobs.calls)
click(settings);dialog=find('mala_settings_dialog');assert dialog.property('visible');dialog.close();settle()
panel.setProperty('midiMapping',True);click(back);assert selected.backs==1 and not panel.property('midiMapping')
assert len(knobs.calls)==count and not knobs.parameters
# A retired/missing module disables the control instead of issuing stale writes.
ctx.setContextProperty('currentEffects',{});settle();assert not bypass.property('enabled')
click_at(1175,661);assert len(knobs.calls)==count
ctx.setContextProperty('currentEffects',effects);settle()
assert not warnings,warnings
report=dict(success=True,full_component_loaded=True,layout_no_overlap=True,
    bypass_clicks_and_backend_acknowledgement=True,external_state_updates=True,
    second_module_unchanged=True,spotlight_module_bypass=True,settings_and_back=True,
    stale_module_disabled=True,parameter_writes=knobs.parameters,warnings=warnings,
    fixture_limitation='Numeric host state and linear knob lookup; no audio or physical touch test.',
    geometry=[dict(name=i.objectName(),x=i.property('x'),width=i.property('width')) for i in items])
(OUT/'ui-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
w.close();w.deleteLater();app.sendPostedEvents(None,QEvent.DeferredDelete)
