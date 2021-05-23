#define FNAME_SIZE 32
typedef struct filesystem_metadata
{
    int32_t tot_directories;
    int32_t tot_inodes;
    int32_t tot_data_blocks;
    uint32_t* boot_block;
    uint32_t* inode_block;
    uint32_t* data_block;
} filesystem_metadata_t;

typedef struct dentry {
    uint8_t* fname;
    uint32_t ftype;
    uint32_t inode;
} dentry_t;

typedef struct file_descriptor {
    uint8_t* fname;
    uint32_t ftype;
    uint32_t inode;
    uint32_t size;
    uint32_t offset;
} file_descriptor_t;

extern int32_t read_dentry_by_name(uint8_t* fname, dentry_t* dentry);
extern int32_t read_dentry_by_index(const uint32_t index , dentry_t* dentry);
extern int32_t read_data(uint32_t inode, uint32_t offset, uint8_t* buff, uint32_t length);
extern int32_t fs_init(uint32_t fs_start, uint32_t fs_end);
extern int32_t get_size(uint32_t inode);
extern int32_t fopen(uint8_t* fname);
extern int32_t fread(uint8_t* buff, const uint32_t size);
extern int32_t fclose(const uint8_t* fname);
extern int32_t fwrite(const uint8_t* fname);
filesystem_metadata_t fs_meta;

int32_t dread(uint8_t* buff, int32_t file_pos);

int32_t dir_open(uint8_t* fname);
int32_t dir_read(uint8_t* buff, int32_t size);
int32_t dir_close(const uint8_t* fname);
int32_t dir_write();
