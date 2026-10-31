// Copyright 2026 Beebo / Hector Lab contributors. SPDX-License-Identifier: MIT
// Portable panel response; existing LV2 controls remain in their original units.
#pragma once
#include "beads/pot_channel.h"
#include <algorithm>
#include <cmath>

namespace mala {
constexpr unsigned kPanelKnobs = 12;  // Existing ports Time through Reverb.
inline float KnobTarget(unsigned law, float position) {
  if (!std::isfinite(position) || law > 2) return 0.f;
  const unsigned raw = std::min(65535u, unsigned(std::max(0.f,std::min(1.f,position))*65536.f));
  beads::PotChannel channel;
  // The UI supplies the original static law. Audio applies its 4 kHz filter
  // separately so semitone/attenuation port values never change meaning.
  channel.Init(beads::PotChannel::Law(law),1.f,0.f);
  channel.Process(uint16_t(raw));
  return channel.value();
}
class PanelResponse {
 public:
  PanelResponse() { time_hysteresis_.Init(.001f); }
  void Process(const float* target, bool enabled) {
    for (unsigned i=0;i<kPanelKnobs;++i) {
      if (enabled) lp_[i] += .05f*(target[i]-lp_[i]);
      else lp_[i]=target[i];
      value_[i]=lp_[i];
    }
    // A moving deadband, only on Time, exactly as CvReader::Init specifies.
    value_[0]=time_hysteresis_.Process(lp_[0],enabled ? .001f : 0.f);
  }
  float value(unsigned i) const { return value_[i]; }
 private:
  float lp_[kPanelKnobs]{};
  float value_[kPanelKnobs]{};
  stmlib::HysteresisFilter time_hysteresis_;
};
}
