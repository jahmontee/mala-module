// SPDX-License-Identifier: MIT. Address-sanitized first/final wavetable endpoints.
#include "beads/dsp/synth.h"
#include "stmlib/utils/random.h"
#include <cmath>
#include <cstdio>
beads::Synth synth;
uint16_t reverb[32768];
int main() {
  unsigned cases=0;
  for (unsigned quality=0; quality<4; ++quality) {
    for (unsigned bank : {0u,11u}) {
      for (float position : {0.f,1.f}) {
        synth.Init(reverb); stmlib::Random::Seed(0x21);
        beads::Parameters p{};
        p.time={position,0,0,false}; p.size={.6f,0,0,false};
        p.shape={.6f,0,0,false}; p.pitch={0,0,0,false};
        beads::Processor::MixParameters mix{float(bank)/11.f,.65f,.15f,false};
        beads::FloatFrame out[12]; bool freeze[12]{};
        for (unsigned block=0; block<1000; ++block) {
          synth.Render(beads::SEED_BUTTON_STATE_LOCKED,nullptr,freeze,
              beads::Synth::Resolution(quality),beads::ModulatedParameter{.3f,0},p,mix,out,12);
          for (const auto& f : out) if (!std::isfinite(f.l) || !std::isfinite(f.r)) return 1;
        }
        ++cases;
      }
    }
  }
  std::printf("{\"endpoint_cases\":%u,\"address_sanitizer_pass\":true}\n",cases);
}
