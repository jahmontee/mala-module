// Copyright 2026 Beebo / Hector Lab contributors. SPDX-License-Identifier: MIT
// The digital codec boundary only; GainControl's source is compiled unchanged.
#pragma once
#include "beads/gain_control.h"
#include <cmath>
#include <cstdint>
#include <limits>

namespace mala {
inline int32_t CodecSample(float value) {
  if (!std::isfinite(value)) return 0;
  // A float rounded to +1 must not be cast to the out-of-range int32 2^31.
  if (value >= 1.f) return std::numeric_limits<int32_t>::max();
  if (value <= -1.f) return std::numeric_limits<int32_t>::min();
  return static_cast<int32_t>(double(value) * 2147483648.0);
}
inline beads::GainControl::SoftClippingMode ClippingMode(unsigned quality) {
  return quality == 3 ? beads::GainControl::SOFT_CLIPPING_MODE_ON
      : quality == 2 ? beads::GainControl::SOFT_CLIPPING_MODE_DYNAMIC
      : beads::GainControl::SOFT_CLIPPING_MODE_OFF;
}
inline void ProcessInput(beads::GainControl& gain, bool active, uint8_t setting,
                         unsigned connections, beads::FloatFrame* frames, unsigned n) {
  beads::Codec::Frame pcm[12];
  for (unsigned i = 0; i < n; ++i)
    pcm[i] = {CodecSample(frames[i].l), CodecSample(frames[i].r)};
  gain.Process(active, setting, !(connections & 1), !(connections & 2), pcm, frames, n);
}
}  // namespace mala
