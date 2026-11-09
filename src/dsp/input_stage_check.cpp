// SPDX-License-Identifier: MIT. Input adapter versus unmodified original gain stage.
#include "input_stage.h"
#include <cassert>
#include <cstring>
#include <cstdio>
#include <initializer_list>
#include <new>

int main() {
  assert(mala::CodecSample(1.f)==INT32_MAX && mala::CodecSample(-1.f)==INT32_MIN);
  assert(mala::CodecSample(.5f)==1073741824 && mala::CodecSample(-.5f)==-1073741824);
  assert(mala::CodecSample(NAN)==0 && mala::CodecSample(INFINITY)==0);
  unsigned cases=0;
  const unsigned rates[]={48000,32000,48000,24000};
  for (unsigned q=0;q<4;++q) for (unsigned mask=0;mask<4;++mask)
    for (unsigned setting : {0u,1u,128u,255u}) {
      // Its empty constructor relies on hardware BSS initialization. Match that
      // explicitly, including fields which Init(reset=true) intentionally retains.
      alignas(beads::GainControl) unsigned char a[sizeof(beads::GainControl)]{};
      alignas(beads::GainControl) unsigned char b[sizeof(beads::GainControl)]{};
      auto& original=*new(a) beads::GainControl;
      auto& wrapped=*new(b) beads::GainControl;
      const unsigned n=rates[q]/4000;
      original.Init(rates[q],mala::ClippingMode(q),true);
      wrapped.Init(rates[q],mala::ClippingMode(q),true);
      beads::FloatFrame expected[12],actual[13]; beads::Codec::Frame pcm[12];
      for (unsigned block=0;block<28000;++block) {
        for (unsigned i=0;i<n;++i) {
          // A silent connected channel must never borrow the other input.
          const float l=mask==2?0.f:.025f, r=mask==1?0.f:-.03f;
          actual[i]={l,r}; pcm[i]={int32_t(double(l)*2147483648.),int32_t(double(r)*2147483648.)};
        }
        actual[n]={123,456};
        original.Process(true,setting,!(mask&1),!(mask&2),pcm,expected,n);
        mala::ProcessInput(wrapped,true,setting,mask,actual,n);
        assert(!std::memcmp(expected,actual,n*sizeof(expected[0])));
        assert(actual[n].l==123 && actual[n].r==456);
        assert(original.adjusting()==wrapped.adjusting() && original.vu_meter()==wrapped.vu_meter());
        if (mask==1 || mask==2) for (unsigned i=0;i<n;++i) assert(actual[i].l==actual[i].r);
        if (!mask) for (unsigned i=0;i<n;++i) assert(actual[i].l==0 && actual[i].r==0);
      }
      assert(!wrapped.adjusting());
      if (!setting && mask) {
        // Completed learning survives a quality-only re-init at its new rate.
        wrapped.Init(32000,beads::GainControl::SOFT_CLIPPING_MODE_OFF,false);
        assert(!wrapped.adjusting()); wrapped.Restart(); assert(wrapped.adjusting());
      }
      ++cases;
      original.~GainControl(); wrapped.~GainControl();
    }
  // Connected silence on L must stay silent with a sounding R (no amplitude heuristic).
  alignas(beads::GainControl) unsigned char c[sizeof(beads::GainControl)]{};
  auto& g=*new(c) beads::GainControl;
  g.Init(48000,beads::GainControl::SOFT_CLIPPING_MODE_OFF,true);
  beads::FloatFrame stereo[12]; for(auto& f:stereo) f={0,.1f};
  mala::ProcessInput(g,true,0,3,stereo,12);
  for(const auto& f:stereo) assert(f.l==0 && f.r>0);
  g.~GainControl();
  std::printf("{\"original_gain_cases\":%u,\"seven_seconds_per_case\":true,\"pcm_saturation_nonfinite\":true,\"learning_restart_and_quality_retention\":true,\"connected_silence_preserved\":true}\n",cases);
}
