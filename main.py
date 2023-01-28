import asyncio
import evdev


async def print_events(device):
    async for event in device.async_read_loop():
        print(f'{device.path}: code: {event.code}, type: {event.type}, value: {event.value}')


def main():
    raw_devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for raw_device in raw_devices:
        print(raw_device.path, raw_device.name, raw_device.phys)

    dev_nums = input().strip().split()
    dev_nums = [int(dev_num) for dev_num in dev_nums]

    devices = [evdev.InputDevice(f'/dev/input/event{dev_num}') for dev_num in dev_nums]

    loop = asyncio.get_event_loop()

    for device in devices:
        asyncio.ensure_future(print_events(device), loop=loop)

    loop.run_forever()


if __name__ == '__main__':
    main()
