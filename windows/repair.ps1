#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Install', 'Restore', 'Status')][string]$Action = 'Status',
    [string]$AdbPath,
    [string]$Serial,
    [switch]$NonInteractive
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$script:AdbExe = $null
$script:SelectedSerial = $null
$script:UseSu = $false
$script:LogPath = $null

function Quote-NativeArgument([string]$Value) {
    # Windows CRT quoting; works with ProcessStartInfo on Windows PowerShell 5.1.
    $result = New-Object System.Text.StringBuilder
    [void]$result.Append([char]34)
    $slashes = 0
    foreach ($character in $Value.ToCharArray()) {
        if ($character -eq [char]92) { $slashes++; continue }
        if ($character -eq [char]34) {
            [void]$result.Append([char]92, (2 * $slashes + 1))
        } else {
            [void]$result.Append([char]92, $slashes)
        }
        [void]$result.Append($character)
        $slashes = 0
    }
    [void]$result.Append([char]92, (2 * $slashes))
    [void]$result.Append([char]34)
    return $result.ToString()
}

function Write-Log([string]$Message) {
    if ($script:LogPath) { Add-Content -LiteralPath $script:LogPath -Value $Message -Encoding UTF8 }
}

function Invoke-Adb {
    param([string[]]$Arguments, [int]$TimeoutSeconds = 30, [switch]$AllowFailure)
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $script:AdbExe
    $info.Arguments = (($Arguments | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $info.StandardErrorEncoding = New-Object System.Text.UTF8Encoding($false)
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    Write-Log ('ADB ' + ($Arguments -join ' '))
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            throw 'ADB 操作超时。安装或恢复可能已生效，请先运行“检查状态”，再决定后续操作。'
        }
        $text = ($stdout.Result + $stderr.Result).Trim()
        $result = [pscustomobject]@{ ExitCode = $process.ExitCode; Text = $text }
        Write-Log $text
        if ($result.ExitCode -ne 0 -and -not $AllowFailure) {
            throw ('ADB 操作失败（退出码 ' + $result.ExitCode + '）：' + $text)
        }
        return $result
    } finally { $process.Dispose() }
}

