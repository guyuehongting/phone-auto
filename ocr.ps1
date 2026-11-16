param(
    [Parameter(Mandatory=$true)][string]$Path,
    [string]$Lang = "zh-Hans-CN",
    [string]$Out = ""
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime

[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$full = (Resolve-Path $Path).Path
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($full)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$language = New-Object Windows.Globalization.Language($Lang)
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if (-not $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
if (-not $engine) { Write-Error "无法创建 OCR 引擎"; exit 1 }

$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

$lines = @()
foreach ($line in $result.Lines) {
    $minX = [double]::MaxValue; $minY = [double]::MaxValue
    $maxX = 0; $maxY = 0
    foreach ($w in $line.Words) {
        $r = $w.BoundingRect
        if ($r.X -lt $minX) { $minX = $r.X }
        if ($r.Y -lt $minY) { $minY = $r.Y }
        if (($r.X + $r.Width) -gt $maxX) { $maxX = $r.X + $r.Width }
        if (($r.Y + $r.Height) -gt $maxY) { $maxY = $r.Y + $r.Height }
    }
    $lines += [pscustomobject]@{
        text = $line.Text
        x    = [int]$minX
        y    = [int]$minY
        w    = [int]($maxX - $minX)
        h    = [int]($maxY - $minY)
    }
}

$json = [pscustomobject]@{
    image  = $full
    width  = $decoder.PixelWidth
    height = $decoder.PixelHeight
    count  = $lines.Count
    lines  = $lines
} | ConvertTo-Json -Depth 4

# 直接写 UTF-8 文件，避免控制台管道把中文转成 GBK 乱码
if ([string]::IsNullOrWhiteSpace($Out)) {
    $Out = [System.IO.Path]::ChangeExtension($full, ".ocr.json")
}
[System.IO.File]::WriteAllText($Out, $json, [System.Text.UTF8Encoding]::new($false))
Write-Output $Out
