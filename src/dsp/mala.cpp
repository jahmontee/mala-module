// Copyright 2026 Beebo / Hector Lab contributors. SPDX-License-Identifier: MIT
// 48 kHz host adapter for all original Beads media. Algorithm source unchanged.
#include <lv2/core/lv2.h>
#include <lv2/state/state.h>
#include <lv2/urid/urid.h>
#include <lv2/atom/atom.h>
#include "beads/dsp/processor.h"
#include "beads/dsp/synth.h"
#include "stmlib/utils/random.h"
#include "rate_converter.h"
#include "input_stage.h"
#include "frozen_buffer.h"
#include "output_routing.h"
#include "panel_response.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iterator>
#include <new>

namespace {
constexpr const char* kURI = "urn:beebo-hector-lab:mala-preview";
enum Port { TIME, SIZE, SHAPE, PITCH, DENSITY, TIME_AMOUNT, SIZE_AMOUNT,
  SHAPE_AMOUNT, PITCH_AMOUNT, FEEDBACK, MIX, REVERB, FREEZE, SEED,
  LEFT_IN, RIGHT_IN, LEFT_OUT, RIGHT_OUT, TIME_CV, SIZE_CV, SHAPE_CV,
  PITCH_CV, DENSITY_CV, ASSIGN_CV, SEED_GATE, FREEZE_GATE, CONNECTIONS,
  ASSIGN_DESTINATION, FEEDBACK_CV_AMOUNT, MIX_CV_AMOUNT, REVERB_CV_AMOUNT,
  ACTIVE_FREEZE, QUALITY, MONO, ACTIVE_QUALITY, ACTIVE_MONO,
  BUFFER_SECONDS, MODE_TRANSITION, LATENCY, INPUT_STAGE, AUDIO_CONNECTIONS,
  INPUT_GAIN, GAIN_RELEARN, GAIN_ADJUSTING, INPUT_VU,
  SYNTH_ENABLE, ACTIVE_SYNTH, SYNTH_WAIT_SECONDS, BUFFER_AUTOSAVE,
  BUFFER_STATE, BUFFER_WAIT_SECONDS, BUFFER_EPOCH, FREEZE_RELEASE,
  OUTPUT_NORMALIZATION, OUTPUT_CONNECTIONS, GRAIN_TRIGGERS, PANEL_RESPONSE,
  CV_INPUT_UNITS, PORT_COUNT };
constexpr unsigned kSeedDelay = 120;  // Original 2.5 ms Seed compensation.
constexpr unsigned kSynthWaitBlocks = 40000;  // 10 seconds at 4 kHz.
struct Mala {
  beads::Processor processor;
  beads::Synth synth;
  beads::GainControl gain;
  mala::FrozenBuffer backup;
  LV2_URID state_key, chunk_type;
  uint8_t delay[3][256 * 1024];
  uint16_t reverb[32768];
  float* ports[PORT_COUNT];
  float cv[6];
  bool seed_delay[kSeedDelay];
  unsigned delay_index, phase, transition_blocks;
  mala::RateConverter input_converter[4], output_converter[4];
  mala::OutputRouting output_routing;
  mala::PanelResponse panel;
  beads::FloatFrame input[12], output[12];
  bool freeze[12], delayed_seed[12];
  beads::Parameters parameters;
  beads::ModulatedParameter density;
  beads::Processor::MixParameters mix;
  beads::SeedButtonState seed;
  unsigned mask, quality;
  int requested_quality;
  bool mono, requested_mono, configured;
  float buffer_seconds;
  bool seed_connected;
  bool input_stage, previous_input_stage;
  bool synth_enable, synth_mode;
  bool buffer_autosave, restored_freeze, release_baseline_pending, gain_baseline_pending;
  unsigned freeze_release, previous_freeze_release;
  bool restore_freeze_anchor;
  unsigned no_input_blocks;
  unsigned audio_connections, gain_relearn, previous_gain_relearn;
  unsigned output_connections;
  bool output_normalization;
  uint8_t input_gain;
  stmlib::GateFlags previous_seed;
  uint32_t rng;
};
float bounded(float v, float lo, float hi, float fallback = 0.f) {
  return std::isfinite(v) ? std::max(lo, std::min(hi, v)) : fallback;
}
float control(const Mala* p, Port port, float fallback = 0.f,
              float lo = 0.f, float hi = 1.f) {
  return p->ports[port] ? bounded(*p->ports[port], lo, hi, fallback) : fallback;
}
float sample(const Mala* p, Port port, unsigned index) {
  const float v = p->ports[port] ? p->ports[port][index] : 0.f;
  return std::isfinite(v) ? v : 0.f;
}
LV2_Handle instantiate(const LV2_Descriptor*, double rate, const char*,
                       const LV2_Feature* const* features) {
  if (rate != 48000.) return nullptr;
  void* memory = std::calloc(1, sizeof(Mala));
  if (!memory) return nullptr;
  auto* p = new(memory) Mala;
  if (features) for (unsigned i=0; features[i]; ++i) {
    if (!std::strcmp(features[i]->URI,LV2_URID__map)) {
      auto* map=static_cast<const LV2_URID_Map*>(features[i]->data);
      if (map && map->map) {
        p->state_key=map->map(map->handle,"urn:beebo-hector-lab:mala-preview#frozenBuffer");
        p->chunk_type=map->map(map->handle,LV2_ATOM__Chunk);
      }
    }
  }
  stmlib::Random::Seed(0x21);
  uint8_t* buffers[] = {p->delay[0], p->delay[1], p->delay[2]};
  p->processor.Init(buffers, p->reverb);
  // Original processor and synth share this RAM; initialize both once at boot.
  p->synth.Init(p->reverb);
  p->processor.Configure(beads::Processor::MEDIA_DIGITAL, false);
  p->gain.Init(48000.f, beads::GainControl::SOFT_CLIPPING_MODE_OFF, true);
  const unsigned rates[] = {48000, 32000, 48000, 24000};
  for (unsigned i = 0; i < 4; ++i) {
    p->input_converter[i].Init(48000, rates[i]);
    p->output_converter[i].Init(rates[i], 48000);
  }
  p->buffer_seconds = 4.f;
  p->rng = stmlib::Random::state();
  return p;
}
void connect_port(LV2_Handle h, uint32_t index, void* data) {
  if (index < PORT_COUNT) static_cast<Mala*>(h)->ports[index] = static_cast<float*>(data);
}
// Snapshot knobs/CV at the original 4 kHz boundary, independent of host blocks.
void prepare(Mala* p, unsigned offset) {
  float targets[mala::kPanelKnobs];
  const float defaults[]={.25f,.6f,.6f,0.f,.73f,0.f,0.f,0.f,0.f,.2f,.85f,.15f};
  for (unsigned i=0;i<mala::kPanelKnobs;++i)
    targets[i]=control(p,Port(i),defaults[i],i==PITCH ? -24.f : i>=TIME_AMOUNT && i<=PITCH_AMOUNT ? -1.f : 0.f,
                      i==PITCH ? 24.f : 1.f);
  p->panel.Process(targets,control(p,PANEL_RESPONSE)>=.5f);
  p->mask = static_cast<unsigned>(control(p, CONNECTIONS, 0, 0, 255));
  const bool connected = p->mask & 64;
  if (connected != p->seed_connected) {
    std::fill(std::begin(p->seed_delay), std::end(p->seed_delay), false);
    p->previous_seed = stmlib::GATE_FLAG_LOW;
    p->seed_connected = connected;
  }
  const bool hector_cv = control(p, CV_INPUT_UNITS) >= .5f;
  for (unsigned i = 0; i < 6; ++i) {
    float v = p->mask & (1u << i) ? sample(p, Port(TIME_CV + i), offset) : 0.f;
    // Poly uses one signal unit per five volts. Omitted/defaulted capability
    // retains legacy virtual volts. Audio and the two logic gates bypass this.
    if (hector_cv) v *= 5.f;
    const float coefficient = i < 3 ? .5f : (i == 5 ? .1f : 1.f);
    v = i == 3 ? bounded(v * 12.f, -60.f, 60.f)
        : bounded(v / 5.f, i < 3 ? -1.6f : -1.f, i < 3 ? 1.6f : 1.f);
    p->cv[i] += coefficient * (v - p->cv[i]);
  }
  p->parameters.time = {p->panel.value(TIME), p->panel.value(TIME_AMOUNT), p->cv[0], bool(p->mask & 1)};
  p->parameters.size = {p->panel.value(SIZE), p->panel.value(SIZE_AMOUNT), p->cv[1], bool(p->mask & 2)};
  p->parameters.shape = {p->panel.value(SHAPE), p->panel.value(SHAPE_AMOUNT), p->cv[2], bool(p->mask & 4)};
  p->parameters.pitch = {p->panel.value(PITCH), p->panel.value(PITCH_AMOUNT), p->cv[3], bool(p->mask & 8)};
  p->parameters.monophonic_mode = false;
  p->density = {p->panel.value(DENSITY), p->mask & 16 ? p->cv[4] : 0.f};
  const unsigned destination = static_cast<unsigned>(control(p, ASSIGN_DESTINATION, 0, 0, 3));
  float mixes[3];
  const Port knobs[] = {FEEDBACK, MIX, REVERB};
  const Port amounts[] = {FEEDBACK_CV_AMOUNT, MIX_CV_AMOUNT, REVERB_CV_AMOUNT};
  const float amount_defaults[] = {255.f, 0.f, 128.f};
  for (unsigned i = 0; i < 3; ++i) {
    const float amount = destination == 3
        ? control(p, amounts[i], amount_defaults[i], 0, 255) / 256.f
        : float(destination == i);
    mixes[i] = bounded(p->panel.value(knobs[i]) * 1.005f
                        + ((p->mask & 32 ? p->cv[5] : 0.f) - .002f) * amount, 0, 1);
  }
  p->mix = {mixes[0], mixes[1], mixes[2], control(p, GRAIN_TRIGGERS) >= .5f};
  p->output_normalization = control(p, OUTPUT_NORMALIZATION) >= .5f;
  p->output_connections = unsigned(std::round(control(p, OUTPUT_CONNECTIONS, 3, 0, 3)));
  p->seed = static_cast<beads::SeedButtonState>(static_cast<int>(std::round(control(p, SEED, 2, 0, 2))));
  p->requested_quality = int(std::round(control(p, QUALITY, 0, 0, 3)));
  // Missing appended ports retain the old 39-port unity-input contract.
  p->input_stage = control(p, INPUT_STAGE, 0) >= .5f;
  p->synth_enable = control(p, SYNTH_ENABLE, 0) >= .5f;
  p->buffer_autosave = control(p, BUFFER_AUTOSAVE, 0) >= .5f;
  p->freeze_release=unsigned(std::round(control(p,FREEZE_RELEASE,0,0,16777215)));
  if (!p->configured || p->release_baseline_pending) {
    p->previous_freeze_release=p->freeze_release; p->release_baseline_pending=false;
  }
  const bool latch=control(p,FREEZE)>=.5f;
  if (p->restored_freeze && (latch!=p->restore_freeze_anchor || p->freeze_release!=p->previous_freeze_release))
    p->restored_freeze=false;
  p->previous_freeze_release=p->freeze_release;
  p->audio_connections = unsigned(std::round(control(p, AUDIO_CONNECTIONS, 3, 0, 3)));
  p->input_gain = uint8_t(std::round(control(p, INPUT_GAIN, 0, 0, 255)));
  p->gain_relearn = unsigned(std::round(control(p, GAIN_RELEARN, 0, 0, 16777215)));
  // Restoring a graph's counter establishes its baseline, not a new button press.
  if (!p->configured || p->gain_baseline_pending) {
    p->previous_gain_relearn = p->gain_relearn; p->gain_baseline_pending=false;
  }
  // The existing Mono control remains a force-mono option for stereo patches.
  p->requested_mono = p->input_stage && !p->audio_connections && p->configured ? p->mono
      : control(p, MONO) >= .5f || (p->input_stage && p->audio_connections && p->audio_connections != 3);
}
void restart_codec(Mala* p, bool synth_mode, bool reset_gain) {
  p->synth_mode = synth_mode;
  p->no_input_blocks = 0;
  const unsigned rate_mode = synth_mode ? 0 : p->quality;
  p->gain.Init(synth_mode ? 48000.f : p->processor.sample_rate(),
      mala::ClippingMode(p->quality), reset_gain);
  p->input_converter[rate_mode].Reset();
  p->output_converter[rate_mode].Reset();
  p->output_routing.Reset();
  std::fill(std::begin(p->seed_delay), std::end(p->seed_delay), false);
  std::fill(std::begin(p->delayed_seed), std::end(p->delayed_seed), false);
  p->previous_seed = stmlib::GATE_FLAG_LOW;
  p->transition_blocks = 1000;
}
void process_block(Mala* p) {
  const bool frozen = std::any_of(std::begin(p->freeze), std::end(p->freeze), [](bool v) { return v; });
  // ui.cc saves the requested media even while frozen; beads.cc defers
  // Configure until neither Freeze nor the codec transition is active.
  const bool quality_changed = p->quality != unsigned(p->requested_quality);
  const bool mono_changed = p->mono != p->requested_mono;
  const bool synthesis_allowed = p->input_stage && p->synth_enable;
  // MonitorStateChange resets its timer during Freeze or codec restart. Audio
  // above .01 resets it below, so tails can delay entry beyond ten seconds.
  if (frozen || p->transition_blocks || !synthesis_allowed || p->audio_connections)
    p->no_input_blocks = 0;
  if (p->configured && !frozen && !p->transition_blocks && synthesis_allowed
      && !p->audio_connections && !p->synth_mode && p->no_input_blocks >= kSynthWaitBlocks)
    restart_codec(p, true, true);
  const bool leaving_synth = p->synth_mode && (!synthesis_allowed || p->audio_connections);
  // While unpatched, recording format stays intact. In Synth, quality controls
  // resolution directly (even frozen) and never changes its 48 kHz rate.
  const bool format_allowed = !p->input_stage || p->audio_connections;
  if (!p->configured || (!frozen && !p->transition_blocks
      && (leaving_synth || (!p->synth_mode && format_allowed && (quality_changed || mono_changed))))) {
      const bool initial = !p->configured;
      const beads::Processor::Media media[] = {beads::Processor::MEDIA_DIGITAL,
        beads::Processor::MEDIA_VINTAGE_DIGITAL, beads::Processor::MEDIA_CLEAN_TAPE,
        beads::Processor::MEDIA_DIRTY_TAPE};
      p->quality = p->requested_quality;
      p->mono = p->requested_mono;
      p->processor.Configure(media[p->quality], p->mono);
      // beads.cc resets learning for mono changes, retains it for media changes.
      p->gain.Init(p->processor.sample_rate(), mala::ClippingMode(p->quality), initial || mono_changed || leaving_synth);
      p->input_converter[p->quality].Reset();
      p->output_converter[p->quality].Reset();
      p->output_routing.Reset();
      if (!initial) restart_codec(p, false, mono_changed || leaving_synth);
      const float record_rate = p->quality == 2 ? 24000.f : p->processor.sample_rate();
      p->buffer_seconds = p->processor.remaining() / record_rate;
      // Original codec restart silences 1000 callbacks at 4 kHz (250 ms).
      // Instantiation chooses its initial mode without simulating device boot.
      p->transition_blocks = initial ? 0 : 1000;
      p->configured = true;
  }
  if (p->input_stage && !p->previous_input_stage)
    p->gain.Init(p->synth_mode ? 48000.f : p->processor.sample_rate(), mala::ClippingMode(p->quality), true);
  p->previous_input_stage = p->input_stage;
  if (p->gain_relearn != p->previous_gain_relearn) p->gain.Restart();
  p->previous_gain_relearn = p->gain_relearn;
  // Original gain sensing runs through a codec transition, with active=false.
  // Keep the legacy bypass's previous converter timing unchanged.
  beads::FloatFrame native_in[12], native_out[12];
  unsigned n = 0;
  if (p->input_stage || !p->transition_blocks) {
    n = p->input_converter[p->synth_mode ? 0 : p->quality].Process(p->input, 12, native_in);
    if (p->input_stage) mala::ProcessInput(p->gain, !p->transition_blocks,
        p->input_gain, p->audio_connections, native_in, n);
  }
  if (p->transition_blocks) {
    --p->transition_blocks;
    std::fill(std::begin(p->output), std::end(p->output), beads::FloatFrame{0, 0});
    p->backup.Tick(frozen,p->buffer_autosave,p->synth_mode,p->processor);
    return;
  }
  bool native_freeze[12];
  stmlib::GateFlags events[12];
  for (unsigned i = 0; i < n; ++i) {
    bool gate = false, freeze = false;
    for (unsigned j = i * 12 / n; j < (i + 1) * 12 / n; ++j) {
      gate |= p->delayed_seed[j];
      freeze |= p->freeze[j];
    }
    native_freeze[i] = freeze;
    events[i] = p->previous_seed = stmlib::ExtractGateFlags(p->previous_seed, gate);
  }
  if (p->synth_mode) {
    // Hardware media enum runs Dirty/Clean/Vintage/Digital; the retained LV2
    // contract presents Bright/Cold/Sunny/Scorched in the opposite order.
    const beads::Synth::Resolution resolutions[] = {beads::Synth::RESOLUTION_16_BIT,
        beads::Synth::RESOLUTION_7_BIT, beads::Synth::RESOLUTION_16_BIT_6_BIT,
        beads::Synth::RESOLUTION_4_BIT};
    p->synth.Render(p->seed, p->seed_connected ? events : nullptr, native_freeze,
        resolutions[p->requested_quality], p->density, p->parameters,
        p->mix, native_out, n);
  } else {
    p->processor.Process(p->seed, p->seed_connected ? events : nullptr, native_freeze,
        p->density, p->parameters, p->mix, native_in, native_out, n);
    if (synthesis_allowed && !p->audio_connections && !frozen) {
      const bool audible = std::any_of(native_out, native_out + n,
          [](const beads::FloatFrame& f) { return std::fabs(f.l) > .01f || std::fabs(f.r) > .01f; });
      p->no_input_blocks = audible ? 0 : p->no_input_blocks + 1;
    }
  }
  p->output_routing.Process(native_out, n,
      p->output_converter[p->synth_mode ? 0 : p->quality], p->output,
      p->mix.output_gate, p->output_normalization, p->output_connections);
  p->backup.Tick(frozen,p->buffer_autosave,p->synth_mode,p->processor);
}
void run(LV2_Handle h, uint32_t count) {
  auto* p = static_cast<Mala*>(h);
  stmlib::Random::Seed(p->rng);
  for (unsigned i = 0; i < count; ++i) {
    if (!p->phase) prepare(p, i);
    // One host control block of fixed buffering avoids truncated Sunny Tape
    // ratio-2 calls and makes native timing invariant to host quantum size.
    p->input[p->phase] = {sample(p, LEFT_IN, i), sample(p, RIGHT_IN, i)};
    if (p->ports[LEFT_OUT]) p->ports[LEFT_OUT][i] = p->output[p->phase].l;
    if (p->ports[RIGHT_OUT]) p->ports[RIGHT_OUT][i] = p->output[p->phase].r;
    p->freeze[p->phase] = p->restored_freeze || control(p, FREEZE) >= .5f
        || ((p->mask & 128) && sample(p, FREEZE_GATE, i) >= .5f);
    p->delayed_seed[p->phase] = p->seed_delay[p->delay_index];
    p->seed_delay[p->delay_index] = p->seed_connected && sample(p, SEED_GATE, i) >= .5f;
    p->delay_index = (p->delay_index + 1) % kSeedDelay;
    if (p->ports[ACTIVE_FREEZE]) *p->ports[ACTIVE_FREEZE] = p->freeze[p->phase] ? 1.f : 0.f;
    if (++p->phase == 12) { process_block(p); p->phase = 0; }
  }
  if (p->ports[ACTIVE_QUALITY]) *p->ports[ACTIVE_QUALITY] = float(p->synth_mode ? p->requested_quality : p->quality);
  if (p->ports[ACTIVE_MONO]) *p->ports[ACTIVE_MONO] = p->mono ? 1.f : 0.f;
  if (p->ports[BUFFER_SECONDS]) *p->ports[BUFFER_SECONDS] = p->buffer_seconds;
  if (p->ports[MODE_TRANSITION]) *p->ports[MODE_TRANSITION] = p->transition_blocks ? 1.f : 0.f;
  if (p->ports[LATENCY]) *p->ports[LATENCY] = 12.f + (p->synth_mode ? 0.f : p->quality == 1 ? 96.f : p->quality == 3 ? 192.f : 0.f);
  if (p->ports[GAIN_ADJUSTING]) *p->ports[GAIN_ADJUSTING] = p->input_stage && p->gain.adjusting() ? 1.f : 0.f;
  if (p->ports[INPUT_VU]) *p->ports[INPUT_VU] = p->input_stage ? float(p->gain.vu_meter()) : 0.f;
  if (p->ports[ACTIVE_SYNTH]) *p->ports[ACTIVE_SYNTH] = p->synth_mode ? 1.f : 0.f;
  if (p->ports[SYNTH_WAIT_SECONDS]) *p->ports[SYNTH_WAIT_SECONDS] = float(p->no_input_blocks) / 4000.f;
  if (p->ports[BUFFER_STATE]) *p->ports[BUFFER_STATE]=p->backup.Status(p->buffer_autosave,p->synth_mode);
  if (p->ports[BUFFER_WAIT_SECONDS]) *p->ports[BUFFER_WAIT_SECONDS]=p->backup.WaitSeconds();
  if (p->ports[BUFFER_EPOCH]) *p->ports[BUFFER_EPOCH]=p->backup.Epoch();
  p->rng = stmlib::Random::state();
}
void cleanup(LV2_Handle h) {
  auto* p = static_cast<Mala*>(h);
  p->~Mala(); std::free(p);
}
LV2_State_Status save_state(LV2_Handle h, LV2_State_Store_Function store,
    LV2_State_Handle handle, uint32_t, const LV2_Feature* const*) {
  auto* p=static_cast<Mala*>(h);
  if (!p->state_key || !p->chunk_type) return LV2_STATE_ERR_NO_FEATURE;
  const int slot=p->backup.Pin();
  uint8_t empty[mala::kFrozenHeader]; mala::EmptyFrozen(empty);
  const LV2_State_Status result=store(handle,p->state_key,slot<0 ? empty : p->backup.Data(slot),
      slot<0 ? mala::kFrozenHeader : mala::kFrozenSize,p->chunk_type,LV2_STATE_IS_POD);
  if (slot>=0) p->backup.Unpin(slot);
  return result;
}
LV2_State_Status restore_state(LV2_Handle h, LV2_State_Retrieve_Function retrieve,
    LV2_State_Handle handle, uint32_t, const LV2_Feature* const*) {
  auto* p=static_cast<Mala*>(h);
  if (!p->state_key || !p->chunk_type) return LV2_STATE_ERR_NO_FEATURE;
  size_t size=0; uint32_t type=0,flags=0;
  const auto* data=static_cast<const uint8_t*>(retrieve(handle,p->state_key,&size,&type,&flags));
  if (!data) { p->backup.Clear(); p->restored_freeze=false; return LV2_STATE_SUCCESS; }
  if (type!=p->chunk_type || !(flags & LV2_STATE_IS_POD) || !mala::ValidFrozen(data,size)) return LV2_STATE_ERR_BAD_TYPE;
  // Host port values may be applied after restore(). Explicit LV2 snapshots
  // therefore restore independently of the capture-enable port. Desktop cold
  // startup honors disabled autosave before invoking this interface.
  if (size==mala::kFrozenHeader) {
    p->backup.Clear(); p->restored_freeze=false; return LV2_STATE_SUCCESS;
  }
  p->quality=3-data[16]; p->mono=data[17];
  p->processor.Configure(beads::Processor::Media(data[16]),p->mono);
  for (size_t offset=0; offset<mala::kFrozenBytes;) {
    const size_t n=std::min(mala::kFrozenBytes-offset,262144-offset%262144);
    std::memcpy(p->processor.delay_buffer_raw_bytes(offset),data+mala::kFrozenHeader+offset,n); offset+=n;
  }
  *p->processor.mutable_delay_write_ptr()=mala::Get32(data+12);
  p->backup.Adopt(data); p->configured=true; p->restored_freeze=true;
  p->buffer_autosave=control(p,BUFFER_AUTOSAVE)>=.5f;
  p->restore_freeze_anchor=control(p,FREEZE)>=.5f; p->release_baseline_pending=true;
  p->gain_baseline_pending=true;
  p->previous_gain_relearn=unsigned(control(p,GAIN_RELEARN,0,0,16777215));
  p->previous_input_stage=control(p,INPUT_STAGE)>=.5f;
  restart_codec(p,false,true);
  const float record_rate=p->quality==2 ? 24000.f : p->processor.sample_rate();
  p->buffer_seconds=p->processor.remaining()/record_rate;
  std::fill(std::begin(p->output),std::end(p->output),beads::FloatFrame{0,0});
  p->phase=0;
  if (p->ports[ACTIVE_FREEZE]) *p->ports[ACTIVE_FREEZE]=1.f;
  return LV2_STATE_SUCCESS;
}
const LV2_State_Interface state_interface{save_state,restore_state};
const void* extension_data(const char* uri) {
  return !std::strcmp(uri,LV2_STATE__interface) ? &state_interface : nullptr;
}
const LV2_Descriptor descriptor{kURI, instantiate, connect_port, nullptr, run,
                               nullptr, cleanup, extension_data};
}
extern "C" LV2_SYMBOL_EXPORT
const LV2_Descriptor* lv2_descriptor(uint32_t index) { return index ? nullptr : &descriptor; }
extern "C" LV2_SYMBOL_EXPORT
float mala_knob_response(uint32_t law, float position) { return mala::KnobTarget(law,position); }
