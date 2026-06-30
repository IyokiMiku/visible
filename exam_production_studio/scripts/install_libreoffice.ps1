# 安装 LibreOffice（供试卷模板 PDF 预览），显示真实下载进度条 + 速度。
# 由 start.bat 在检测不到 soffice 且 winget 可用时调用。
# 策略：用 winget 解析官方安装包 URL → 自行流式下载（带进度/速度）→ 静默安装；
#       任一步失败则回退到 winget install（显示 winget 自带进度）。
$ErrorActionPreference = 'Continue'

Write-Host ''
Write-Host '============================================================'
Write-Host '  正在安装 LibreOffice（用于试卷模板 PDF 预览）'
Write-Host '  请勿关闭此窗口；安装阶段可能弹出 UAC 授权，请点“是”。'
Write-Host '============================================================'

function Format-Size([double]$bytes) {
  if ($bytes -ge 1GB) { return ('{0:N2} GB' -f ($bytes / 1GB)) }
  if ($bytes -ge 1MB) { return ('{0:N1} MB' -f ($bytes / 1MB)) }
  if ($bytes -ge 1KB) { return ('{0:N0} KB' -f ($bytes / 1KB)) }
  return ('{0:N0} B' -f $bytes)
}

function Get-InstallerUrl {
  try {
    $out = winget show --id TheDocumentFoundation.LibreOffice -e --accept-source-agreements 2>$null
    $m = $out | Select-String -Pattern 'https?://\S+?\.(?:msi|exe)' -AllMatches | Select-Object -First 1
    if ($m) { return $m.Matches[0].Value.Trim() }
  } catch {}
  return $null
}

function Invoke-Download($url, $dest) {
  $req = [System.Net.HttpWebRequest]::Create($url)
  $req.UserAgent = 'eps-installer'
  $req.AllowAutoRedirect = $true
  $resp = $req.GetResponse()
  $total = [double]$resp.ContentLength
  $in = $resp.GetResponseStream()
  $fs = [System.IO.File]::Create($dest)
  try {
    $buf = New-Object byte[] 262144
    [double]$read = 0
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    [double]$lastMs = 0
    [double]$lastBytes = 0
    while (($n = $in.Read($buf, 0, $buf.Length)) -gt 0) {
      $fs.Write($buf, 0, $n)
      $read += $n
      $ms = $sw.Elapsed.TotalMilliseconds
      if (($ms - $lastMs) -ge 300) {
        $speed = ($read - $lastBytes) / (($ms - $lastMs) / 1000)
        $lastMs = $ms
        $lastBytes = $read
        if ($total -gt 0) {
          $pct = [int](($read / $total) * 100)
          $fill = [int](30 * $read / $total)
          $bar = ('#' * $fill) + ('-' * (30 - $fill))
          Write-Host -NoNewline ("`r  [{0}] {1,3}%  {2}/{3}  {4}/s   " -f $bar, $pct, (Format-Size $read), (Format-Size $total), (Format-Size $speed))
        } else {
          Write-Host -NoNewline ("`r  已下载 {0}  {1}/s   " -f (Format-Size $read), (Format-Size $speed))
        }
      }
    }
    if ($total -gt 0) {
      Write-Host ("`r  [{0}] 100%  {1} 下载完成{2}" -f ('#' * 30), (Format-Size $read), (' ' * 20))
    } else {
      Write-Host ("`r  已下载 {0} 下载完成{1}" -f (Format-Size $read), (' ' * 20))
    }
  } finally {
    $fs.Close(); $in.Close(); $resp.Close()
  }
}

function Install-ViaWinget {
  Write-Host '  使用 winget 安装（显示其自带进度）...'
  winget install -e --id TheDocumentFoundation.LibreOffice --accept-source-agreements --accept-package-agreements
  return $LASTEXITCODE
}

$code = 1
$url = Get-InstallerUrl
if ($url) {
  $ext = if ($url -match '\.msi(\?|$)') { 'msi' } else { 'exe' }
  $dest = Join-Path $env:TEMP ("LibreOffice_setup." + $ext)
  try {
    Write-Host ("  安装包：{0}" -f $url)
    Invoke-Download $url $dest
    Write-Host '  下载完成，开始安装（可能弹出 UAC，请点“是”）...'
    if ($ext -eq 'msi') {
      $p = Start-Process 'msiexec.exe' -ArgumentList ('/i "{0}" /qn /norestart' -f $dest) -PassThru -Verb RunAs
    } else {
      $p = Start-Process $dest -ArgumentList '/S' -PassThru -Verb RunAs
    }
    $p.WaitForExit()
    $code = $p.ExitCode
    if ($null -eq $code) { $code = 0 }
  } catch {
    Write-Host ''
    Write-Host ("  [提示] 自助下载/安装失败：{0}" -f $_.Exception.Message)
    $code = Install-ViaWinget
  }
} else {
  Write-Host '  无法解析安装包地址。'
  $code = Install-ViaWinget
}

Write-Host ("  安装结束（退出码 {0}）。" -f $code)
if ($code -ne 0) {
  Write-Host '  如反复失败，可手动安装：https://www.libreoffice.org/download/'
}
exit $code
