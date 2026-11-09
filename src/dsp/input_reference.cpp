// SPDX-License-Identifier: MIT. Original GainControl + Processor, no Mala input helper.
#include "beads/gain_control.h"
#include "beads/dsp/processor.h"
#include "stmlib/utils/random.h"
#include "rate_converter.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>

beads::Processor processor;
beads::GainControl gain;
uint8_t memory[3][256 * 1024];
uint16_t reverb[32768];
int main(int argc, char** argv) {
  if (argc != 7) return 2;
  const unsigned quality=std::atoi(argv[1]), mask=std::atoi(argv[2]);
  const uint8_t setting=std::atoi(argv[3]);
  const unsigned frames=std::atoi(argv[4]);
  if (quality>3 || mask>3 || frames%12) return 2;
  FILE* out=std::fopen(argv[5],"wb"); FILE* report=std::fopen(argv[6],"w");
  FILE* in=std::fopen("/build/input.f32","wb");
  if (!out || !report || !in) return 3;
  uint8_t* buffers[]={memory[0],memory[1],memory[2]};
  const beads::Processor::Media media[]={beads::Processor::MEDIA_DIGITAL,
      beads::Processor::MEDIA_VINTAGE_DIGITAL,beads::Processor::MEDIA_CLEAN_TAPE,
      beads::Processor::MEDIA_DIRTY_TAPE};
  processor.Init(buffers,reverb); processor.Configure(media[quality],mask==1 || mask==2);
  const auto clipping=quality==3?beads::GainControl::SOFT_CLIPPING_MODE_ON:
      quality==2?beads::GainControl::SOFT_CLIPPING_MODE_DYNAMIC:
      beads::GainControl::SOFT_CLIPPING_MODE_OFF;
  gain.Init(processor.sample_rate(),clipping,true); stmlib::Random::Seed(0x21);
  mala::RateConverter down,up;
  down.Init(48000,processor.sample_rate()); up.Init(processor.sample_rate(),48000);
  beads::FloatFrame zero[12]{}; std::fwrite(zero,sizeof(zero),1,out);
  for (unsigned t=0;t<frames;t+=12) {
    beads::FloatFrame input[12],native[12],gained[12],processed[12],output[12];
    beads::Codec::Frame pcm[12]; bool freeze[12]{};
    for (unsigned i=0;i<12;++i) {
      const unsigned k=t+i;
      const float amplitude=setting? .8f : .025f;
      input[i]={amplitude*(k%109<55?1.f:-1.f), amplitude*(k%137<68?-.8f:.8f)};
      if (k%901==0) input[i]={1.2f,-1.2f};
      std::fwrite(input+i,sizeof(input[i]),1,in);
    }
    const unsigned n=down.Process(input,12,native);
    for (unsigned i=0;i<n;++i) {
      // Independent PCM conversion, including exact positive saturation.
      auto quantize=[](float x)->int32_t {
        return int32_t(std::clamp(double(x)*2147483648.0,-2147483648.0,2147483647.0));
      };
      pcm[i]={quantize(native[i].l),quantize(native[i].r)};
    }
    gain.Process(true,setting,!(mask&1),!(mask&2),pcm,gained,n);
    beads::Parameters p{};
    p.time={.25f,0.f,0.f,false}; p.size={.6f,0.f,0.f,false};
    p.shape={.6f,0.f,0.f,false}; p.pitch={0.f,0.f,0.f,false};
    beads::ModulatedParameter density{.73f,0.f};
    beads::Processor::MixParameters mix{.2f*1.005f-.002f,.85f*1.005f,.15f*1.005f,false};
    processor.Process(beads::SEED_BUTTON_STATE_LOCKED,nullptr,freeze,density,p,mix,gained,processed,n);
    up.Process(processed,n,output);
    if (t+12<frames) std::fwrite(output,sizeof(output),1,out);
  }
  std::fprintf(report,"{\"quality\":%u,\"mask\":%u,\"gain\":%u,\"frames\":%u,\"adjusting\":%s,\"vu\":%u}\n",
      quality,mask,setting,frames,gain.adjusting()?"true":"false",gain.vu_meter());
  std::fclose(out); std::fclose(report); std::fclose(in);
}
