// SPDX-License-Identifier: MIT. Direct unmodified Beads Synth/Processor oracle.
#include "beads/dsp/processor.h"
#include "beads/dsp/synth.h"
#include "stmlib/utils/random.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>

beads::Processor processor;
beads::Synth synth;
uint8_t memory[3][256 * 1024];
uint16_t reverb[32768];
int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const unsigned quality = std::atoi(argv[1]);
  if (quality > 3) return 2;
  FILE* output = std::fopen("/build/synth-reference.f32", "wb");
  FILE* inputs = std::fopen("/build/synth-inputs.f32", "wb");
  if (!output || !inputs) return 3;
  stmlib::Random::Seed(0x21);
  uint8_t* buffers[] = {memory[0], memory[1], memory[2]};
  processor.Init(buffers, reverb);
  synth.Init(reverb);
  processor.Configure(beads::Processor::MEDIA_DIGITAL, false);
  processor.Configure(beads::Processor::Media(3 - quality), false);
  beads::Parameters p{};
  p.time = {.25f, 0, 0, false}; p.size = {.6f, 0, 0, false};
  p.shape = {.6f, 0, 0, false}; p.pitch = {0, 0, 0, false};
  beads::ModulatedParameter density{.5f, 0};
  beads::Processor::MixParameters mix{0, 0, 0, false};
  beads::FloatFrame zero[12]{}, out[12]{};
  bool freeze[12]{};
  // Exercise the original idle recording path to preserve its RNG/reverb state.
  for (unsigned block = 0; block < 40000; ++block)
    processor.Process(beads::SEED_BUTTON_STATE_OFF, nullptr, freeze, density,
        p, mix, zero, out, unsigned(processor.sample_rate()) / 4000);
  // The 250 ms codec silence runs neither original audio engine.
  std::fwrite(zero, sizeof(zero), 1, output);  // Existing 12-frame host adapter delay.
  float cv[6]{};
  bool seed_delay[120]{};
  unsigned delay_index = 0;
  stmlib::GateFlags previous = stmlib::GATE_FLAG_LOW;
  constexpr unsigned frames = 48000;
  for (unsigned t = 0; t < frames; t += 12) {
    float block_inputs[12][8];
    stmlib::GateFlags seed[12];
    for (unsigned i = 0; i < 12; ++i) {
      const unsigned k = t + i;
      const unsigned bank = (k / 4000) % 12;
      float* v = block_inputs[i];
      v[0] = 3.f * std::sin(float(k) * .0004f);
      v[1] = -2.f + float(k % 6000) / 1500.f;
      v[2] = 2.f * std::cos(float(k) * .0003f);
      v[3] = k < 24000 ? .5f : -1.f;
      v[4] = .4f * std::sin(float(k) * .0002f);
      v[5] = (float(bank) / 11.f - .1f * 1.005f + .002f) * 5.f;
      v[6] = k % 2400 < 24 ? 1.f : 0.f;
      v[7] = k >= 16000 && k < 24000 ? 1.f : 0.f;
      std::fwrite(v, sizeof(float), 8, inputs);
      freeze[i] = v[7] > .5f;
      const bool gate = seed_delay[delay_index];
      seed_delay[delay_index] = v[6] > .5f;
      delay_index = (delay_index + 1) % 120;
      seed[i] = previous = stmlib::ExtractGateFlags(previous, gate);
    }
    for (unsigned i = 0; i < 6; ++i) {
      const float coefficient = i < 3 ? .5f : i == 5 ? .1f : 1.f;
      const float v = i == 3 ? block_inputs[0][i] * 12.f : block_inputs[0][i] / 5.f;
      cv[i] += coefficient * (v - cv[i]);
    }
    p.time = {.25f, .35f, cv[0], true}; p.size = {.55f, -.6f, cv[1], true};
    p.shape = {.6f, .4f, cv[2], true}; p.pitch = {3.f, .7f, cv[3], true};
    density = {.8f, cv[4]};
    mix = {std::fmax(0.f, std::fmin(1.f, .1f * 1.005f + cv[5] - .002f)),
        .65f * 1.005f, .15f * 1.005f, false};
    synth.Render(beads::SEED_BUTTON_STATE_LOCKED, seed, freeze,
        beads::Synth::Resolution(3 - quality), density, p, mix, out, 12);
    if (t + 12 < frames) std::fwrite(out, sizeof(out), 1, output);
  }
  std::fclose(output); std::fclose(inputs);
  std::printf("{\"quality\":%u,\"frames\":%u,\"banks\":%zu,\"native_rate\":48000}\n",
      quality, frames, beads::kNumBanks);
}
