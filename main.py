import asyncio
import gc
from threading import Thread
from time import time, sleep

import evdev
from evdev import UInput, ecodes as e


def get_sign(x):
    if x > 0:
        return 1
    elif x == 0:
        return 0
    else:
        return -1


class Movable:
    def __init__(self, fast, slow, func, tick) -> None:
        self.fast = fast
        self.slow = slow

        self.output_range = slow - fast
        self.slope = self.output_range / 128

        self.func = func
        self.tick = tick

        self.reset()

    def reset(self):
        self.x, self.y = 0, 0
        self.timer_x, self.timer_y = self.fast, self.fast

    def get_interval(self, x):
        return self.output_range - self.slope * abs(x)

    def move_in_interval(self, x, timer):
        timer -= self.tick
        move_by = 0

        if timer <= 0:
            if x != 0:
                move_by = get_sign(x)
                timer = self.get_interval(x)
            else:
                timer = self.fast

        return move_by, timer

    def move(self):
        move_x, self.timer_x = self.move_in_interval(self.x, self.timer_x)
        move_y, self.timer_y = self.move_in_interval(self.y, self.timer_y)

        if move_x != 0 or move_y != 0:
            # print(move_x, move_y)
            self.func(move_x, move_y)


class Mover(Thread):
    def __init__(self, mouse, scroll, tick):
        super().__init__(daemon=True)
        self.mouse = mouse
        self.scroll = scroll
        self.period = tick / 1000
        self.i = 0
        self.t0 = time()
        self.start()

    def sleep(self):
        self.i += 1
        delta = self.t0 + self.period * self.i - time()
        if delta > 0:
            sleep(delta)

    def run(self):
        while True:
            self.mouse.move()
            self.scroll.move()
            self.sleep()


class Controller:
    def __init__(self) -> None:
        mouse_fast, mouse_slow = 9, 21
        scroll_fast, scroll_slow = 40, 160
        tick = 1

        cap = {
            # It's necessary to enable any mouse button. Otherwise Relative events would not work
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL_HI_RES, e.REL_HWHEEL_HI_RES]
        }
        self.ui = UInput(cap, name='example-device', version=0x3)

        self.mouse = Movable(mouse_fast, mouse_slow, self.mouse_func, tick)
        self.scroll = Movable(scroll_fast, scroll_slow, self.scroll_func, tick)
        Mover(self.mouse, self.scroll, tick)

    def mouse_func(self, x, y):
        self.ui.write(e.EV_REL, e.REL_X, x)
        self.ui.write(e.EV_REL, e.REL_Y, -y)
        self.ui.syn()

    def scroll_func(self, x, y):
        self.ui.write(e.EV_REL, e.REL_HWHEEL_HI_RES, x)
        self.ui.write(e.EV_REL, e.REL_WHEEL_HI_RES, y)
        self.ui.syn()


async def handle_events(device, controller):
    async for event in device.async_read_loop():
        if event.code == 0 and event.type == 0 and event.value == 0:
            continue

        match event.code:
            case 0 | 2:
                value = event.value - 128
                # print(value)
                match event.code:
                    case 0:
                        controller.scroll.x = value
                    case 2:
                        controller.mouse.x = value
            case 1 | 5:
                value = 128 - event.value
                # print(value)
                match event.code:
                    case 1:
                        controller.scroll.y = value
                    case 5:
                        controller.mouse.y = value
            case _:
                print("Unsupported value")
                # print(f'{device.path}: code: {event.code}, type: {event.type}, value: {event.value}')

        # print(f'{device.path}: code: {event.code}, type: {event.type}, value: {event.value}')


def main():
    raw_devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for raw_device in raw_devices:
        print(raw_device.path, raw_device.name, raw_device.phys)

    # dev_nums = input().strip().split()
    dev_nums = [7]
    dev_nums = [int(dev_num) for dev_num in dev_nums]

    devices = [evdev.InputDevice(f'/dev/input/event{dev_num}') for dev_num in dev_nums]

    loop = asyncio.get_event_loop()
    controller = Controller()

    for device in devices:
        asyncio.ensure_future(handle_events(device, controller), loop=loop)

    gc.disable()
    gc.collect()

    loop.run_forever()


if __name__ == '__main__':
    main()
