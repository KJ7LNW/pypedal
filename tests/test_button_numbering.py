"""Test that button numbers are sequential across all devices"""
from pypedal.core.config import Config

def test_sequential_button_numbering() -> None:
    """Test that buttons are numbered sequentially across devices"""
    config = Config('example.conf')

    print('\nDevice button assignments:')
    all_buttons = []
    for i, device in enumerate(config.devices):
        buttons = sorted(set(m.button for m in device.mappings))
        all_buttons.extend(buttons)
        print(f'Device {i+1} ({device.path.split("/")[-1]}): buttons {buttons}')

    print(f'\nAll buttons: {all_buttons}')
    print(f'Expected: {list(range(1, len(all_buttons) + 1))}')

    assert all_buttons == list(range(1, len(all_buttons) + 1)), \
        f"Buttons not sequential: {all_buttons}"

if __name__ == '__main__':
    test_sequential_button_numbering()
