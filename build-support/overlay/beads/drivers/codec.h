// Lab type-only shim; no codec driver implementation.
#pragma once
#include <cstdint>
namespace beads { class Codec { public:
struct Frame { int32_t l; int32_t r; } __attribute__((packed, aligned(4)));
}; }
