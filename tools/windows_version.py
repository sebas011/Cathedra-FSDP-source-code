import argparse
from pathlib import Path


def version_resource(version: str) -> str:
    numbers = tuple(int(part) for part in version.split('.'))
    if len(numbers) != 3 or any(number < 0 or number > 65535 for number in numbers):
        raise ValueError('Use a three-part Windows-compatible version.')
    windows_version = (*numbers, 0)
    values = {'FileDescription': 'Cathedra FSDP', 'FileVersion': version,
              'InternalName': 'Cathedra FSDP', 'OriginalFilename': 'Cathedra FSDP.exe',
              'ProductName': 'Cathedra FSDP', 'ProductVersion': version}
    strings = ','.join(f'StringStruct({key!r}, {value!r})' for key, value in values.items())
    return (f'VSVersionInfo(ffi=FixedFileInfo(filevers={windows_version!r}, prodvers={windows_version!r}, '
            'mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), '
            f"kids=[StringFileInfo([StringTable('040904B0', [{strings}])]), "
            "VarFileInfo([VarStruct('Translation', [1033, 1200])])])")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('version')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(version_resource(args.version), encoding='utf-8')
