import subprocess

commands = [
    (
        "$arrays = @(Get-CimInstance Win32_PhysicalMemoryArray); "
        "if ($arrays) { "
        "  $max = 0; "
        "  foreach ($array in $arrays) { "
        "    if ($array.PSObject.Properties.Name -contains 'MaxCapacityEx' -and $array.MaxCapacityEx) { "
        "      $max += [int64]$array.MaxCapacityEx * 1KB; "
        "    } elseif ($array.MaxCapacity) { "
        "      $max += ([int64]$array.MaxCapacity * 1KB); "
        "    } "
        "  } "
        "  if ($max -gt 0) { Write-Output ([math]::Round($max / 1GB, 2)) } "
        "}"
    )
]
for cmd in commands:
    res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    print("OUT:", res.stdout.strip())
    print("ERR:", res.stderr.strip())
