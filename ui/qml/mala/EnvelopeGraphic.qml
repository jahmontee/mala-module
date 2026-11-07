// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.11

// Normalized panel-envelope contour from Beads' GrainEnvelope::Start/Render.
// This is a shape guide, not an audio waveform or per-grain CV/randomness meter.
Item {
    id: envelope
    property real shapeValue: 0
    property color ink: "#37322d"
    property real strokeWidth: 1.7
    readonly property real normalizedShape: Math.max(0, Math.min(1, shapeValue))
    readonly property real sustainFraction: Math.max(1 - 3 * normalizedShape, 0)
    readonly property real attackFraction: {
        var a=(normalizedShape - 1/3) * 1.5;
        return a < 0 ? 0 : a < .5 ? 4*a*a*a : a;
    }
    readonly property real releaseFraction: (1-attackFraction) * (1-sustainFraction)
    readonly property real smoothness: attackFraction < .5 ? 2*attackFraction : 2-2*attackFraction
    function smoothStep(t) { return t*t*(3-2*t); }
    function envelopeAt(phase) {
        if (phase < 0 || phase > 1) return 0;
        var t, base;
        if (attackFraction > 0 && phase <= attackFraction) {
            t=phase/attackFraction;
            return t + (smoothStep(t)-t)*smoothness;
        }
        if (phase <= attackFraction + sustainFraction) return 1;
        if (releaseFraction <= 0) return 0;
        t=Math.max(0, 1-(phase-attackFraction-sustainFraction)/releaseFraction);
        base=t*t*t*t;
        return base + (smoothStep(t)-base)*smoothness;
    }
    onShapeValueChanged: if (curve) curve.requestPaint()
    onInkChanged: if (curve) curve.requestPaint()
    Canvas {
        id: curve
        anchors.fill: parent
        onPaint: {
            var c=getContext("2d");c.clearRect(0,0,width,height);c.save();
            c.strokeStyle=envelope.ink;c.lineWidth=envelope.strokeWidth;c.lineJoin="round";
            c.beginPath();c.moveTo(2,height-2);
            for(var i=0;i<=128;i++) {
                c.lineTo(2+(width-4)*i/128,2+(height-4)*(1-envelope.envelopeAt(i/128)));
            }
            c.lineTo(width-2,height-2);c.stroke();c.restore();
        }
    }
}
