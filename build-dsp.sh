#!/bin/sh
set -eu
case "$0" in
  */*) cd "${0%/*}" ;;
esac
exec "${CXX:-aarch64-linux-gnu-g++-12}" -std=gnu++17 -march=armv8-a -mtune=generic -O2 -fno-fast-math -DTEST -include cstdio -fPIC -fvisibility=hidden -shared -Ibuild-support/overlay -Ivendor/lv2-headers -Ivendor src/dsp/mala.cpp vendor/beads/dsp/processor.cc vendor/beads/dsp/mu_law.cc vendor/beads/dsp/delay_clock.cc vendor/beads/dsp/delay_controller.cc vendor/beads/dsp/trigger_generator.cc vendor/beads/dsp/synth.cc vendor/beads/resources.cc vendor/stmlib/dsp/units.cc vendor/beads/gain_control.cc build-support/overlay/stmlib/utils/random.cc -o module.so
