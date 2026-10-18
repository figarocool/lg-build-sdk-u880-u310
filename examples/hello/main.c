#include "u310.h"
#include "hello_bitmap.h"
void app_draw(void) {
    u310_clear(0);
    u310_draw_bitmap(0, 90, hello_bitmap);
    u310_present();
}
