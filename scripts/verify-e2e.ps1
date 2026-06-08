# End-to-end smoke test (run while kubectl port-forward svc/gateway 8080:8080 is active).
param(
    [string]$Base = "http://127.0.0.1:8080",
    [string]$Email = "v@email.com",
    [string]$Password = "Admin123",
    [string]$VideoPath = "$PSScriptRoot\..\convertor\videofile.mp4"
)

$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host "FAIL: $msg" -ForegroundColor Red; exit 1 }

Write-Host "=== Cluster pods ===" -ForegroundColor Cyan
kubectl get pods -l 'app in (gateway,auth,convertor,mongo)' 2>$null
if ($LASTEXITCODE -ne 0) { Fail "kubectl not connected. Start Docker Desktop, then: minikube start" }

Write-Host "`n=== 1. Login (JWT) ===" -ForegroundColor Cyan
try {
    $login = Invoke-RestMethod -Uri "$Base/login" -Method Post -ContentType "application/json" -Body (@{ email = $Email; password = $Password } | ConvertTo-Json)
} catch {
    Fail "Login failed ($($_.Exception.Message)). Is port-forward running? Is MySQL up for auth?"
}
$token = $login.token
if (-not $token -or $token.Length -lt 20) { Fail "Login returned unexpected body" }
Write-Host "OK - JWT received ($($token.Length) chars)"

Write-Host "`n=== 2. Upload video ===" -ForegroundColor Cyan
if (-not (Test-Path $VideoPath)) { Fail "Video not found: $VideoPath" }
$upRaw = curl.exe -s -w "`nHTTP_CODE:%{http_code}" -X POST "$Base/upload" -H "Authorization: Bearer $token" -F "file=@$VideoPath"
$upLines = $upRaw -split "`n"
$httpCode = ($upLines[-1] -replace "HTTP_CODE:", "").Trim()
$upBody = ($upLines[0..($upLines.Length - 2)] -join "`n").Trim()
if ($httpCode -ne "200") { Fail "Upload failed ($httpCode): $upBody. Check gateway logs (Mongo/RabbitMQ)." }
$upJson = $upBody | ConvertFrom-Json
if (-not $upJson.video_fid) { Fail "Upload response missing video_fid: $($up.Content)" }
$videoFid = $upJson.video_fid
Write-Host "OK - video_fid=$videoFid"

Write-Host "`n=== 3. Poll conversion status ===" -ForegroundColor Cyan
$mp3Fid = $null
for ($i = 1; $i -le 90; $i++) {
    Start-Sleep -Seconds 2
    try {
        $st = Invoke-WebRequest -Uri "$Base/status?video_fid=$videoFid" -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing
        $stJ = $st.Content | ConvertFrom-Json
    } catch {
        Fail "Status check failed. Rebuild gateway if /status returns 404."
    }
    if ($stJ.ready) { $mp3Fid = $stJ.mp3_fid; break }
    Write-Host "  waiting... ($i)"
}
if (-not $mp3Fid) {
    Fail "MP3 not ready after 3 min. Check: kubectl logs deployment/convertor"
}

Write-Host "OK - mp3_fid=$mp3Fid"

Write-Host "`n=== 4. Download MP3 ===" -ForegroundColor Cyan
$outFile = Join-Path $env:TEMP "verify-output.mp3"
Invoke-WebRequest -Uri "$Base/download?mp3_fid=$mp3Fid" -Headers @{ Authorization = "Bearer $token" } -OutFile $outFile -UseBasicParsing
$size = (Get-Item $outFile).Length
if ($size -lt 1000) { Fail "Downloaded file too small ($size bytes)" }
Write-Host "OK - saved $outFile ($size bytes)"

Write-Host "`n=== 5. List user files ===" -ForegroundColor Cyan
$filesRes = Invoke-RestMethod -Uri "$Base/files" -Headers @{ Authorization = "Bearer $token" }
if ($filesRes.files.Count -lt 1) { Fail "No files returned from /files" }
Write-Host "OK - $($filesRes.files.Count) file(s) in library"

Write-Host "`nAll checks passed." -ForegroundColor Green
