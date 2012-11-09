// Filesystem used in RTSC compiled binaries.

#ifndef _RTSCFS_H
#define _RTSCFS_H

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
	uint64_t fs_count;
	uint64_t fs_offset;
} rtscfs_header_t;

typedef struct {
	uint64_t entry_name_size;
	uint64_t entry_name_offset;
	uint64_t entry_size;
	uint64_t entry_offset;
	uint64_t entry_flags;
} rtscfs_entry_t;

#define RTSCFS_FLAG_BZ2 (((uint64_t)1)<<0)

void rtscfs_init(void* fs);
void* rtscfs_find(const char* key, size_t* length);

#endif

