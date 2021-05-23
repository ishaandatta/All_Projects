#include "lib.h"
#include "debug.h"
#include "filesystem.h"
#include "task.h"

#define BLOCK_SIZE 4096
#define DIR_ENTRY_OFFSET 64
#define DIR_ENTRY_FTYPE_OFFSET 8
#define DIR_ENTRY_INODE_OFFSET 9
#define MAX_DIRS 63
#define INT32_PTR_SIZE 4
#define STR_END_CHAR '\0'


file_descriptor_t fd;



/* 
 *  fs_init
 *   DESCRIPTION: Initializes filesystem by setting up global variables
 *   INPUTS: Start and end address of filesystem mapped to memory
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if FS is intialized correctly else -1 
 *   SIDE EFFECTS: NIL
 */

int32_t fs_init(uint32_t fs_start, uint32_t fs_end)
{
    if(fs_end<fs_start)
    {
        return -1;
    }
    fs_meta.boot_block = (uint32_t* )fs_start;
    fs_meta.tot_directories = *fs_meta.boot_block;
    fs_meta.tot_directories = *fs_meta.boot_block;
    fs_meta.tot_inodes = *(fs_meta.boot_block+1);
    fs_meta.tot_data_blocks = *(fs_meta.boot_block+2);
    fs_meta.inode_block = (uint32_t* )(fs_start+BLOCK_SIZE);
    fs_meta.data_block = (uint32_t* )(fs_start+BLOCK_SIZE+fs_meta.tot_inodes*BLOCK_SIZE);
    return 0;
}


/* 
 *  read_dentry_by_name
 *   DESCRIPTION: Reads directory entry by name 
 *   INPUTS: fname -- filename to parse for, dentry -- pointer to directory entry to be returned
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if dentry found correctly else -1 
 *   SIDE EFFECTS: dentry populated with correct directory entry
 */

int32_t read_dentry_by_name(uint8_t* fname, dentry_t* dentry)
{
    if(dentry==NULL)
    {
        return -1;
    }

    int i;
    for(i=DIR_ENTRY_OFFSET; i<DIR_ENTRY_OFFSET*(fs_meta.tot_directories+1); i+=DIR_ENTRY_OFFSET)
    {
        int ch = 1;
        uint8_t* fname_iter = fname;
        int j = 0;
        while(*fname_iter!=STR_END_CHAR && j<DIR_ENTRY_FTYPE_OFFSET*INT32_PTR_SIZE)
        {
            if(*fname_iter!=*(((char *)fs_meta.boot_block)+i+j))
            {
                ch  = 0;
                break;
            }
            fname_iter++;
            j++;
        }

        if(*fname_iter!='\0')
        {
            ch = 0;
        }

        if(j<DIR_ENTRY_FTYPE_OFFSET*INT32_PTR_SIZE && *(((char *)fs_meta.boot_block)+i+j)!=STR_END_CHAR)
        {
            ch = 0;
        }
        if(ch==1)
        {
            dentry->fname = fname;
            dentry->ftype = *(fs_meta.boot_block+DIR_ENTRY_FTYPE_OFFSET+i/INT32_PTR_SIZE);
            dentry->inode = *(fs_meta.boot_block+DIR_ENTRY_INODE_OFFSET+i/INT32_PTR_SIZE);
            return 0;
        }
    }
    return -1;
}


/* 
 *  read_dentry_by_index
 *   DESCRIPTION: Reads directory entry by index 
 *   INPUTS: index -- directory index to locate, dentry -- pointer to directory entry to be returned
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if dentry found correctly else -1 
 *   SIDE EFFECTS: dentry populated with correct directory entry
 */

int32_t read_dentry_by_index(const uint32_t index , dentry_t* dentry)
{
    int j;
    if(index>=MAX_DIRS || dentry==NULL)
    {
        return -1;
    }

    for(j=0; j<FNAME_SIZE; j++)
    {
        dentry->fname[j] = *(((uint8_t *)fs_meta.boot_block)+j+((index+1)*DIR_ENTRY_OFFSET));
    }
    dentry->ftype = *(((uint8_t *)fs_meta.boot_block)+DIR_ENTRY_FTYPE_OFFSET*INT32_PTR_SIZE+(index+1)*DIR_ENTRY_OFFSET);
    dentry->inode = *(((uint8_t *)fs_meta.boot_block)+DIR_ENTRY_INODE_OFFSET*INT32_PTR_SIZE+(index+1)*DIR_ENTRY_OFFSET);
    return 0;
}

/* 
 *  get_size
 *   DESCRIPTION: Gets size of file from inode 
 *   INPUTS: inode -- inode index
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if valid size returned else -1 
 *   SIDE EFFECTS: NIL
 */
int32_t get_size(uint32_t inode)
{
    if(inode>=fs_meta.tot_inodes)
    {
        return -1;
    }
    uint32_t* inode_address = fs_meta.inode_block+(inode)*(BLOCK_SIZE/INT32_PTR_SIZE);
    uint32_t num_bytes = *inode_address;
    return num_bytes;
}

