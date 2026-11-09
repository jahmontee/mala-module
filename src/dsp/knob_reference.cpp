// SPDX-License-Identifier: MIT. Original PotChannels feeding original audio cores.
#include "beads/pot_channel.h"
#include "beads/dsp/processor.h"
#include "beads/dsp/synth.h"
#include "stmlib/utils/random.h"
#include "rate_converter.h"
#include <cstdio>
#include <cstdlib>

beads::Processor processor;
beads::Synth synth;
beads::PotChannel pots[12],instant[12];
uint8_t memory[3][256*1024];uint16_t reverb[32768];
float v[12];
void Read(const uint16_t* raw,FILE* targets=nullptr) {
  for (unsigned i=0;i<12;++i) {
    pots[i].Process(raw[i]);v[i]=pots[i].value();
    instant[i].Process(raw[i]);float target=instant[i].value();
    if (targets)std::fwrite(&target,sizeof(float),1,targets);
  }
}
beads::Parameters Parameters(const float* cv) {
  beads::Parameters p{};
  p.time={v[0],v[5],cv[0],true};p.size={v[1],v[6],cv[1],true};
  p.shape={v[2],v[7],cv[2],true};p.pitch={v[3],v[8],cv[3],true};return p;
}
beads::Processor::MixParameters Mix(float assign) {
  float feedback=v[9]*1.005f+assign-.002f;
  CONSTRAIN(feedback,0.f,1.f);
  return {feedback,v[10]*1.005f,v[11]*1.005f,false};
}
int main(int argc,char** argv) {
  if(argc!=3)return 2;const unsigned quality=std::atoi(argv[1]);const bool synthesis=std::atoi(argv[2]);
  if(quality>3)return 2;
  FILE* audio=std::fopen("/build/knob-reference.f32","wb");
  FILE* targets=std::fopen("/build/knob-targets.f32","wb");
  FILE* idle=std::fopen("/build/knob-idle.f32","wb");
  if(!audio||!targets||!idle)return 3;
  for(unsigned i=0;i<12;++i) {
    auto law=i==3 ? beads::PotChannel::LAW_DETUNE : i>=5&&i<=8 ? beads::PotChannel::LAW_ATTENUVERTER : beads::PotChannel::LAW_NORMAL;
    pots[i].Init(law,.05f,i==0 ? .001f : 0.f);instant[i].Init(law,1.f,0.f);
  }
  stmlib::Random::Seed(0x21);uint8_t* buffers[]={memory[0],memory[1],memory[2]};
  processor.Init(buffers,reverb);synth.Init(reverb);
  processor.Configure(beads::Processor::MEDIA_DIGITAL,false);
  processor.Configure(beads::Processor::Media(synthesis ? 3 : 3-quality),false);
  beads::FloatFrame input[12]{},out[12]{},native[12]{};bool freeze[12]{};float cv[6]{};
  if(synthesis) {
    const uint16_t raw[]={16384,39321,39321,32768,32768,32768,32768,32768,32768,0,0,0};
    for(unsigned i=0;i<12;++i){instant[i].Process(raw[i]);float target=instant[i].value();std::fwrite(&target,4,1,idle);}
    for(unsigned block=0;block<41000;++block) {
      Read(raw);
      if(block<40000)processor.Process(beads::SEED_BUTTON_STATE_OFF,nullptr,freeze,{v[4],0},Parameters(cv),Mix(0),input,out,12);
    }
  }
  std::fclose(idle);
  const unsigned rate=synthesis ? 48000 : unsigned(processor.sample_rate());
  mala::RateConverter down,up;down.Init(48000,rate);up.Init(rate,48000);
  std::fill(std::begin(out),std::end(out),beads::FloatFrame{0,0});std::fwrite(out,sizeof(out),1,audio);
  bool delayed[120]{};unsigned cursor=0;stmlib::GateFlags previous=stmlib::GATE_FLAG_LOW;
  const uint16_t pitches[]={0,4551,10012,15473,20935,26396,32768,39139,44600,50062,55523,60984,65535,41000,30000,53000};
  for(unsigned t=0;t<48000;t+=12) {
    const unsigned block=t/12,section=block/250;
    const uint16_t raw[]={uint16_t(4000+(section%8)*7000),uint16_t(block<800 ? 13107 : block<1600 ? 39321 : block<3200 ? 65535 : 63000),
      uint16_t(10000+(section%5)*11000),pitches[section],uint16_t(section%2 ? 52000 : 21000),
      uint16_t(12000+(section%5)*10000),uint16_t(section%2 ? 28000 : 45000),
      uint16_t(section%3 ? 32000 : 47000),uint16_t(section%2 ? 40000 : 20000),12000,43000,9000};
    Read(raw,targets);
    const float volts[]={1.25f,-.75f,.8f,.125f,.3f,.5f};
    for(unsigned i=0;i<6;++i) {
      const float coefficient=i<3 ? .5f : i==5 ? .1f : 1.f;
      const float value=i==3 ? volts[i]*12.f : volts[i]/5.f;
      cv[i]+=coefficient*(value-cv[i]);
    }
    bool host_gate[12];
    for(unsigned i=0;i<12;++i) {
      const unsigned k=t+i;
      input[i]={k%97<48 ? .12f : -.12f,k%131<65 ? .09f : -.09f};
      host_gate[i]=delayed[cursor];delayed[cursor]=k%2400==0;cursor=(cursor+1)%120;
    }
    unsigned n=down.Process(input,12,native);stmlib::GateFlags events[12];
    for(unsigned i=0;i<n;++i) {
      bool gate=false;for(unsigned j=i*12/n;j<(i+1)*12/n;++j)gate|=host_gate[j];
      events[i]=previous=stmlib::ExtractGateFlags(previous,gate);freeze[i]=t>=30000&&t<42000;
    }
    const auto p=Parameters(cv);const beads::ModulatedParameter d{v[4],cv[4]};const auto mix=Mix(cv[5]);
    if(synthesis)synth.Render(beads::SEED_BUTTON_STATE_LOCKED,events,freeze,beads::Synth::RESOLUTION_16_BIT,d,p,mix,out,n);
    else processor.Process(beads::SEED_BUTTON_STATE_LOCKED,events,freeze,d,p,mix,native,out,n);
    up.Process(out,n,native);
    if(t+12<48000)std::fwrite(native,sizeof(beads::FloatFrame),12,audio);
  }
  std::fclose(targets);std::fclose(audio);
}
