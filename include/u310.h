#ifndef U310_H
#define U310_H
#include <stdint.h>
#include <stddef.h>
#define U310_SCREEN_WIDTH 176
#define U310_SCREEN_HEIGHT 220
/* Raw firmware UI events: only create/destroy are named so far. */
#define U310_UI_CREATE 0u
#define U310_UI_DESTROY 1u
#define U310_UI_KEY_DOWN 5u
#define U310_UI_KEY_UP 6u
#define U310_UI_REDRAW 10u
/* Queue another UI turn; repeated requests before delivery are coalesced.
 * Unpaced: applications must not assume this is a 60 Hz timer. */
void u310_request_redraw(void);
/* Drawing colors are 0x00RRGGBB; bitmap pixels use RGB565. */
void u310_clear(uint32_t color);
void u310_fill_rect(int left, int top, int right, int bottom, uint32_t color);
void u310_draw_bitmap(int x, int y, const void *native_bitmap);
void u310_present(void);
/* Firmware application heap. Allocation may fail; caller must free it. */
void *u310_alloc(size_t size);
void u310_free(void *pointer);
/* Current native graphics surface; buffer belongs to the firmware. */
typedef struct {
    uint32_t id, width, height, bits_per_pixel;
    void *buffer;
} u310_surface;
int u310_get_surface(u310_surface *surface);
/* Read-only files: UTF-16LE zero-terminated paths, mode 1 as used by PXO loader. */
typedef uintptr_t u310_file;
u310_file u310_file_create(const uint16_t *path);
int32_t u310_file_write(u310_file file,const void *buffer,uint32_t size);
u310_file u310_file_open_read(const uint16_t *path);
int32_t u310_file_read(u310_file file, void *buffer, uint32_t size);
void u310_file_close(u310_file file);
size_t u310_utf16_length(const uint16_t *text);
/* Native clock low word. Unit/calibration still being verified. */
uint32_t u310_clock_raw(void);
/* Queue a normal process exit; returns before destruction is completed.
 * Call from app/UI callbacks. BACK also requests this exit by default. */
void u310_exit(void);
/* U880 V10b native audio. UTF-16 path, single playback, volume 0..7.
 * Returns firmware status (0 accepted), -1 on invalid input/unsupported target.
 * Call stop before leaving an application that started audio. */
int u310_audio_play_file(const uint16_t *path,unsigned volume);
void u310_audio_stop(void);
/* Optional: release application-owned files/buffers before UI teardown. */
void app_shutdown(void);
/* Optional: defer BACK while firmware still owns an asynchronous request.
 * Return zero to defer; call u310_exit() once the request has completed. */
int app_can_exit(void);
/* Define these in an application. No main(), OS or libc is required. */
void app_draw(void);
void app_event(uint32_t event, uint32_t parameter);
#endif
