// SPDX-License-Identifier: MIT. Independent direct build of the pinned Beads core.
// No Mala adapter is included. Fixtures specify processor-unit CV and gate events.
#include "beads/dsp/processor.h"
#include "stmlib/utils/random.h"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>

beads::Processor processor;
uint8_t delay_memory[3][256 * 1024];
uint16_t reverb_memory[32768];
int main(int argc, char** argv) {
  if (argc != 4) return 2;
  const int scenario = std::atoi(argv[1]);
  const bool external = scenario == 1 || scenario == 3;
  FILE* out = std::fopen(argv[2], "wb");
  FILE* fixture = std::fopen(argv[3], "wb");
  if (!out || !fixture) return 3;
  uint8_t* memories[] = {delay_memory[0], delay_memory[1], delay_memory[2]};
  stmlib::Random::Seed(0x21);
  processor.Init(memories, reverb_memory);
  processor.Configure(beads::Processor::MEDIA_DIGITAL, false);
  float time = 0, size = 0, shape = 0, assign = 0;
  std::array<bool, 120> delayed{};
  unsigned cursor = 0, phase = 0;
  stmlib::GateFlags previous = stmlib::GATE_FLAG_LOW;
  for (unsigned host = 0; host < 96000; host += 128) {
    for (unsigned local = 0; local < 128;) {
      unsigned n = std::min(12u - phase, 128u - local);
      if (!phase && external) {
        // Known voltage fixture: 1.25, -.75, .8, 1, -.25, .5 volts.
        time += .5f * (.25f - time);
        size += .5f * (-.15f - size);
        shape += .5f * (.16f - shape);
        assign += .1f * (.1f - assign);
      }
      beads::Parameters p{};
      p.time = {.25f, .35f, time, external};
      p.size = {.6f, .6f, size, external};
      p.shape = {.6f, -.5f, shape, external};
      p.pitch = {0.f, .4f, external ? 12.f : 0.f, external};
      p.monophonic_mode = false;
      beads::ModulatedParameter density{scenario == 3 ? .5f : .73f, scenario == 1 ? -.05f : 0.f};
      beads::Processor::MixParameters mix{
          .2f * 1.005f + ((external ? assign : 0.f) - .002f),
          .85f * 1.005f, .15f * 1.005f, false};
      beads::FloatFrame input[12], output[12];
      bool freeze[12];
      stmlib::GateFlags seed[12];
      for (unsigned i = 0; i < n; ++i) {
        const unsigned t = host + local + i;
        const float envelope = float(6000 - t % 6000) / 6000.f;
        input[i] = {((t % 109 < 55) ? .12f : -.12f) * envelope,
                    ((t % 137 < 68) ? .11f : -.11f) * envelope};
        if (t >= 84000) input[i] = {0, 0};
        const float gate = t % 6000 < 20 ? 1.f : 0.f;
        const float fg = t >= 60000 && t < 84000 ? 1.f : 0.f;
        const float frame[] = {input[i].l, input[i].r, 1.25f, -.75f, .8f,
                               1.f, -.25f, .5f, gate, fg};
        std::fwrite(frame, sizeof(float), 10, fixture);
        const bool old = delayed[cursor];
        delayed[cursor] = gate >= .5f;
        cursor = (cursor + 1) % 120;
        seed[i] = previous = stmlib::ExtractGateFlags(previous, old);
        freeze[i] = (external && fg >= .5f) || (scenario == 2 && t >= 60000);
      }
      const auto button = scenario == 3
          ? (host == 24064 ? beads::SEED_BUTTON_STATE_ON : beads::SEED_BUTTON_STATE_OFF)
          : beads::SEED_BUTTON_STATE_LOCKED;
      processor.Process(button, external ? seed : nullptr, freeze, density, p, mix, input, output, n);
      std::fwrite(output, sizeof(beads::FloatFrame), n, out);
      phase = (phase + n) % 12;
      local += n;
    }
  }
  std::fclose(fixture); std::fclose(out);
}
