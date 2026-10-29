import ctypes
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import parser, prepare, write_json
from salt import get_student_params


def windows_topology():
    # SYSTEM_LOGICAL_PROCESSOR_INFORMATION: pointer mask, enum, aligned union.
    class Entry(ctypes.Structure):
        _fields_ = [('mask', ctypes.c_size_t), ('relationship', ctypes.c_int),
                    ('payload', ctypes.c_uint64 * 2)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    size = ctypes.c_ulong()
    kernel.GetLogicalProcessorInformation(None, ctypes.byref(size))
    buffer = ctypes.create_string_buffer(size.value)
    if not kernel.GetLogicalProcessorInformation(buffer, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    cores, caches = [], []
    for offset in range(0, size.value, ctypes.sizeof(Entry)):
        item = Entry.from_buffer_copy(buffer, offset)
        if item.relationship == 0:
            cores.append(int(item.mask))
        elif item.relationship == 2:
            raw = bytes(item.payload)
            caches.append({'level': raw[0], 'line_bytes': int.from_bytes(raw[2:4], 'little'),
                           'size_bytes': int.from_bytes(raw[4:8], 'little'),
                           'type': {0: 'unified', 1: 'instruction', 2: 'data', 3: 'trace'}.get(int.from_bytes(raw[8:12], 'little')),
                           'logical_cpu_mask': int(item.mask)})
    import json
    command = 'Get-CimInstance Win32_Processor | Select-Object Name,MaxClockSpeed | ConvertTo-Json -Compress'
    source = 'Win32_Processor'
    try:
        cpu = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True, stderr=subprocess.PIPE))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu = {'Name': winreg.QueryValueEx(key, 'ProcessorNameString')[0], 'MaxClockSpeed': None}
        source = 'Windows hardware registry (CIM unavailable)'
    if isinstance(cpu, list):
        cpu = cpu[0]
    return {'cpu_model': cpu['Name'], 'reported_max_frequency_mhz': cpu['MaxClockSpeed'],
            'physical_cores': len(cores), 'core_masks': cores, 'caches': caches,
            'topology_source': f'GetLogicalProcessorInformation + {source} (current processor group)'}


def linux_topology():
    import json
    items = json.loads(subprocess.check_output(['lscpu', '-J'], text=True))['lscpu']
    info = {i['field'].rstrip(':'): i['data'] for i in items}
    pairs = set()
    caches = []
    seen = set()
    for cpu in Path('/sys/devices/system/cpu').glob('cpu[0-9]*'):
        pairs.add(((cpu / 'topology/physical_package_id').read_text().strip(),
                   (cpu / 'topology/core_id').read_text().strip()))
        for entry in (cpu / 'cache').glob('index*'):
            key = ((entry / 'level').read_text(), (entry / 'type').read_text(), (entry / 'shared_cpu_list').read_text())
            if key in seen:
                continue
            seen.add(key)
            size = (entry / 'size').read_text().strip()
            factor = {'K': 1024, 'M': 1024**2}.get(size[-1], 1)
            caches.append({'level': int(key[0]), 'type': key[1].strip().lower(),
                           'size_bytes': int(size[:-1] if factor != 1 else size) * factor,
                           'line_bytes': int((entry / 'coherency_line_size').read_text())})
    return {'cpu_model': info.get('Model name'), 'physical_cores': len(pairs),
            'caches': caches, 'core_masks': [], 'topology_source': 'lscpu and sysfs'}


def main():
    p = parser('Capture real host telemetry and student parameters')
    p.add_argument('--student-id', default='230103254')
    args = p.parse_args()
    out = prepare(args)
    if sys.platform == 'win32':
        profile = windows_topology()
    elif sys.platform.startswith('linux'):
        profile = linux_topology()
    else:
        raise RuntimeError('This profiler supports Windows and Linux; do not guess cache telemetry.')
    profile.update({'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'os': platform.platform(), 'kernel': platform.release(),
                    'python': sys.version, 'implementation': platform.python_implementation(),
                    'logical_threads': os.cpu_count(), 'microarchitecture': None,
                    'base_frequency_mhz': None,
                    'unknown_fields_note': 'Microarchitecture and base frequency are not inferred from marketing names.',
                    'smoke': args.smoke})
    profile['smt_detected'] = profile['logical_threads'] > profile['physical_cores']
    write_json(out / 'host_profile.json', profile)
    write_json(out / 'salted_params.json', get_student_params(args.student_id))
    print(f"Profile: {profile['cpu_model']}, {profile['physical_cores']} cores; {out}")


if __name__ == '__main__':
    main()

