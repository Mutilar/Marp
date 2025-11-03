param(
    [string]$InputPath = (Join-Path $PSScriptRoot "..\readme.md"),
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\assets\diagrams\high-level-wiring.png"),
    [int]$DiagramIndex = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Throw-IfMissingCommand {
    param([string]$CommandName)
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Required command '$CommandName' was not found. Install Node.js from https://nodejs.org/ to gain access to npx."
    }
}

if (-not (Test-Path -Path $InputPath)) {
    throw "Could not locate input markdown file at '$InputPath'."
}

$readmeContent = Get-Content -Path $InputPath -Raw
$regex = [regex]'```mermaid\s+([\s\S]*?)```'
$matches = $regex.Matches($readmeContent)

if ($matches.Count -eq 0) {
    throw "No mermaid code block was found in '$InputPath'."
}

if ($DiagramIndex -lt 0 -or $DiagramIndex -ge $matches.Count) {
    throw "DiagramIndex $DiagramIndex is out of range. Found $($matches.Count) mermaid block(s)."
}

$diagramSource = $matches[$DiagramIndex].Groups[1].Value.Trim()

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "marp-mermaid"
$tempFile = Join-Path $tempRoot "diagram.mmd"

if (-not (Test-Path -Path $tempRoot)) {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
}

$diagramSource | Set-Content -Path $tempFile -Encoding utf8

$fullOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $fullOutputPath

if (-not (Test-Path -Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

Throw-IfMissingCommand -CommandName "npx"

$arguments = @("--yes", "@mermaid-js/mermaid-cli", "-i", $tempFile, "-o", $fullOutputPath)

& npx @arguments

if ($LASTEXITCODE -ne 0) {
    throw "Mermaid CLI exited with code $LASTEXITCODE."
}

Write-Host "Rendered diagram saved to $fullOutputPath"