function Find-Adb {
    if ($AdbPath) {
        if (-not (Test-Path -LiteralPath $AdbPath -PathType Leaf)) { throw '指定的 ADB 文件不存在。' }
        return (Resolve-Path -LiteralPath $AdbPath).Path
    }
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    $candidates.Add((Join-Path $PSScriptRoot 'adb\adb.exe'))
    $command = Get-Command adb.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates.Add($command.Source) }
    foreach ($base in @([Environment]::GetEnvironmentVariable('ProgramFiles'), [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'))) {
        if ($base) {
            foreach ($relative in @('Netease\MuMuPlayer-12.0', 'MuMuPlayer-12.0', 'MuMuPlayer12')) {
                foreach ($file in @('shell\adb.exe', 'adb.exe', 'nx_main\adb.exe')) {
                    $candidates.Add((Join-Path (Join-Path $base $relative) $file))
                }
            }
        }
    }
    foreach ($key in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
        foreach ($entry in @(Get-ItemProperty $key -ErrorAction SilentlyContinue)) {
            if ($entry.PSObject.Properties['DisplayName'] -and $entry.DisplayName -match 'MuMu' -and $entry.PSObject.Properties['InstallLocation'] -and $entry.InstallLocation) {
                foreach ($file in @('shell\adb.exe', 'adb.exe', 'nx_main\adb.exe')) {
                    $candidates.Add((Join-Path $entry.InstallLocation $file))
                }
            }
        }
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    if ($NonInteractive) { throw '未找到 ADB，请通过 -AdbPath 指定 MuMu 的 adb.exe。' }
    $manual = (Read-Host '未找到 ADB，请粘贴 MuMu 的 adb.exe 完整路径').Trim().Trim('"')
    if (-not (Test-Path -LiteralPath $manual -PathType Leaf)) { throw 'ADB 路径无效，请重新运行并选择实际的 adb.exe。' }
    return (Resolve-Path -LiteralPath $manual).Path
}

function Get-Devices {
    $result = Invoke-Adb -Arguments @('devices', '-l')
    foreach ($line in ($result.Text -split '\r?\n')) {
        if ($line -match '^(\S+)\s+(device|offline|unauthorized)\b(.*)$') {
            [pscustomobject]@{ Serial = $matches[1]; State = $matches[2]; Details = $matches[3].Trim() }
        }
    }
}

function Select-Device {
    $devices = @(Get-Devices)
    if ($Serial -and $Serial -notmatch '^[a-zA-Z0-9_.:\[\]-]+$') { throw '设备标识包含不支持的字符。' }
    if ($Serial -and -not @($devices | Where-Object { $_.Serial -eq $Serial -and $_.State -eq 'device' }).Count) {
        if ($Serial -match '^[a-zA-Z0-9_.-]+:[0-9]{1,5}$') {
            [void](Invoke-Adb -Arguments @('connect', $Serial))
            $devices = @(Get-Devices)
        }
    }
    $ready = @($devices | Where-Object { $_.State -eq 'device' })
    if ($Serial) {
        if (-not @($ready | Where-Object { $_.Serial -eq $Serial }).Count) { throw '指定实例不可用，请检查模拟器的 ADB 开关及授权。' }
        return $Serial
    }
    if ($ready.Count -eq 0) {
        if ($NonInteractive) { throw '没有在线设备，请先连接模拟器的 ADB 地址。' }
        Write-Host ($devices | Format-Table -AutoSize | Out-String)
        $address = Read-Host '输入模拟器 ADB 地址（例如 127.0.0.1:16384；按实际实例端口填写）'
        if ($address -notmatch '^[a-zA-Z0-9_.-]+:[0-9]{1,5}$') { throw 'ADB 地址格式无效，请填写主机名或 IP 加端口。' }
        [void](Invoke-Adb -Arguments @('connect', $address))
        $ready = @(Get-Devices | Where-Object { $_.State -eq 'device' })
    }
    if ($ready.Count -eq 0) { throw '连接后仍没有在线实例，请检查端口或授权。' }
    if ($ready.Count -eq 1) { return $ready[0].Serial }
    if ($NonInteractive) { throw '发现多个设备，请使用 -Serial 明确选择一个实例。' }
    for ($i = 0; $i -lt $ready.Count; $i++) { Write-Host ('[' + ($i + 1) + '] ' + $ready[$i].Serial + ' ' + $ready[$i].Details) }
    $choice = Read-Host '选择要操作的实例编号'
    $index = 0
    if (-not [int]::TryParse($choice, [ref]$index) -or $index -lt 1 -or $index -gt $ready.Count) { throw '实例编号无效，已停止。' }
    return $ready[$index - 1].Serial
}

function Invoke-Root([string]$Command, [int]$TimeoutSeconds = 30, [switch]$AllowFailure) {
    if ($Command.Contains("'")) { throw '内部命令包含不支持的引号。' }
    if ($script:UseSu) { $Command = "su -c '" + $Command + "'" }
    return Invoke-Adb -Arguments @('-s', $script:SelectedSerial, 'shell', $Command) -TimeoutSeconds $TimeoutSeconds -AllowFailure:$AllowFailure
}

function Main {
    $logDir = Join-Path $PSScriptRoot 'logs'
    [void][IO.Directory]::CreateDirectory($logDir)
    $script:LogPath = Join-Path $logDir ((Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + $Action + '.log')
    $script:AdbExe = Find-Adb
    $script:SelectedSerial = Select-Device
    Write-Host ('实例：' + $script:SelectedSerial)
    $identity = Invoke-Adb -Arguments @('-s', $script:SelectedSerial, 'shell', 'id')
    if ($identity.Text -notmatch 'uid=0\(') {
        $identity = Invoke-Adb -Arguments @('-s', $script:SelectedSerial, 'shell', 'su -c id') -AllowFailure
        if ($identity.ExitCode -ne 0 -or $identity.Text -notmatch 'uid=0\(') { throw '未获得 Root，请在模拟器中授权 shell 的 Root 请求后重试。' }
        $script:UseSu = $true
    }
    $abi = (Invoke-Root 'getprop ro.product.cpu.abi').Text
    $sdk = (Invoke-Root 'getprop ro.build.version.sdk').Text
    Write-Host ('系统：SDK ' + $sdk + ' / ' + $abi)
    if ($Action -eq 'Status') {
        foreach ($command in @('settings get secure default_input_method', 'settings get secure enabled_input_methods', '/data/adb/ksud module list', 'cat /data/adb/modules/mumu_ime_allow_com_ac/last-run.log', 'cat /data/adb/modules_update/mumu_ime_allow_com_ac/last-run.log')) {
            Write-Host ('> ' + $command)
            Write-Host (Invoke-Root $command -AllowFailure).Text
        }
        Write-Host '状态检查完成；未向设备上传文件，也未安装或切换输入法。'
        return
    }
    $metadataPath = Join-Path $PSScriptRoot 'package.json'
    if (-not (Test-Path -LiteralPath $metadataPath)) { throw '缺少完整工具包，请解压共享 ZIP 后运行，不要直接运行源码目录。' }
    $metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Action -eq 'Install') {
        if ($abi -ne 'x86_64' -or $sdk -ne '35') { throw '目前仅支持 x86_64 / Android 15（SDK 35），已停止安装。' }
        $framework = (Invoke-Root 'sha256sum /system/framework/framework.jar').Text.Split(' ')[0]
        if ($framework -ne $metadata.framework_sha256) { throw '系统框架指纹不匹配，已停止安装。请使用对应版本的修复包。' }
        $module = Join-Path $PSScriptRoot 'module.zip'
        if (-not (Test-Path -LiteralPath $module) -or (Get-FileHash -LiteralPath $module -Algorithm SHA256).Hash.ToLowerInvariant() -ne $metadata.module_sha256) { throw '模块 ZIP 缺失或校验不匹配，请重新获取完整工具包。' }
        Write-Host (Invoke-Root '/data/adb/ksud --version').Text
    }
    $helper = Join-Path $PSScriptRoot 'device.sh'
    if ((Get-FileHash -LiteralPath $helper -Algorithm SHA256).Hash.ToLowerInvariant() -ne $metadata.device_sha256) { throw '设备脚本校验不匹配，请重新获取完整工具包。' }
    [void](Invoke-Adb -Arguments @('-s', $script:SelectedSerial, 'shell', 'mkdir -p /data/local/tmp/mumu-ime-share'))
    [void](Invoke-Adb -Arguments @('-s', $script:SelectedSerial, 'push', $helper, '/data/local/tmp/mumu-ime-share/device.sh'))
    if ($Action -eq 'Install') { [void](Invoke-Adb -Arguments @('-s', $script:SelectedSerial, 'push', $module, '/data/local/tmp/mumu-ime-share/module.zip') -TimeoutSeconds 120) }
    $result = Invoke-Root ('sh /data/local/tmp/mumu-ime-share/device.sh ' + $Action.ToLowerInvariant()) -TimeoutSeconds 180
    Write-Host $result.Text
    $marker = if ($Action -eq 'Install') { 'MUMU_SHARE_INSTALLED' } else { 'MUMU_SHARE_RESTORED' }
    if ($result.Text -notmatch ('(?m)^' + $marker + '\r?$')) { throw '设备没有返回完成标记，请运行状态检查并保留日志。' }
    if ($Action -eq 'Install') { Write-Host '安装并应用成功。工具不会自动重启；方便时请手动重启验证开机修复。' }
    else { Write-Host '已恢复本设备原来的配置，并停用开机修复模块。' }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Main; Write-Host ('日志：' + $script:LogPath); exit 0 }
    catch { Write-Host ('操作未完成：' + $_.Exception.Message); if ($script:LogPath) { Write-Log $_.Exception.Message; Write-Host ('日志：' + $script:LogPath) }; Write-Host '请保留日志并检查状态；不要在原因不明时反复安装。'; exit 1 }
}