/* 
 *  read_data
 *   DESCRIPTION: Reads data in opened file 
 *   INPUTS: inode -- inode number to read from, offset -- offset in inode to start reading from, 
                buff -- buffer to populate, length -- size in bytes to read
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if data read was valid, else -1 
 *   SIDE EFFECTS: buff populated with correct length of data in file
 */
 
int32_t read_data(uint32_t inode, uint32_t offset, uint8_t* buff, uint32_t length)
{
    if(inode>=fs_meta.tot_inodes || buff==NULL)
    {
        return -1;
    }

    uint32_t* inode_address = fs_meta.inode_block+(inode)*(BLOCK_SIZE/INT32_PTR_SIZE);
    uint32_t num_bytes = *inode_address;
    if(offset+length>num_bytes)
    {
        length = num_bytes-offset;
    }

    int i;
    uint32_t buff_ptr = 0;
    for(i=(offset/BLOCK_SIZE); i<=(offset+length)/BLOCK_SIZE; i++)
    {
        uint32_t block_no = *(inode_address+(i+1));
        uint8_t* block_address = (uint8_t *)(fs_meta.data_block+(block_no)*(BLOCK_SIZE/INT32_PTR_SIZE));
        uint32_t block_ptr = (i==(offset/BLOCK_SIZE))>0?offset%BLOCK_SIZE:0;
        while(buff_ptr<length && block_ptr<BLOCK_SIZE)
        {
            if (*(block_address+block_ptr) != '\r')
                *(buff+buff_ptr) = *(block_address+block_ptr);
            else
                *(buff+buff_ptr) = ' ';
            buff_ptr++;
            block_ptr++;
        }
    }
    return length;
}

/* 
 *  fopen
 *   DESCRIPTION: Opens directory entry (file) corresponding to filename passed in 
 *   INPUTS: fname -- filename to parse for
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if file opened correctly else -1 
 *   SIDE EFFECTS: Sets values in global file struct
 */
int32_t fopen(uint8_t* fname){
    dentry_t dentry;
    fd.fname = fname;
    if(read_dentry_by_name(fname, &dentry)){
        return -1;
    }
    fd.ftype = dentry.ftype;
    fd.size = get_size(dentry.inode);
    fd.inode = dentry.inode;
    fd.offset = 0;
    return 0;
}

/* 
 *  fwrite
 *   DESCRIPTION: Writes to opened file
 *   INPUTS: fname -- filename to write to
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if write successful else -1 
 *   SIDE EFFECTS: 
 */
int32_t fwrite(const uint8_t* fname){
    return -1;
}

/* 
 *  fread
 *   DESCRIPTION: Fills buffer with data in opened file
 *   INPUTS: buff -- buffer to populate, size -- size in bytes to read
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if read successful else -1 
 *   SIDE EFFECTS: dentry populated with correct directory entry
 */
int32_t fread(uint8_t* buff, const uint32_t size){
    if(fd.offset >= fd.size || fd.fname == 0){
        return -1;
    }
    if(read_data(fd.inode, fd.offset, buff, size) == -1){
        printf("read_data failed\n");
        return -1;
    }
    fd.offset += size;
    return 0;
}

/* 
 *  fclose
 *   DESCRIPTION: Closes opened file (resets global structs associated with opened file)
 *   INPUTS: fname -- filename to close
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 if file closed correctly else -1 
 *   SIDE EFFECTS: resets global structs associated with opened file
 */
int32_t fclose(const uint8_t* fname){
    fd.fname = STR_END_CHAR;
    fd.ftype = 0;
    fd.inode = NULL;
    fd.size = 0;
    fd.offset = 0;
    return 0;
}

/* 
 *  dread
 *   DESCRIPTION: Reads file name into buffer 
 *   INPUTS: buff -- buffer to populate, pos -- position of directory entry
 *   OUTPUTS: NIL
 *   RETURN VALUE: length of file if successful, else -1 
 *   SIDE EFFECTS: buff populated with filename
 */

int32_t dread(uint8_t* buff, int32_t file_pos)
{
    int j;
	uint8_t fname[FNAME_SIZE+1];
	dentry_t dentry;
	dentry.fname = fname;
    if (file_pos > fs_meta.tot_directories){
        return 0;
    }
    read_dentry_by_index(file_pos, &dentry);
    for (j = 0; j < strlen((int8_t*)dentry.fname); j++){
        buff[j] = dentry.fname[j];
    }
    return j;
}

int32_t dir_open(uint8_t* fname){
    if (*fname != '.'){
        return -1;
    }
    return 0;
}

int32_t dir_read(uint8_t* buff, int32_t file_pos){
    return dread(buff, file_pos);
}

int32_t dir_close(const uint8_t* fname){
    return 0;
}

int32_t dir_write(){
    return -1;
}
