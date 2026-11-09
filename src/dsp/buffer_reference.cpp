// SPDX-License-Identifier: MIT. Original cold-boot buffer load and Processor oracle.
#include "beads/dsp/processor.h"
#include "beads/dsp/synth.h"
#include "beads/gain_control.h"
#include "stmlib/utils/random.h"
#include "rate_converter.h"
#include <cstdio>
#include <cstring>
beads::Processor processor;
beads::Synth synth;
beads::GainControl gain;
uint8_t memory[3][256*1024];
uint16_t reverb[32768];
uint8_t blob[768032];
unsigned u32(const uint8_t* p) {
  return unsigned(p[0]) | unsigned(p[1])<<8 | unsigned(p[2])<<16 | unsigned(p[3])<<24;
}
int main() {
  FILE* in=std::fopen("/build/current.blob","rb");
  FILE* out=std::fopen("/build/buffer-reference.f32","wb");
  if (!in || !out || std::fread(blob,1,sizeof(blob),in)!=sizeof(blob)) return 1;
  std::fclose(in); stmlib::Random::Seed(0x21);
  uint8_t* buffers[]={memory[0],memory[1],memory[2]};
  processor.Init(buffers,reverb); synth.Init(reverb);
  processor.Configure(beads::Processor::MEDIA_DIGITAL,false);
  processor.Configure(beads::Processor::Media(blob[16]),bool(blob[17]));
  // Same 32-byte raw copy and write-pointer restoration as the source Load().
  for (unsigned offset=0; offset<768000; offset+=32)
    std::memcpy(processor.delay_buffer_raw_bytes(offset),blob+32+offset,32);
  *processor.mutable_delay_write_ptr()=int(u32(blob+12));
  mala::RateConverter up; up.Init(processor.sample_rate(),48000);
  beads::FloatFrame zero[12]{},gained[12],native[12],host[12]; bool frozen[12];
  beads::Codec::Frame pcm[12]{};
  const auto clipping=blob[16]==0 ? beads::GainControl::SOFT_CLIPPING_MODE_ON :
      blob[16]==1 ? beads::GainControl::SOFT_CLIPPING_MODE_DYNAMIC : beads::GainControl::SOFT_CLIPPING_MODE_OFF;
  gain.Init(processor.sample_rate(),clipping,true);
  const unsigned block_size=unsigned(processor.sample_rate())/4000;
  for (unsigned i=0; i<1000; ++i) gain.Process(false,1,false,bool(blob[17]),pcm,gained,block_size);
  for (bool& b : frozen) b=true;
  beads::Parameters p{};
  p.time={.02f,0,0,false}; p.size={.6f,0,0,false};
  p.shape={.6f,0,0,false}; p.pitch={0,0,0,false};
  beads::Processor::MixParameters mix{.2f*1.005f-.002f,.85f*1.005f,.15f*1.005f,false};
  std::fwrite(zero,sizeof(zero),1,out);
  for (unsigned t=0; t<48000; t+=12) {
    const unsigned n=unsigned(processor.sample_rate())/4000;
    gain.Process(true,1,false,bool(blob[17]),pcm,gained,n);
    processor.Process(beads::SEED_BUTTON_STATE_LOCKED,nullptr,frozen,
        beads::ModulatedParameter{.73f,0},p,mix,gained,native,n);
    up.Process(native,n,host);
    if (t+12<48000) std::fwrite(host,sizeof(host),1,out);
  }
  std::fclose(out);
}
