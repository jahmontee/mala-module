// SPDX-License-Identifier: MIT. Direct original-core fixture, no LV2 adapter.
#include "beads/dsp/processor.h"
#include "stmlib/utils/random.h"
#include "rate_converter.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>

beads::Processor processor;
uint8_t delay_memory[3][256 * 1024];
uint16_t reverb_memory[32768];
int main(int argc, char** argv) {
  if (argc != 5) return 2;
  const unsigned quality = std::atoi(argv[1]);
  const bool mono = std::atoi(argv[2]);
  if (quality > 3) return 2;
  FILE* out = std::fopen(argv[3], "wb");
  FILE* report = std::fopen(argv[4], "w");
  if (!out || !report) return 3;
  const beads::Processor::Media media[] = {beads::Processor::MEDIA_DIGITAL,
    beads::Processor::MEDIA_VINTAGE_DIGITAL, beads::Processor::MEDIA_CLEAN_TAPE,
    beads::Processor::MEDIA_DIRTY_TAPE};
  uint8_t* memories[] = {delay_memory[0], delay_memory[1], delay_memory[2]};
  stmlib::Random::Seed(0x21);
  processor.Init(memories, reverb_memory);
  processor.Configure(media[quality], mono);
  const unsigned native_rate = processor.sample_rate();
  const unsigned record_rate = quality == 2 ? 24000 : native_rate;
  const unsigned capacity = processor.remaining();
  const unsigned capacities[] = {192000, 256000, 256000, 384000};
  if (capacity != capacities[quality] * (mono ? 2 : 1)) return 4;
  mala::RateConverter down, up;
  down.Init(48000, native_rate); up.Init(native_rate, 48000);
  float time = 0, size = 0, shape = 0, assign = 0;
  bool delayed[120]{};
  unsigned cursor = 0;
  stmlib::GateFlags previous = stmlib::GATE_FLAG_LOW;
  // The host adapter's fixed 12-frame queue precedes the native output.
  beads::FloatFrame zero[12]{};
  std::fwrite(zero, sizeof(beads::FloatFrame), 12, out);
  FILE* fixture = quality == 0 && !mono ? std::fopen("/build/input.f32", "wb") : nullptr;
  float frozen_peak = 0;
  for (unsigned host = 0; host < 192000; host += 12) {
    time += .5f * (.25f - time); size += .5f * (-.15f - size);
    shape += .5f * (.16f - shape); assign += .1f * (.1f - assign);
    beads::Parameters p{};
    p.time = {.02f, .35f, time, true}; p.size = {.6f, .6f, size, true};
    p.shape = {.6f, -.5f, shape, true}; p.pitch = {0.f, .4f, 12.f, true};
    beads::ModulatedParameter density{.73f, -.05f};
    beads::Processor::MixParameters mix{.2f * 1.005f + (assign - .002f),
        .85f * 1.005f, .15f * 1.005f, false};
    beads::FloatFrame input[12], native_in[12], native_out[12], output[12];
    bool host_seed[12], host_freeze[12], freeze[12];
    stmlib::GateFlags seed[12];
    for (unsigned i = 0; i < 12; ++i) {
      const unsigned t = host + i;
      const float envelope = float(6000 - t % 6000) / 6000.f;
      input[i] = {((t % 109 < 55) ? .12f : -.12f) * envelope,
                  ((t % 137 < 68) ? .11f : -.11f) * envelope};
      if (t >= 144000) input[i] = {0, 0};
      if (fixture) {
        const float frame[] = {input[i].l, input[i].r, 1.25f, -.75f, .8f, 1.f,
                               -.25f, .5f, float(t % 6000 < 1), float(t >= 120000)};
        std::fwrite(frame, sizeof(float), 10, fixture);
      }
      host_seed[i] = delayed[cursor];
      // One-frame Seed pulses also exercise the gate decimation at native rates.
      delayed[cursor] = t % 6000 < 1; cursor = (cursor + 1) % 120;
      host_freeze[i] = t >= 120000;
    }
    const unsigned n = down.Process(input, 12, native_in);
    for (unsigned i = 0; i < n; ++i) {
      bool g = false, f = false;
      for (unsigned j = i * 12 / n; j < (i + 1) * 12 / n; ++j) {
        g |= host_seed[j]; f |= host_freeze[j];
      }
      freeze[i] = f; seed[i] = previous = stmlib::ExtractGateFlags(previous, g);
    }
    processor.Process(beads::SEED_BUTTON_STATE_LOCKED, seed, freeze, density, p, mix, native_in, native_out, n);
    if (host == 0 && *processor.mutable_delay_write_ptr() != int(capacity - n / processor.ratio())) return 5;
    up.Process(native_out, n, output);
    if (host >= 144000) for (const auto& v : output) frozen_peak = std::max(frozen_peak, std::max(std::fabs(v.l), std::fabs(v.r)));
    if (host + 12 < 192000) std::fwrite(output, sizeof(beads::FloatFrame), 12, out);
  }
  std::fprintf(report, "{\"quality\":%u,\"mono\":%s,\"native_rate\":%u,\"record_rate\":%u,\"record_frames\":%u,\"buffer_seconds\":%.9f,\"frozen_peak\":%.9f,\"write_wrap_checked\":true}\n",
      quality, mono ? "true" : "false", native_rate, record_rate, capacity, double(capacity) / record_rate, frozen_peak);
  std::fclose(out); std::fclose(report); if (fixture) std::fclose(fixture);
}
