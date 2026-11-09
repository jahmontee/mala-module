// SPDX-License-Identifier: MIT. Original Processor/Synth outputs before jack routing.
#include "beads/dsp/processor.h"
#include "beads/dsp/synth.h"
#include "stmlib/utils/random.h"
#include "rate_converter.h"
#include <cstdio>
#include <cstdlib>

beads::Processor processor;
beads::Synth synth;
uint8_t memory[3][256 * 1024];
uint16_t reverb[32768];
int main(int argc, char** argv) {
  if (argc != 3) return 2;
  const unsigned quality = std::atoi(argv[1]), mode = std::atoi(argv[2]);
  if (quality > 3 || mode > 2) return 2;
  FILE* audio = std::fopen("/build/output-reference.f32", "wb");
  FILE* gates = std::fopen("/build/output-gates.f32", "wb");
  if (!audio || !gates) return 3;
  stmlib::Random::Seed(0x21);
  uint8_t* buffers[] = {memory[0],memory[1],memory[2]};
  processor.Init(buffers,reverb); synth.Init(reverb);
  processor.Configure(beads::Processor::MEDIA_DIGITAL,false);
  beads::FloatFrame input[12]{}, native[12]{}, out[12]{};
  bool freeze[12]{};
  beads::Parameters p{};
  p.time={.02f,0,0,false}; p.size={mode==1 ? 1.f : .6f,0,0,false};
  p.shape={.6f,0,0,false}; p.pitch={0,0,0,false};
  if (mode==2) {
    beads::ModulatedParameter d{.5f,0};
    beads::Processor::MixParameters m{0,0,0,false};
    // Match original quiet wait; restart silence calls neither audio core.
    beads::Parameters idle=p; idle.time.base=.25f;
    for (unsigned b=0;b<40000;++b)
      processor.Process(beads::SEED_BUTTON_STATE_OFF,nullptr,freeze,d,idle,m,input,native,12);
  } else processor.Configure(beads::Processor::Media(3-quality),false);
  const unsigned rate=mode==2 ? 48000 : unsigned(processor.sample_rate());
  mala::RateConverter down,up; down.Init(48000,rate); up.Init(rate,48000);
  float zero=0; std::fwrite(out,sizeof(out),1,audio);
  for (unsigned i=0;i<12;++i) std::fwrite(&zero,sizeof(zero),1,gates);
  bool delayed[120]{}; unsigned cursor=0;
  stmlib::GateFlags previous=stmlib::GATE_FLAG_LOW;
  for (unsigned t=0;t<48000;t+=12) {
    bool host_gate[12];
    for (unsigned i=0;i<12;++i) {
      const unsigned k=t+i;
      input[i]={k%97<48 ? .12f : -.12f,k%131<65 ? .09f : -.09f};
      host_gate[i]=delayed[cursor]; delayed[cursor]=k%2400==0; cursor=(cursor+1)%120;
    }
    unsigned n=down.Process(input,12,native);
    stmlib::GateFlags events[12];
    for (unsigned i=0;i<n;++i) {
      bool gate=false;
      for (unsigned j=i*12/n;j<(i+1)*12/n;++j) gate|=host_gate[j];
      events[i]=previous=stmlib::ExtractGateFlags(previous,gate);
      freeze[i]=t>=24000 && t<36000;
    }
    beads::ModulatedParameter d{.8f,0};
    beads::Processor::MixParameters m{.2f*1.005f-.002f,.65f*1.005f,.15f*1.005f,true};
    if (mode==2) synth.Render(beads::SEED_BUTTON_STATE_LOCKED,events,freeze,
        beads::Synth::Resolution(3-quality),d,p,m,out,n);
    else processor.Process(beads::SEED_BUTTON_STATE_LOCKED,events,freeze,d,p,m,native,out,n);
    float logic[12];
    for (unsigned i=0;i<12;++i) logic[i]=out[i*n/12].r<-.4f ? .8f : 0.f;
    // This direct oracle never includes output_routing.h. Only left audio uses FIR.
    up.Process(out,n,native);
    if (t+12<48000) {
      std::fwrite(native,sizeof(beads::FloatFrame),12,audio);
      std::fwrite(logic,sizeof(float),12,gates);
    }
  }
  std::fclose(audio);std::fclose(gates);
}
