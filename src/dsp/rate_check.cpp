// SPDX-License-Identifier: MIT. Isolated indexing, gain and rejection checks.
#include "rate_converter.h"
#include <vector>
#include <cstdio>
#include <cassert>

int main() {
  const unsigned rates[][2] = {{48000,48000},{48000,32000},{32000,48000},{48000,24000},{24000,48000}};
  std::puts("[");
  for (unsigned r = 0; r < 5; ++r) {
    const unsigned in_rate = rates[r][0], out_rate = rates[r][1];
    const unsigned block = in_rate / 4000, out_block = out_rate / 4000;
    mala::RateConverter converter; converter.Init(in_rate, out_rate);
    std::vector<beads::FloatFrame> input(block * 256), output(out_block * 256);
    for (unsigned i = 0; i < input.size(); ++i) input[i] = {float(int(i * 53 % 139) - 69) / 100.f, float(int(i * 17 % 107) - 53) / 100.f};
    for (unsigned i = 0; i < input.size(); i += block) assert(converter.Process(&input[i], block, &output[i / block * out_block]) == out_block);
    unsigned divisor = in_rate; unsigned b = out_rate;
    while (b) { unsigned tmp = divisor % b; divisor = b; b = tmp; }
    const unsigned up = out_rate / divisor, down = in_rate / divisor;
    double error = 0;
    // Independently evaluate zero insertion -> full FIR convolution -> decimation.
    for (unsigned j = 0; j < output.size(); ++j) {
      beads::FloatFrame expected{0,0};
      if (in_rate == out_rate) expected = input[j];
      else for (unsigned tap = (j * down) % up; tap < mala::kFilterLength; tap += up) {
        const int k = (int(j * down) - int(tap)) / int(up);
        if (int(j * down) < int(tap)) continue;
        expected.l += input[k].l * converter.coefficient(tap);
        expected.r += input[k].r * converter.coefficient(tap);
      }
      error = std::max(error, double(std::fabs(expected.l - output[j].l)));
      error = std::max(error, double(std::fabs(expected.r - output[j].r)));
    }
    assert(error < 2e-6);
    auto amplitude = [&](double hz, double measure_hz) {
      converter.Reset();
      double real = 0, imag = 0;
      const unsigned samples = in_rate / 10, out_samples = out_rate / 10;
      beads::FloatFrame in[12], out[12];
      for (unsigned i = 0; i < samples; i += block) {
        for (unsigned k = 0; k < block; ++k) in[k] = {float(std::cos(6.283185307179586 * hz * (i+k) / in_rate)),0};
        converter.Process(in, block, out);
        for (unsigned k = 0; k < out_block; ++k) {
          const unsigned t = i / block * out_block + k;
          if (t < out_samples / 2) continue;
          const double phase = 6.283185307179586 * measure_hz * t / out_rate;
          real += out[k].l * std::cos(phase); imag -= out[k].l * std::sin(phase);
        }
      }
      return 4. * std::hypot(real, imag) / out_samples;
    };
    const double gain = amplitude(1000,1000); assert(std::fabs(gain - 1) < .001);
    double rejection = 0;
    if (out_rate < in_rate) {
      const double frequency = out_rate == 32000 ? 20000 : 16000;
      rejection = 20 * std::log10(std::max(1e-15, amplitude(frequency, out_rate - frequency)));
      assert(rejection < -65);
    } else if (out_rate > in_rate) {
      const double image = out_rate - (in_rate - 2000);
      rejection = 20 * std::log10(std::max(1e-15, amplitude(2000,image)));
      assert(rejection < -65);
    }
    std::printf("%s{\"input_rate\":%u,\"output_rate\":%u,\"convolution_error\":%.10g,\"passband_gain\":%.9f,\"alias_or_image_db\":%.3f}",r ? ",\n" : "",in_rate,out_rate,error,gain,rejection);
  }
  std::puts("\n]");
}
