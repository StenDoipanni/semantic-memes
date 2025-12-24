// Stub library to provide missing Intel JIT profiler symbols
// This is a workaround for PyTorch MKL library conflicts

#include <stdint.h>

// Stub functions for Intel JIT profiler
void iJIT_NotifyEvent(void* pEvent) {
    (void)pEvent;
}

int iJIT_IsProfilingActive(void) {
    return 0;
}

unsigned int iJIT_GetNewMethodID(void) {
    return 0;
}

