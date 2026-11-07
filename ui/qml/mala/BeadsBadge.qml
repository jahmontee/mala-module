// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.11

Rectangle {
    id: badge
    property color accent: "#00b4bd"
    property string symbol: "cloud"
    width: 30; height: 68; radius: width / 2; antialiasing: true
    gradient: Gradient {
        GradientStop { position: 0; color: Qt.lighter(badge.accent, 1.08) }
        GradientStop { position: 1; color: Qt.darker(badge.accent, 1.06) }
    }
    Canvas {
        anchors.centerIn: parent; width: 24; height: 26
        onPaint: {
            var c=getContext("2d");c.clearRect(0,0,width,height);c.save();
            c.strokeStyle="#fffdf4";c.fillStyle="#fffdf4";c.lineWidth=1.8;c.lineJoin="round";c.lineCap="round";
            c.beginPath();
            if(badge.symbol==="cloud") {
                c.moveTo(5,19);c.bezierCurveTo(-1,18,0,11,6,11);c.bezierCurveTo(6,4,16,3,17,10);c.bezierCurveTo(24,9,25,18,19,19);c.stroke();
                for(var i=0;i<5;i++){c.beginPath();c.arc(4+i*4,21,0.8,0,Math.PI*2);c.fill();}
            } else if(badge.symbol==="feedback") {
                // The arc and arrowhead both point counterclockwise.
                c.arc(12,14,8,-Math.PI*.98,-Math.PI*.75,true);c.stroke();
                c.beginPath();c.moveTo(6.4,3.4);c.lineTo(6.25,8.6);c.lineTo(11.5,8.5);c.stroke();
            } else if(badge.symbol==="sun") {
                c.arc(12,16,6,Math.PI,Math.PI*2);c.lineTo(18,17);c.lineTo(6,17);c.stroke();
                for(var j=0;j<7;j++){var a=Math.PI+j*Math.PI/6;c.beginPath();c.arc(12+10*Math.cos(a),16+10*Math.sin(a),0.8,0,Math.PI*2);c.fill();}
            } else if(badge.symbol==="wave") {
                c.moveTo(1,19);c.bezierCurveTo(7,19,6,6,12,6);c.bezierCurveTo(18,6,17,19,23,19);c.stroke();
            } else if(badge.symbol==="random") {
                c.arc(12,14,8,-Math.PI*.52,Math.PI*1.23);c.stroke();c.beginPath();c.moveTo(9,3);c.lineTo(13,6);c.lineTo(9,9);c.stroke();
            } else {
                c.moveTo(3,8);c.lineTo(12,3);c.lineTo(21,8);c.lineTo(21,19);c.lineTo(12,24);c.lineTo(3,19);c.closePath();
                c.moveTo(3,8);c.lineTo(12,13);c.lineTo(21,8);c.moveTo(12,13);c.lineTo(12,24);c.stroke();
                if(badge.symbol==="dice") {
                    [[8,8],[16,8],[7,15],[8,19],[16,16],[17,20]].forEach(function(p){c.beginPath();c.arc(p[0],p[1],1.1,0,Math.PI*2);c.fill();});
                }
            }
            c.restore();
        }
    }
}
