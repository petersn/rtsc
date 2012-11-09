// Filesystem used in RTSC compiled binaries.

using namespace std;
#include <iostream>
#include "rtscfs.h"
#include "bzlib.h"

typedef struct {
	void* data;
	size_t size;
} cache_t;

void* rtscfs_image;
cache_t* rtscfs_data_cache;

void rtscfs_init(void* fs) {
	rtscfs_image = fs;
	rtscfs_header_t* header = (rtscfs_header_t*) rtscfs_image;
	uint64_t count = header->fs_count;
	rtscfs_data_cache = new cache_t[count];
	rtscfs_entry_t* entry = (rtscfs_entry_t*) (rtscfs_image + header->fs_offset);
	for (int index=0; index<count; index++) {
		if (entry->entry_flags & RTSCFS_FLAG_BZ2) {
			uint64_t bz2_decompressed_length = *((uint64_t*)(rtscfs_image + entry->entry_offset));
			char* return_address = new char[bz2_decompressed_length];
			unsigned int bz2_decompressed_length_verify = bz2_decompressed_length;
//			cout << "Decompressing entry " << index << " of length " << entry->entry_size << " to " << bz2_decompressed_length << endl;
			int success = BZ2_bzBuffToBuffDecompress(return_address, &bz2_decompressed_length_verify, (char*)(rtscfs_image + entry->entry_offset + 8), entry->entry_size - 8, 0, 0);
			if (bz2_decompressed_length != bz2_decompressed_length_verify)
				cerr << "BZ2 error: entry " << index << " should have been " << bz2_decompressed_length << " long, but was " << bz2_decompressed_length_verify << " long instead." << endl;
//			cout << "Got " << success << " and " << bz2_decompressed_length_verify << " bytes out." << endl;
			rtscfs_data_cache[index].data = return_address;
			rtscfs_data_cache[index].size = bz2_decompressed_length_verify;
		} else {
//			cout << "Passing through." << endl;
			rtscfs_data_cache[index].data = rtscfs_image + entry->entry_offset;
			rtscfs_data_cache[index].size = entry->entry_size;
		}
		entry++;
	}
}

void* rtscfs_find(const char* key, size_t* length) {
	int key_length = strlen(key);
	rtscfs_header_t* header = (rtscfs_header_t*) rtscfs_image;
	uint64_t count = header->fs_count;
	rtscfs_entry_t* entry = (rtscfs_entry_t*) (rtscfs_image + header->fs_offset);
	for (int index=0; index<count; index++) {
		if (entry->entry_name_size == key_length &&
			memcmp(rtscfs_image + entry->entry_name_offset, key, key_length) == 0) {
			if (length != NULL)
				*length = rtscfs_data_cache[index].size;
			return rtscfs_data_cache[index].data;
		}
		entry++;
	}
	return NULL;
}

/*
int 
*/
