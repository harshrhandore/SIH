param([ValidateSet('init-env','show-demo-password')][string]$Command = 'init-env', [switch]$Native)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $taskRoot '.env'
if ($Command -eq 'show-demo-password') {
    $passwordLine = [IO.File]::ReadAllLines($envPath) | Where-Object { $_.StartsWith('DEMO_PASSWORD=') }
    if (!$passwordLine) { throw 'Run init-env first.' }
    Write-Output $passwordLine.Substring(14)
    exit 0
}
if (Test-Path -LiteralPath $envPath) { Write-Output 'Environment already exists; left unchanged.'; exit 0 }
$values = [ordered]@{}
foreach ($line in [IO.File]::ReadAllLines((Join-Path $taskRoot '.env.example'))) {
    if ($line -and !$line.StartsWith('#') -and $line.Contains('=')) {
        $parts = $line.Split(@('='),2,[StringSplitOptions]::None)
        $values[$parts[0]] = $parts[1]
    }
}
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    foreach ($key in @('POSTGRES_PASSWORD','RUNTIME_DB_PASSWORD','JWT_SECRET','MASK_SECRET','GRANT_SECRET','DEMO_PASSWORD')) {
        $buffer = New-Object byte[] 36
        $rng.GetBytes($buffer)
        $values[$key] = [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+','-').Replace('/','_')
    }
} finally { $rng.Dispose() }
$databaseHost = if ($Native) { '127.0.0.1:55432' } else { 'db:5432' }
$values['DATABASE_OWNER_URL'] = 'postgresql://shiksham_owner:' + [Uri]::EscapeDataString($values['POSTGRES_PASSWORD']) + '@' + $databaseHost + '/shiksham'
$values['DATABASE_URL'] = 'postgresql://shiksham_runtime:' + [Uri]::EscapeDataString($values['RUNTIME_DB_PASSWORD']) + '@' + $databaseHost + '/shiksham'
$lines = foreach ($key in $values.Keys) { $key + '=' + $values[$key] }
[IO.File]::WriteAllLines($envPath,$lines,(New-Object Text.UTF8Encoding($false)))
Write-Output 'Created .env with generated secrets. Use show-demo-password locally to view the demo password.'
