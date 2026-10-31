// Copyright 2026 Beebo / Hector Lab contributors. SPDX-License-Identifier: MIT
// Jack routing after the original stereo mix; no change to grains or feedback.
#pragma once
#include "rate_converter.h"

namespace mala {
class OutputRouting {
 public:
  void Reset() {
    std::fill(std::begin(gate_delay_), std::end(gate_delay_), 0.f);
    cursor_ = 0;
    gate_mode_ = false;
  }
  void Process(beads::FloatFrame* native, unsigned n, RateConverter& converter,
      beads::FloatFrame* out, bool gate_mode, bool normalize, unsigned connections) {
    if (gate_mode != gate_mode_) {
      // Keep left audio/reverb running; no stale right audio or trigger tail
      // should leak into the newly selected signal type.
      converter.ResetRight();
      std::fill(std::begin(gate_delay_), std::end(gate_delay_), 0.f);
      cursor_ = 0;
      gate_mode_ = gate_mode;
    }
    bool gates[12]{};
    if (gate_mode) for (unsigned i = 0; i < n; ++i) {
      // The source writes -0.8 for a high trigger; its analog DAC stage
      // inverts polarity. Expose +0.8 digital logic, without a volts claim.
      gates[i] = native[i].r < -.4f;
      native[i].r = 0.f;
    }
    converter.Process(native, n, out);
    const unsigned delay = converter.delay_input_frames() * 12 / n;
    for (unsigned i = 0; i < 12; ++i) {
      if (gate_mode) {
        // Hold native logic levels at 48 kHz, delayed to the audio output
        // filter's group delay. Avoid FIR ringing or invented threshold edges.
        const float gate = gates[i * n / 12] ? .8f : 0.f;
        if (delay) {
          out[i].r = gate_delay_[cursor_];
          gate_delay_[cursor_] = gate;
          cursor_ = (cursor_ + 1) % delay;
        } else out[i].r = gate;
      }
      // Equal 1k output resistors join L/R when the R jack is empty.
      // Apply this after gate substitution, including the original L bleed.
      if (normalize && !(connections & 2)) out[i].l = .5f * (out[i].l + out[i].r);
    }
  }
 private:
  float gate_delay_[96]{};
  unsigned cursor_ = 0;
  bool gate_mode_ = false;
};
}
