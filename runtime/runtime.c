#include "u310.h"
#include "u310_native.h"
#include "../api/bounds.h"
typedef uintptr_t word;
typedef word (*call0)(void);
typedef word (*call1)(word);
typedef word (*call2)(word, word);
typedef word (*call3)(word, word, word);
typedef word (*call4)(word, word, word, word);
typedef word (*call5)(word, word, word, word, word);
static word *exports;
static unsigned exit_requested;
static unsigned shutdown_called;
static unsigned redraw_pending;
#ifdef U310_TARGET_U880
/* U880 V10b: the export table has two extra slots before the UI group, so
 * groups from 0x48 move up by 8 bytes; the graphics group lost one method at
 * 0x08 and every method from 0x0c up moves down by 4 (checked against the
 * original Calculator.pxo of both supported firmwares). */
static unsigned target_group(unsigned api) { return api >= 0x48 ? api + 8 : api; }
static unsigned target_offset(unsigned api, unsigned offset) {
    return (api == 0x18 && offset >= 0x0c) ? offset - 4 : offset;
}
#else
static unsigned target_group(unsigned api) { return api; }
static unsigned target_offset(unsigned api, unsigned offset) { (void)api; return offset; }
#endif
static word method(unsigned api, unsigned offset) {
    return *(word *)((unsigned char *)exports[target_group(api)/4] + target_offset(api,offset));
}
uintptr_t u310_native_method(uint32_t group,uint32_t offset) {
#ifdef U310_TARGET_U880
    (void)group; (void)offset;
    return 0; /* the catalog bounds are from U310 and have not been validated for U880 */
#endif
    if (!exports || (group & 3) || (offset & 3) || group/4 >= U310_NATIVE_GROUP_COUNT)
        return 0;
    if (offset/4 >= u310_native_counts[group/4]) return 0;
    word pointer=method(group,offset);
    if (pointer==0x89c389 || (pointer&~1u)<0x5c000 || (pointer&~1u)>=U310_NATIVE_CODE_END || (!(pointer&1) && (pointer&3)))
        return 0;
    return pointer;
}
uintptr_t u310_native_exports(void) { return (uintptr_t)exports; }
u310_file u310_file_create(const uint16_t *path) {
    if (!path) return 0;
    return ((call3)method(0x38,0x0c))((word)path,0,0);
}
u310_file u310_file_open_update(const uint16_t *path) {
    if (!path) return 0;
    return ((call2)method(0x38,0x10))((word)path,0);
}
int32_t u310_file_write(u310_file file,const void *buffer,uint32_t size) {
    if (!file || (!buffer && size)) return -1;
    return (int32_t)((call3)method(0x38,0x20))(file,(word)buffer,size);
}
void *u310_alloc(size_t size) {
    if (!size) return 0;
    return (void *)((call3)method(0x2c,0))((word)size,(word)"u310sdk",0);
}
void u310_free(void *pointer) {
    if (pointer) ((call3)method(0x2c,4))((word)pointer,(word)"u310sdk",0);
}
int u310_get_surface(u310_surface *surface) {
    if (!surface) return 0;
    return (int)((call2)method(0x18,0x1c))((word)-1,(word)surface);
}
u310_file u310_file_open_read(const uint16_t *path) {
    if (!path) return 0;
    return ((call2)method(0x38,0x10))((word)path,1);
}
int32_t u310_file_read(u310_file file,void *buffer,uint32_t size) {
    if (!file || (!buffer && size)) return -1;
    return (int32_t)((call3)method(0x38,0x1c))(file,(word)buffer,size);
}
void u310_file_close(u310_file file) {
    if (file) ((call1)method(0x38,0x14))(file);
}
size_t u310_utf16_length(const uint16_t *text) {
    return (size_t)((call1)method(0x68,0x10))((word)text);
}
uint32_t u310_clock_raw(void) {return (uint32_t)((call0)method(0x50,0x08))();}
void u310_request_redraw(void) {
    if (!exit_requested && !redraw_pending) {
        redraw_pending=1;
        if (!((call4)method(0x08,0))((word)-6,0x6b,0,0)) redraw_pending=0;
    }
}
void u310_exit(void) {
    if (!exit_requested && app_can_exit()) {
#ifdef U310_TARGET_U880
        /* Original U880 Calculator.pxo, BACK handler at code+0x31f4:
         * TaskInfo's close callback owns the process/menu transition. */
        static const uint16_t name[]=u"TaskInfo";
        word handle=((call1)method(0x30,8))((word)name);
        if (!handle || handle==(word)-1) return;
        word task=((call1)method(0x30,12))(handle);
        if (!task) return;
        word close=*(word *)(task+0x148);
        if (!close) return;
        exit_requested=1;
        ((call3)close)(0,0,2);
#else
        exit_requested=1;
        /* Queue process destruction; never free this PXO on its own stack. */
        ((call4)method(0x08,0))((word)-6,2,0,0);
#endif
    }
}
__attribute__((weak)) void app_shutdown(void) {}
__attribute__((weak)) int app_can_exit(void) {return 1;}
__attribute__((used)) void pxo_init(const word *imports) {
    if (imports) exports = (word *)imports[0];
}
void u310_clear(uint32_t color) {
    ((call0)method(0x18,0x40))();
    u310_fill_rect(0,0,175,219,color);
}
void u310_fill_rect(int left,int top,int right,int bottom,uint32_t color) {
    ((call5)method(0x18,0x80))((word)left,(word)top,(word)right,(word)bottom,color);
}
void u310_draw_bitmap(int x, int y, const void *bitmap) {
    ((call3)method(0x18,0xc0))((word)x,(word)y,(word)bitmap);
}
void u310_present(void) { ((call0)method(0x18,0x0c))(); }
__attribute__((weak)) void app_event(uint32_t event, uint32_t parameter) {
    (void)event; (void)parameter;
}
static word ui_event(word event, word parameter) {
#ifdef U310_TARGET_U880
    if (event==U310_UI_KEY_DOWN && (parameter&255)==0x11) {
        u310_exit();
        return 1;
    }
#endif
    app_event(event,parameter);
    if (!exit_requested && event != U310_UI_DESTROY) app_draw();
    return 1;
}
int u310_audio_play_file(const uint16_t *path,unsigned volume) {
#ifdef U310_TARGET_U880
    /* SNDAPI_Play_Audio, U880 export group 0x15c +0x18.
     * Non-null options: three bytes read by LGOEM_Play_Cmx2. The firmware
     * copies the path into its CMX source; no PXO buffer survives this call. */
    static const uint8_t options[4]={0,0,0,0};
    if (!path || volume>7) return -1;
    return (int)((call4)method(0x154,0x18))((word)path,1,volume,(word)options);
#else
    (void)path; (void)volume; return -1;
#endif
}
void u310_audio_stop(void) {
#ifdef U310_TARGET_U880
    ((call1)method(0x154,0x20))(0);
#endif
}
__attribute__((used)) word pxo_entry(word message, word parameter) {
    if (message == 1) {
        exit_requested=0;
        shutdown_called=0;
        redraw_pending=0;
        ((call2)method(0x48,0x18))(1,(word)ui_event);
        ((call1)method(0x48,0x1c))(1);
        ((call0)method(0x48,0x10))();
    } else if (message == 2) {
        if (!shutdown_called) {
            shutdown_called=1;
            app_shutdown();
            ((call0)method(0x48,0x14))();
        }
    } else if (message == 3 || (message == 0x65 && (parameter & 255)==0x11)) {
        u310_exit();
    } else if (!exit_requested) {
        if (message==0x6b) redraw_pending=0;
        ((call2)method(0x48,0x0c))(message,parameter);
    }
    return 1;
}
void *memcpy(void *dst,const void *src,size_t n) {
    unsigned char *d=dst; const unsigned char *s=src;
    for(size_t i=0;i<n;i++) d[i]=s[i];
    return dst;
}
void *memset(void *dst,int c,size_t n) {
    unsigned char *d=dst;
    for(size_t i=0;i<n;i++) d[i]=(unsigned char)c;
    return dst;
}
void __aeabi_memcpy(void *d,const void *s,size_t n) {memcpy(d,s,n);}
void __aeabi_memcpy4(void *d,const void *s,size_t n) {memcpy(d,s,n);}
void __aeabi_memclr(void *d,size_t n) {memset(d,0,n);}
void __aeabi_memclr4(void *d,size_t n) {memset(d,0,n);}
