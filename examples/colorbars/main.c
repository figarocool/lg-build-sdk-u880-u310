#include "u310.h"
static const uint32_t colors[] = {0xff0000,0x00ff00,0x0000ff,0xffffff};
void app_draw(void) {
    u310_clear(0);
    for (unsigned i=0; i<4; i++)
        u310_fill_rect(i*44, 0, i*44+43, 219, colors[i]);
    u310_present();
}
