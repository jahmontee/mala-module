// Copyright 2026 Beebo / Hector Lab contributors. SPDX-License-Identifier: MIT
// Causal rational polyphase FIR. Only 12-frame, 48 kHz / 4 kHz blocks enter
// the adapter; their 8/6-frame native equivalents keep every phase integral.
#pragma once
#include "beads/dsp/frame.h"
#include <algorithm>
#include <cmath>
#include <iterator>

namespace mala {
constexpr unsigned kHostBlock = 12;
constexpr unsigned kFilterLength = 193;
class RateConverter {
 public:
  void Init(unsigned input_rate, unsigned output_rate) {
    const unsigned divisor = gcd(input_rate, output_rate);
    up_ = output_rate / divisor;
    down_ = input_rate / divisor;
    bypass_ = input_rate == output_rate;
    const double pi = 3.14159265358979323846;
    const double cutoff = .5 * std::min(input_rate, output_rate)
        - 1000.;
    const double normalized = cutoff / (double(input_rate) * up_);
    for (unsigned i = 0; i < kFilterLength; ++i) {
      const double x = double(i) - (kFilterLength - 1) / 2.;
      const double sinc = x ? std::sin(2. * pi * normalized * x) / (pi * x)
                           : 2. * normalized;
      const double window = .42 - .5 * std::cos(2. * pi * i / (kFilterLength - 1))
                                  + .08 * std::cos(4. * pi * i / (kFilterLength - 1));
      coefficients_[i] = float(sinc * window);
    }
    // Each interpolation phase has unity DC gain, including finite-FIR edges.
    for (unsigned phase = 0; phase < up_; ++phase) {
      double sum = 0;
      for (unsigned i = phase; i < kFilterLength; i += up_) sum += coefficients_[i];
      for (unsigned i = phase; i < kFilterLength; i += up_) coefficients_[i] /= sum;
    }
    Reset();
  }
  void Reset() {
    std::fill(std::begin(history_), std::end(history_), beads::FloatFrame{0, 0});
    head_ = 0;
  }
  unsigned Process(const beads::FloatFrame* input, unsigned size, beads::FloatFrame* output) {
    if (bypass_) { std::copy(input, input + size, output); return size; }
    // The caller always supplies a complete rational cycle.
    const unsigned count = size * up_ / down_;
    unsigned consumed = 0;
    for (unsigned j = 0; j < count; ++j) {
      const unsigned time = j * down_;
      while (consumed <= time / up_) Push(input[consumed++]);
      beads::FloatFrame value{0, 0};
      unsigned age = 0;
      for (unsigned tap = time % up_; tap < kFilterLength; tap += up_, ++age) {
        const auto& sample = history_[(head_ + kFilterLength - 1 - age) % kFilterLength];
        value.l += coefficients_[tap] * sample.l;
        value.r += coefficients_[tap] * sample.r;
      }
      output[j] = value;
    }
    while (consumed < size) Push(input[consumed++]);
    return count;
  }
  unsigned delay_input_frames() const { return bypass_ ? 0 : (kFilterLength - 1) / (2 * up_); }
  void ResetRight() { for (auto& frame : history_) frame.r = 0.f; }
  float coefficient(unsigned i) const { return coefficients_[i]; }
 private:
  static unsigned gcd(unsigned a, unsigned b) { while (b) { unsigned r = a % b; a = b; b = r; } return a; }
  void Push(beads::FloatFrame value) { history_[head_] = value; head_ = (head_ + 1) % kFilterLength; }
  beads::FloatFrame history_[kFilterLength];
  float coefficients_[kFilterLength];
  unsigned up_, down_, head_;
  bool bypass_;
};
}
