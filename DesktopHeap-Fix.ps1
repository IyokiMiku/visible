# ============================================================
#  DesktopHeap-Fix.ps1
#  Fixes recurring 0xc0000142 (STATUS_DLL_INIT_FAILED) caused by
#  interactive desktop heap exhaustion.
#
#  HOW TO RUN:
#    Right-click this file  ->  "Run with PowerShell"
#    (It will auto-request Administrator rights via a UAC prompt.)
#
#  WHAT IT DOES:
#    Raises the 2nd value of SharedSection (interactive desktop heap)
#    from 20480 KB to 40960 KB. A REBOOT is required to take effect.
#
#  TO REVERT:
#    Run with -Revert  (sets it back to 20480), then reboot.
# ============================================================

param(
    [switch]$Revert
)

# ---- self-elevate to Administrator ----
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($Revert) { $argList += " -Revert" }
    Start-Process powershell.exe -ArgumentList $argList -Verb RunAs
    exit
}

$key = 'HKLM:\System\CurrentControlSet\Control\Session Manager\SubSystems'
$target = if ($Revert) { '20480' } else { '40960' }

$current = (Get-ItemProperty -Path $key -Name Windows).Windows
Write-Host ""
Write-Host "Current value:" -ForegroundColor Cyan
Write-Host "  $current"

if ($current -notmatch 'SharedSection=\d+,\d+,\d+') {
    Write-Host "ERROR: could not find SharedSection in the registry value. Aborting." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$new = $current -replace 'SharedSection=(\d+),(\d+),(\d+)', ('SharedSection=$1,' + $target + ',$3')
Set-ItemProperty -Path $key -Name Windows -Value $new

$check = (Get-ItemProperty -Path $key -Name Windows).Windows
Write-Host ""
Write-Host "New value:" -ForegroundColor Green
Write-Host "  $check"
Write-Host ""
Write-Host ("Interactive desktop heap set to {0} KB." -f $target) -ForegroundColor Green
Write-Host "A REBOOT is required for this to take effect." -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to close"
