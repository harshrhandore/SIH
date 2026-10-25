param([ValidateSet('init-env','show-demo-password')][string]$Command = 'init-env', [switch]$Native)
$taskRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonExe)) { $pythonExe = 'python' }
$taskArgs = @((Join-Path $PSScriptRoot 'demo.py'), $Command)
if ($Native) { $taskArgs += '--native' }
& $pythonExe @taskArgs
exit $LASTEXITCODE
