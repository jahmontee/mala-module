#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Interaction checks against the real QML and bridge, using numeric host state."""
import math
import time
from PySide2.QtCore import QEvent, QPoint, QPointF, Qt
from PySide2.QtGui import QMouseEvent, QWheelEvent


def check(app, window, hub, effects, knobs, stack, panel, find, click, settle, screenshot):
    name='/main/mala1'
    controller=hub.bridge(name)
    original={s:c.value for s,c in effects[name]['controls'].items()}
    original_outputs={s:c.value for s,c in effects[name]['broadcast_ports'].items()}
    other={s:c.value for s,c in effects['/main/mala2']['controls'].items()}
    symbols=['feedback','mix','reverb','time','density','pitch','size','shape',
             'time_amount','size_amount','shape_amount','pitch_amount']
    targets_on_panel=[find('knob_touch_'+s) for s in symbols]
    targets_on_panel += [find(s) for s in ['freeze_button','seed_button','latch_button',
        'quality_selector','mono_checkbox','assignment_button']]
    rectangles=[]
    for target in targets_on_panel:
        p=target.mapToScene(QPointF(0,0))
        rect=(p.x(),p.y(),target.width(),target.height())
        assert rect[0]>=0 and rect[1]>=0 and rect[0]+rect[2]<=1280 and rect[1]+rect[3]<=656,target.objectName()
        for other_name,other_rect in rectangles:
            assert (rect[0]+rect[2]<=other_rect[0] or other_rect[0]+other_rect[2]<=rect[0] or
                    rect[1]+rect[3]<=other_rect[1] or other_rect[1]+other_rect[3]<=rect[1]),(target.objectName(),other_name,'overlapping touch areas')
        rectangles.append((target.objectName(),rect))

    # Check the rendered geometry of the requested alignments.
    for symbol in ['feedback','mix','reverb']:
        face=find('face_'+symbol);label=find('title_'+symbol)
        assert abs(face.mapToScene(QPointF(0,face.height()/2)).y()-label.mapToScene(QPointF(0,label.height()/2)).y())<.01
    for symbol,left,right in [('size',376,634),('shape',634,892)]:
        face=find('face_'+symbol+'_amount');title=find('title_'+symbol+'_amount')
        for item in [face,title]:
            assert abs(item.mapToScene(QPointF(item.width()/2,0)).x()-(left+right)/2)<.01,(symbol,'divider centering')
    assignment=find('assignment_button');mono=find('mono_checkbox')
    assert abs(assignment.mapToScene(QPointF(0,0)).x()-mono.mapToScene(QPointF(0,0)).x())<.01
    assert mono.mapToScene(QPointF(0,0)).y()>assignment.mapToScene(QPointF(0,assignment.height())).y()
    assert mono.width()==assignment.width()
    buttons=[find(n+'_button') for n in ['freeze','seed','latch']]
    for button,symbol in zip(buttons,['feedback','mix','reverb']):
        assert button.property('diameter')==67 and button.width()==200 and button.height()==76
        assert button.property('x')==buttons[0].property('x')
        switch_face=find(button.objectName()+'_face');knob_face=find('face_'+symbol)
        assert abs(switch_face.mapToScene(QPointF(0,switch_face.height()/2)).y()-knob_face.mapToScene(QPointF(0,knob_face.height()/2)).y())<.01
    caption=find('size_mode_caption');title=find('title_size')
    gap=caption.mapToScene(QPointF(0,0)).y()-title.mapToScene(QPointF(0,title.height())).y()
    assert 2<=gap<=8,('Size caption gap',gap)

    def value(symbol, value):
        effects[name]['controls'][symbol].update(value)
        controller.sync();settle()

    def output(symbol, value):
        effects[name]['broadcast_ports'][symbol].update(value)
        controller.sync();settle()

    value('mono',1)
    output('active_synth',1)
    status=find('mode_status')
    status_top=status.mapToScene(QPointF(0,0))
    mono_top=mono.mapToScene(QPointF(0,0))
    assert status.property('visible') and status.property('text')=='WAVETABLE\n48 kHz · 16-bit'
    assert 0<status_top.y()-mono_top.y()-mono.height()<=12
    assert mono_top.x()<=status_top.x() and status_top.x()+status.width()<=mono_top.x()+mono.width()
    assert status.property('horizontalAlignment')==Qt.AlignHCenter
    time_title=find('title_time_amount')
    time_face=find('face_time_amount')
    group_center_y=(mono_top.y()+status.mapToScene(QPointF(0,status.height())).y())/2
    assert time_title.mapToScene(QPointF(0,time_title.height())).y()<=group_center_y<=time_face.mapToScene(QPointF(0,0)).y()
    screenshot('mala-v2-mono-buffer-status.png')
    output('active_synth',original_outputs['active_synth'])
    value('mono',original['mono'])

    def send(kind, point, button, buttons):
        app.sendEvent(window,QMouseEvent(kind,point,button,buttons,Qt.NoModifier))
        app.processEvents()

    def drag(symbol, dy, dx=0):
        item=find('knob_touch_'+symbol)
        p=item.mapToScene(QPointF(item.width()/2,item.height()/2))
        q=QPointF(p.x()+dx,p.y()+dy)
        send(QEvent.MouseButtonPress,p,Qt.LeftButton,Qt.LeftButton)
        send(QEvent.MouseMove,q,Qt.NoButton,Qt.LeftButton)
        send(QEvent.MouseButtonRelease,q,Qt.LeftButton,Qt.NoButton)
        settle()

    def wheel(symbol, delta):
        item=find('knob_touch_'+symbol)
        p=item.mapToScene(QPointF(item.width()/2,item.height()/2))
        event=QWheelEvent(p,p,QPoint(),QPoint(0,delta),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
        app.sendEvent(window,event);settle()

    # Echo Field gesture: only vertical travel, 160 px/range, 1% steps.
    value('panel_response',0)
    for symbol in symbols:
        c=effects[name]['controls'][symbol]
        low,high=c.spec['min'],c.spec['max']
        midpoint=(low+high)/2
        value(symbol,midpoint)
        before=len(knobs.parameters)
        click(find('knob_touch_'+symbol))
        assert len(knobs.parameters)==before,(symbol,'touch changed the value')
        drag(symbol,-16)
        assert math.isclose(c.value,low+.6*(high-low),abs_tol=1e-5),(symbol,'up',c.value)
        drag(symbol,16)
        assert math.isclose(c.value,midpoint,abs_tol=1e-5),(symbol,'down',c.value)
        drag(symbol,0,60)
        assert math.isclose(c.value,midpoint,abs_tol=1e-5),(symbol,'horizontal',c.value)
        wheel(symbol,360)
        assert math.isclose(c.value,low+.51*(high-low),abs_tol=1e-5),(symbol,'wheel',c.value)
        wheel(symbol,-120)
        assert math.isclose(c.value,midpoint,abs_tol=1e-5),(symbol,'reverse wheel',c.value)
        drag(symbol,-80)
        assert math.isclose(c.value,high,abs_tol=1e-5),(symbol,'upper bound',c.value)
        drag(symbol,160)
        assert math.isclose(c.value,low,abs_tol=1e-5),(symbol,'lower bound',c.value)
        assert find('value_'+symbol).property('text')==format(c.value,'.2f')

    # Echo Field double-tap resets to minimum, including bipolar controls.
    for symbol in ['feedback','pitch','time_amount']:
        c=effects[name]['controls'][symbol]
        value(symbol,(c.spec['min']+c.spec['max'])/2)
        item=find('knob_touch_'+symbol)
        p=item.mapToScene(QPointF(item.width()/2,item.height()/2))
        send(QEvent.MouseButtonPress,p,Qt.LeftButton,Qt.LeftButton)
        send(QEvent.MouseButtonRelease,p,Qt.LeftButton,Qt.NoButton)
        send(QEvent.MouseButtonDblClick,p,Qt.LeftButton,Qt.LeftButton)
        send(QEvent.MouseButtonRelease,p,Qt.LeftButton,Qt.NoButton);settle()
        assert c.value==c.spec['min'],(symbol,'double tap',c.value)

    # Native Beads lookup remains authoritative for pitch and attenurandomizers.
    value('panel_response',1)
    for symbol in ['pitch','time_amount','size_amount','shape_amount','pitch_amount']:
        value(symbol,hub.response.target(symbol,.5))
        start=controller.positions[symbol]
        expected_position=max(0,min(1,math.floor((start+.1)*100+.5)/100))
        drag(symbol,-16)
        expected=hub.response.target(symbol,expected_position)
        assert math.isclose(effects[name]['controls'][symbol].value,expected,abs_tol=1e-5),(symbol,expected)
        assert math.isclose(find('pointer_'+symbol).property('rotation'),-135+270*expected_position,abs_tol=1e-4)
        # Incoming host/MIDI changes must move the pointer, with no echoed write.
        before=len(knobs.parameters)
        value(symbol,hub.response.target(symbol,.8))
        assert len(knobs.parameters)==before
        assert math.isclose(find('pointer_'+symbol).property('rotation'),-135+270*controller.positions[symbol],abs_tol=1e-4)

    for symbol in ['size','shape']:
        knob=find(symbol+'_parameter')
        assert knob.property('labelPlacement')=='below'
        assert knob.property('labelY')>=knob.property('diameter')
    for position,caption in [(.2,'REVERSE'),(.6,'FORWARD'),(.99,'FORWARD'),(1,'∞  DELAY')]:
        value('size',position)
        assert find('size_mode_caption').property('text')==caption
    output('active_synth',1)
    for position in [.2,1]:
        value('size',position)
        assert find('size_mode_caption').property('text')=='GRAIN DURATION'
    output('active_synth',0)
    # Canonical landmarks from the vendored GrainEnvelope source, with real renders.
    envelope=find('shape_envelope_preview');envelopes=[]
    for index,(shape,a,s,r) in enumerate([(0,0,1,0),(1/3,0,0,1),(2/3,.5,0,.5),(1,1,0,0)]):
        value('shape',shape)
        assert math.isclose(envelope.property('shapeValue'),shape,abs_tol=1e-6)
        for property_name,expected in [('attackFraction',a),('sustainFraction',s),('releaseFraction',r)]:
            assert math.isclose(envelope.property(property_name),expected,abs_tol=1e-6),(shape,property_name)
        image=screenshot('shape-envelope-'+str(index)+'.png')
        envelopes.append(image.copy(921,379,134,48))
    assert all(envelopes[i]!=envelopes[j] for i in range(4) for j in range(i+1,4))
    value('shape',.6)
    assert math.isclose(envelope.property('attackFraction'),.256,abs_tol=1e-6)

    value('freeze',0)
    effects[name]['broadcast_ports']['active_freeze'].update(0);controller.sync();settle()
    assert not find('freeze_button').property('yellowLit')
    click(find('freeze_button'))
    assert effects[name]['controls']['freeze'].value==1
    assert not find('freeze_button').property('highlighted'),'Wait for active Freeze acknowledgement'
    assert not find('freeze_button').property('yellowLit')
    effects[name]['broadcast_ports']['active_freeze'].update(1);controller.sync();settle()
    assert find('freeze_button').property('highlighted')
    assert find('freeze_button').property('yellowLit')
    click(find('freeze_button'));assert effects[name]['controls']['freeze'].value==0
    effects[name]['broadcast_ports']['active_freeze'].update(0);controller.sync();settle()
    assert not find('freeze_button').property('yellowLit')
    # An external Freeze hold also lights the button even with its manual value off.
    output('active_freeze',1);assert find('freeze_button').property('yellowLit')
    output('active_freeze',0);assert not find('freeze_button').property('yellowLit')

    value('seed',0)
    seed=find('seed_button');assert not seed.property('yellowLit')
    p=seed.mapToScene(QPointF(seed.width()/2,seed.height()/2))
    send(QEvent.MouseButtonPress,p,Qt.LeftButton,Qt.LeftButton);settle()
    assert seed.property('yellowLit')
    send(QEvent.MouseButtonRelease,p,Qt.LeftButton,Qt.NoButton);settle()
    assert not seed.property('yellowLit')
    assert [row[1:] for row in knobs.parameters[-2:]]==[['seed',1.0],['seed',0.0]]
    click(find('latch_button'));assert controller.seedLatched and find('latch_button').property('yellowLit') and not seed.property('yellowLit')
    click(find('latch_button'));assert not controller.seedLatched and not seed.property('yellowLit')
    # Exercise the actual bridge's four-second hold timer through QML press/release.
    seed=find('seed_button')
    p=seed.mapToScene(QPointF(seed.width()/2,seed.height()/2))
    send(QEvent.MouseButtonPress,p,Qt.LeftButton,Qt.LeftButton)
    hold_started=time.monotonic();end=hold_started+5
    # Allow event-loop/coarse-timer scheduling, without changing the 4000 ms timer.
    while not controller.seedLatched and time.monotonic()<end:app.processEvents();time.sleep(.002)
    hold_elapsed=time.monotonic()-hold_started
    assert controller.seedLatched,('Seed hold did not latch',controller.seed_down,controller.hold_timer.remainingTime())
    send(QEvent.MouseButtonRelease,p,Qt.LeftButton,Qt.NoButton);settle()
    assert controller.seedLatched,'Releasing a held Seed must keep Latch'
    assert find('latch_button').property('yellowLit') and not seed.property('yellowLit')

    # The center button and LED use requested and active engine state separately.
    quality=find('quality_selector');led=find('quality_led')
    # Qt creates a ComboBox popup lazily on its first real opening.
    before=len(knobs.parameters);click(quality);popup=find('quality_popup')
    assert popup.property('visible') and len(knobs.parameters)==before
    popup.close();settle()
    colors=['#fffdf4','#379cf1','#f5a03c','#e45a9e']
    names=['Bright digital','Cold digital','Sunny tape','Scorched cassette']
    value('quality',3);output('active_quality',3)
    for mode in range(4):
        before=len(knobs.parameters)
        previous_color=led.property('modeColor').name()
        click(quality)
        assert popup.property('visible') and len(knobs.parameters)==before
        assert find('quality_option_'+str(mode)).property('text')==names[mode]
        click(find('quality_option_'+str(mode)))
        assert not popup.property('visible')
        assert effects[name]['controls']['quality'].value==mode
        assert knobs.parameters[before:]==[[name,'quality',float(mode)]]
        assert led.property('modeColor').name()==previous_color,'LED must wait for active engine state'
        before=len(knobs.parameters);output('active_quality',mode)
        assert len(knobs.parameters)==before,'An engine acknowledgement must not echo a write'
        assert led.property('modeColor').name()==colors[mode] and led.property('modeName')==names[mode]
        if mode==1:
            click(quality);screenshot('mala-v2-quality-menu.png');popup.close();settle()

    # Dismissal outside the menu must not press the underlying Freeze button.
    before=len(knobs.parameters);click(quality);click(find('freeze_button'))
    assert not popup.property('visible') and len(knobs.parameters)==before

    value('quality',0);output('active_quality',0)
    value('freeze',1);output('active_freeze',1)
    click(quality);click(find('quality_option_3'))
    assert effects[name]['controls']['quality'].value==3
    assert led.property('modeColor').name()==colors[0]
    assert 'Scorched cassette' in find('mode_status').property('text')
    before=len(knobs.parameters)
    output('active_freeze',0)
    assert led.property('modeColor').name()==colors[0],'Releasing Freeze alone is not an active-quality acknowledgement'
    output('active_quality',3)
    assert led.property('modeColor').name()==colors[3] and len(knobs.parameters)==before
    value('freeze',0)
    # Host/MIDI value changes update the selector and active LED without opening it.
    value('quality',1);output('active_quality',1)
    assert quality.property('currentIndex')==1 and led.property('modeColor').name()==colors[1]
    assert not popup.property('visible')
    click(find('mono_checkbox'));assert effects[name]['controls']['mono'].value==1
    click(find('assignment_button'))
    assignment=find('mala_assignment_dialog');assert assignment.property('visible')
    screenshot('mala-v2-cv-assignment.png');assignment.close();settle()
    click(find('mala_settings_button'))
    settings=find('mala_settings_dialog');assert settings.property('visible')
    click(find('mala_help_button'));help_dialog=find('mala_mode_help');assert help_dialog.property('visible')
    screenshot('mala-v2-help.png');help_dialog.close();settings.close();settle()

    # Every mapping target opens the stock host mapping route without a value write.
    targets=[('knob_touch_'+s,s) for s in symbols]+[
        ('freeze_button','freeze'),('seed_button','seed'),('latch_button','seed'),
        ('midi_target_quality','quality'),('midi_target_mono','mono')]
    for target,symbol in targets:
        before=len(knobs.parameters)
        panel.setProperty('midiMapping',True);settle()
        click(find(target))
        assert len(knobs.parameters)==before,('MIDI selection wrote a value',symbol)
        assert not panel.property('midiMapping')
        assert knobs.selected[-1]==[name,symbol]
        if symbol=='quality':assert not popup.property('visible')
        path,props=stack.calls[-1]
        assert path.endswith('/More.qml') and props==dict(current_effect=name,row_param=symbol,v_type=controller.midiType(symbol))

    # A mapping gesture can never edit a knob, including wheel or double tap.
    panel.setProperty('midiMapping',True);settle()
    before=len(knobs.parameters);wheel('pitch',120)
    assert len(knobs.parameters)==before
    target=find('knob_touch_pitch');p=target.mapToScene(QPointF(target.width()/2,target.height()/2))
    send(QEvent.MouseButtonDblClick,p,Qt.LeftButton,Qt.LeftButton)
    send(QEvent.MouseButtonRelease,p,Qt.LeftButton,Qt.NoButton);settle()
    assert len(knobs.parameters)==before
    panel.setProperty('midiMapping',False);settle()
    assert other=={s:c.value for s,c in effects['/main/mala2']['controls'].items()}

    # Leave a clean, representative preview after the interaction checks.
    for symbol,v in original.items():effects[name]['controls'][symbol].update(v)
    for symbol,v in original_outputs.items():effects[name]['broadcast_ports'][symbol].update(v)
    controller.sync();settle()
    window.activeFocusItem().setFocus(False) if window.activeFocusItem() else None
    send(QEvent.MouseMove,QPointF(5,710),Qt.NoButton,Qt.NoButton);settle()
    screenshot('mala-v2-preview.png')
    # Proof of the yellow face fill as rendered pixels, not just a state property.
    value('freeze',1);output('active_freeze',1);value('seed',1)
    lit_image=screenshot('mala-v2-freeze-seed-yellow.png')
    for target in ['freeze_button','seed_button']:
        button=find(target)
        assert button.property('yellowLit')
        point=button.mapToScene(QPointF(button.property('diameter')/2,button.height()/2))
        color=lit_image.pixelColor(round(point.x()),round(point.y()))
        assert color.red()>180 and color.green()>150 and color.blue()<color.red()-40,(target,color.name())
    for symbol,v in original.items():effects[name]['controls'][symbol].update(v)
    for symbol,v in original_outputs.items():effects[name]['broadcast_ports'][symbol].update(v)
    controller.sync();settle()
    return dict(knobs_checked=len(symbols),side_labels_centered=True,lower_size_shape_centered_between_dividers=True,mono_below_cv_assignment=True,right_buttons_aligned_with_mix_knobs=True,three_right_buttons_same_size_and_spacing=True,size_caption_gap_pixels=gap,echo_field_vertical_travel_pixels=160,
        echo_field_steps_and_wheel=True,echo_field_double_tap_minimum=True,
        main_touch_targets_no_overlap=True,no_touch_jump=True,no_horizontal_adjustment=True,
        bounds_and_value_readback=True,native_beads_response_preserved=True,
        external_parameter_updates=True,freeze_backend_acknowledgement=True,
        seed_momentary_and_actual_four_second_hold=True,latch=True,quality_popup=True,
        seed_hold_elapsed_seconds=round(hold_elapsed,3),
        quality_menu_choices_checked=4,quality_led_colors_checked=colors,
        quality_led_waits_for_active_engine_state=True,quality_queued_while_frozen=True,
        quality_host_updates=True,quality_menu_outside_press_dismissal=True,
        size_and_shape_labels_below_knobs=True,size_region_and_synth_captions=True,
        shape_envelope_landmarks_and_distinct_renders=4,
        freeze_acknowledged_and_external_hold_yellow=True,
        seed_press_yellow_latch_separate_indicator=True,yellow_button_face_pixels_verified=True,
        mono=True,cv_assignment=True,settings_and_help=True,midi_targets_checked=len(targets),
        mapping_does_not_change_parameters=True,second_instance_unchanged=True)
