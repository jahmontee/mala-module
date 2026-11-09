// SPDX-License-Identifier: MIT. Beads backup semantics, without STM32 flash code.
#pragma once
#include "beads/dsp/processor.h"
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>

namespace mala {
constexpr size_t kFrozenBytes = beads::kDelayBufferSizeBits / 8;
constexpr size_t kFrozenHeader = 32;
constexpr size_t kFrozenSize = kFrozenHeader + kFrozenBytes;
constexpr uint32_t kFrozenTag = 0x5a5a5246;  // Original FRZZ tag.
inline uint32_t Get32(const uint8_t* p) {
  return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
inline void Put32(uint8_t* p, uint32_t v) {
  for (unsigned i=0; i<4; ++i) p[i]=uint8_t(v >> (8*i));
}
inline uint32_t FrozenCRC(uint32_t crc, const uint8_t* data, size_t size) {
  while (size--) {
    crc ^= *data++;
    for (unsigned i=0; i<8; ++i) crc=(crc >> 1) ^ (0xedb88320u & (0u-(crc & 1u)));
  }
  return crc;
}
inline void EmptyFrozen(uint8_t* p) {
  std::memset(p,0,kFrozenHeader); Put32(p,kFrozenTag); Put32(p+4,1);
}
inline bool ValidFrozen(const uint8_t* data, size_t size) {
  if (!data || size<kFrozenHeader || Get32(data)!=kFrozenTag || Get32(data+4)!=1) return false;
  for (unsigned i : {18u,19u,24u,25u,26u,27u,28u,29u,30u,31u}) if (data[i]) return false;
  if (!Get32(data+8)) {
    uint8_t empty[kFrozenHeader]; EmptyFrozen(empty);
    return size==kFrozenHeader && !std::memcmp(empty,data,kFrozenHeader);
  }
  if (size!=kFrozenSize || Get32(data+8)!=kFrozenBytes || data[16]>3 || data[17]>1) return false;
  const unsigned bits[] = {8,12,12,16};
  const uint32_t capacity=beads::kDelayBufferSizeBits / (bits[data[16]] * (data[17] ? 1 : 2));
  return Get32(data+12)<capacity && Get32(data+20)==~FrozenCRC(FrozenCRC(~0u,data,20),data+kFrozenHeader,kFrozenBytes);
}

// Audio captures at most 2 KiB per 4 kHz callback. A published slot is immutable
// while host save callbacks pin it. Audio never waits, allocates or writes files.
class FrozenBuffer {
 public:
  static_assert(std::atomic<int>::is_always_lock_free && std::atomic<uint32_t>::is_always_lock_free,
      "Frozen buffer publication requires lock-free integer atomics");
  struct Slot { std::atomic<int> readers{0}; uint8_t data[kFrozenSize]; };
  FrozenBuffer() : published_(-1), epoch_(0), writing_(-1), offset_(0),
                   wait_(0), crc_(~0u), done_(false) {}
  void Clear() {
    const bool changed=published_.exchange(-1,std::memory_order_acq_rel)>=0 || writing_>=0;
    if (writing_>=0) slots_[writing_].readers.store(0,std::memory_order_release);
    writing_=-1; wait_=0; done_=false;
    if (changed) Bump();
  }
  void Tick(bool frozen, bool enabled, bool synth, beads::Processor& processor) {
    if (!frozen || !enabled || synth) { Clear(); return; }
    if (done_) return;
    if (wait_<40000) ++wait_;
    if (wait_<40000) return;
    if (writing_<0) {
      for (int i=0; i<3; ++i) {
        if (i==published_.load(std::memory_order_acquire)) continue;
        int expected=0;
        if (slots_[i].readers.compare_exchange_strong(expected,-1,std::memory_order_acq_rel)) {
          writing_=i; break;
        }
      }
      if (writing_<0) return;  // Retry later, without blocking the audio callback.
      uint8_t* h=slots_[writing_].data; EmptyFrozen(h);
      Put32(h+8,kFrozenBytes); Put32(h+12,*processor.mutable_delay_write_ptr());
      h[16]=processor.media(); h[17]=processor.mono(); offset_=0; crc_=FrozenCRC(~0u,h,20);
    }
    const size_t n=std::min<size_t>({2048,kFrozenBytes-offset_,262144-offset_%262144});
    const uint8_t* from=processor.delay_buffer_raw_bytes(offset_);
    uint8_t* to=slots_[writing_].data+kFrozenHeader+offset_;
    std::memcpy(to,from,n); crc_=FrozenCRC(crc_,to,n); offset_+=n;
    if (offset_==kFrozenBytes) {
      Put32(slots_[writing_].data+20,~crc_);
      slots_[writing_].readers.store(0,std::memory_order_release);
      published_.store(writing_,std::memory_order_release);
      writing_=-1; done_=true; Bump();
    }
  }
  // Save may overlap run(). Retry if publication changes while pinning a slot.
  int Pin() {
    for (;;) {
      const int i=published_.load(std::memory_order_acquire);
      if (i<0) return -1;
      int readers=slots_[i].readers.load(std::memory_order_acquire);
      if (readers<0 || !slots_[i].readers.compare_exchange_weak(readers,readers+1,std::memory_order_acq_rel)) continue;
      if (published_.load(std::memory_order_acquire)==i) return i;
      Unpin(i);
    }
  }
  const uint8_t* Data(int i) const { return slots_[i].data; }
  void Unpin(int i) { slots_[i].readers.fetch_sub(1,std::memory_order_release); }
  // Restore is in LV2's Instantiation threading class: no concurrent run/save.
  void Adopt(const uint8_t* data) {
    Clear(); std::memcpy(slots_[0].data,data,kFrozenSize);
    published_.store(0,std::memory_order_release); wait_=40000; done_=true; Bump();
  }
  unsigned Status(bool enabled, bool synth) const {
    return !enabled ? 0 : synth ? 4 : done_ ? 3 : writing_>=0 ? 2 : wait_ ? 1 : 0;
  }
  float WaitSeconds() const { return float(wait_)/4000.f; }
  uint32_t Epoch() const { return epoch_.load(std::memory_order_acquire); }
 private:
  void Bump() { epoch_.store((epoch_.load(std::memory_order_relaxed)+1)%16777216,std::memory_order_release); }
  Slot slots_[3];
  std::atomic<int> published_;
  std::atomic<uint32_t> epoch_;
  int writing_;
  size_t offset_;
  unsigned wait_;
  uint32_t crc_;
  bool done_;
};
}  // namespace mala
