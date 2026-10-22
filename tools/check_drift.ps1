# check_drift.ps1 -- verify that the generated dictionaries are byte-for-byte the ones cpp-pinyin
# is consuming. ASCII only on purpose: Windows PowerShell 5.1 reads .ps1 without a BOM as ANSI.
#
# Which dialects and tables get compared is DERIVED from the two trees (see "what is compared" below),
# not listed in this file -- same derivation as tools/compare_dict_dirs.py.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\check_drift.ps1 -CppPinyinRoot D:\projects\cpp-pinyin
#   # or set it once in the environment and omit the parameter:
#   #   CPP_PINYIN_ROOT=<cpp-pinyin repo root>   CPP_PINYIN_DICT overrides the dict dir itself
#
# Options:
#   -Python <exe>        interpreter to use (default: python)
#   -SkipGenerate        compare only, do not regenerate (uses the existing out\dict)
#   -WriteReport <path>  also write a Markdown drift report

param(
    [string]$CppPinyinRoot = "",
    [string]$Python = "python",
    [switch]$SkipGenerate,
    [string]$WriteReport = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $repo "out\dict"
# 2026-10: cpp-pinyin moved its dictionary directory from res/dict to data/dialects.
# This file stays ASCII-only on purpose (see the header): PowerShell 5.1 reads a .ps1
# without a BOM as ANSI, so a non-ASCII comment here would be shown as garbage.
if (-not $CppPinyinRoot) { $CppPinyinRoot = $env:CPP_PINYIN_ROOT }
if (-not $CppPinyinRoot) {
    # 2026-10-16: a hardcoded default silently named a layout this machine does not have, so a run
    # without -CppPinyinRoot compared the wrong tree (or failed somewhere else with a confusing message).
    # Keep the old value as a last resort, but fail loudly when it is not there.
    $fallback = "C:\projects\cpp-pinyin"
    if (Test-Path $fallback) {
        $CppPinyinRoot = $fallback
    } else {
        throw "check_drift: no cpp-pinyin root given, and the default ($fallback) does not exist. Pass -CppPinyinRoot <path> or set the CPP_PINYIN_ROOT environment variable."
    }
}
# CPP_PINYIN_DICT names the dictionary directory itself -- the same override run_versions.py honours.
$repoDict = if ($env:CPP_PINYIN_DICT) { $env:CPP_PINYIN_DICT } else { Join-Path $CppPinyinRoot "data\dialects" }

Write-Host "makedict repo : $repo"
Write-Host "output        : $outDir"
Write-Host "cpp-pinyin    : $repoDict"
Write-Host ""

if (-not (Test-Path $repoDict)) {
    Write-Host "ERROR: cpp-pinyin dict dir not found: $repoDict"
    Write-Host "       Pass -CppPinyinRoot <repo root>, or set CPP_PINYIN_ROOT / CPP_PINYIN_DICT."
    exit 2
}

# ---------------------------------------------------------------- generate
if (-not $SkipGenerate) {
    Write-Host "== generate =="
    Push-Location $repo
    try {
        $env:PYTHONIOENCODING = "utf-8"
        foreach ($gen in @("gen/mandarin.py", "gen/cantonese.py")) {
            Write-Host "  -> $gen"
            & $Python $gen
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: $gen failed with exit $LASTEXITCODE"
                exit 3
            }
        }
    } finally {
        Pop-Location
    }
}

# ---------------------------------------------------------------- what is compared
# The dialect ids and table names are DERIVED from the two trees, never listed in this script -- the
# same derivation as tools/compare_dict_dirs.py (`dialects_present()` / `table_names()`).
# Measured: a hardcoded "2 dialects x 4 tables" pair goes SILENTLY NARROW the day a third
# dialect appears -- the gate then keeps printing "0 drift" while attesting to nothing about it. That
# is not hypothetical here: teochew once lived in out\dict and left the repo.
$FALLBACK_TABLES = @("word.txt", "phrases_dict.txt", "phrases_map.txt", "trans_word.txt")  # fallback only

# A directory under either tree is a DIALECT only if it carries a marker a dialect has: one of the four
# tables or the manifest. Two things that are NOT dialects must not be counted as one:
#   * a crashed staging directory -- `out\dict\mandarin.staging` is left behind when a run dies mid-write;
#   * a half-created directory (empty, or holding only `.tmp` leftovers).
# Skipped directories are REPORTED by name, not dropped silently: a rule that hides what it ignored is the
# same class of defect as the hardcoded dialect list this derivation replaced (line 78 above).
function Test-DialectDir($root, $name) {
    $dir = Join-Path $root $name
    if ($name -like "*.*") { return $false }   # `.staging`, `.old`, `.bak`: never an id
    foreach ($marker in @($FALLBACK_TABLES + @("dialect.json", "format.txt"))) {
        if (Test-Path -LiteralPath (Join-Path $dir $marker)) { return $true }
    }
    return $false
}

function Get-DialectDirNames($root) {
    $all = @(Get-SubDirNames $root)
    $kept = @($all | Where-Object { Test-DialectDir $root $_ })
    $skipped = @($all | Where-Object { $kept -notcontains $_ })
    if ($skipped.Count -gt 0) {
        Write-Host "not a dialect (skipped): $($skipped -join ', ')  (under ${root}: no table, no manifest)"
    }
    return $kept
}

function Get-SubDirNames($root) {
    if (-not (Test-Path $root)) { return @() }
    return @(Get-ChildItem -LiteralPath $root -Force |
             Where-Object { $_.PSIsContainer } |
             ForEach-Object { $_.Name } |
             Sort-Object)
}

# required_tables of that dialect's dialect.json, or $null when that side carries no usable manifest.
# The producer's out\dict carries none, so the four historical tables are the FALLBACK there.
function Get-DeclaredTables($root, $lang) {
    $manifest = Join-Path (Join-Path $root $lang) "dialect.json"
    if (-not (Test-Path $manifest)) { return $null }
    try {
        $json = Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
    if ($null -eq $json.required_tables) { return $null }
    $names = @($json.required_tables | ForEach-Object { [string]$_ } | Where-Object { $_ -ne "" })
    if ($names.Count -eq 0) { return $null }
    return $names
}

# Union of both sides' declared tables; the historical four stay first so the report keeps its shape.
function Get-TableNames($rootA, $rootB, $lang) {
    $names = @()
    foreach ($root in @($rootA, $rootB)) {
        $declared = Get-DeclaredTables $root $lang
        if ($null -eq $declared) { $declared = $FALLBACK_TABLES }
        foreach ($t in $declared) { if ($names -notcontains $t) { $names += $t } }
    }
    return @(@($FALLBACK_TABLES | Where-Object { $names -contains $_ }) +
             @($names | Where-Object { $FALLBACK_TABLES -notcontains $_ }))
}

$genIds  = @(Get-DialectDirNames $outDir)
$repoIds = @(Get-DialectDirNames $repoDict)
$dialectIds = @(@($genIds) + @($repoIds) | Sort-Object -Unique)
if ($dialectIds.Count -eq 0) {
    Write-Host "ERROR: no dialect directory in either tree -- refusing to report 0 drift"
    Write-Host "       generated: $outDir"
    Write-Host "       repo     : $repoDict"
    exit 4
}

$files = @()
foreach ($lang in $dialectIds) {
    # format.txt is a MARKER, not a table, so it never appears in `required_tables` and the
    # derivation above cannot see it -- it has to be added here explicitly, or the format
    # generation promised by docs/STABILITY.md R13 goes uncompared.
    $files += [pscustomobject]@{ lang = $lang; name = "format.txt" }
    foreach ($name in @(Get-TableNames $outDir $repoDict $lang)) {
        $files += [pscustomobject]@{ lang = $lang; name = $name }
    }
}

# ---------------------------------------------------------------- compare
Write-Host "dialects      : $($dialectIds -join ', ')"
$onlyGen  = @($dialectIds | Where-Object { $genIds  -contains $_ -and $repoIds -notcontains $_ })
$onlyRepo = @($dialectIds | Where-Object { $repoIds -contains $_ -and $genIds  -notcontains $_ })
if ($onlyGen.Count -gt 0) {
    Write-Host "generated only: $($onlyGen -join ', ')  (nothing under the cpp-pinyin tree)"
}
if ($onlyRepo.Count -gt 0) {
    Write-Host "repo only     : $($onlyRepo -join ', ')  (nothing generated for it)"
}
Write-Host ""

function ConvertTo-Map($lines) {
    $m = @{}
    foreach ($l in $lines) {
        if ($l -notmatch ":") { continue }
        $i = $l.LastIndexOf(":")
        $m[$l.Substring(0, $i)] = $l.Substring($i + 1)
    }
    return $m
}

$rows = @()
$drift = 0

foreach ($f in $files) {
    $gen = Join-Path $outDir "$($f.lang)\$($f.name)"
    $live = Join-Path $repoDict "$($f.lang)\$($f.name)"

    if (-not (Test-Path $gen)) {
        # "generated missing" alone would misread when the whole dialect is one-sided, which the derived
        # scope above now surfaces on purpose -- name the exact situation instead.
        $verdict = "generated missing"
        if (-not (Test-Path $live)) { $verdict = "both missing" }
        $rows += [pscustomobject]@{ Lang = $f.lang; File = $f.name; Gen = 0; Live = 0; Verdict = $verdict }
        $drift++
        continue
    }
    if (-not (Test-Path $live)) {
        $rows += [pscustomobject]@{ Lang = $f.lang; File = $f.name; Gen = 0; Live = 0; Verdict = "repo missing" }
        $drift++
        continue
    }

    $gLines = @(Get-Content $gen -Encoding UTF8)
    $lLines = @(Get-Content $live -Encoding UTF8)

    if ($gLines.Count -ne $lLines.Count) {
        $rows += [pscustomobject]@{ Lang = $f.lang; File = $f.name; Gen = $gLines.Count; Live = $lLines.Count; Verdict = "line count" }
        $drift++
        continue
    }

    # Byte-exact first. An earlier version of this script compared the two files as key to reading
    # maps, which CANNOT see a pure reordering -- and for word.txt the first reading of a key is the
    # engine's default reading, while the order of the keys themselves is never consulted. Measured:
    # this script reported "IDENTICAL" for a Cantonese word.txt in which U+54A4 sat at a different
    # position, which is a real difference that the map form hid.
    $gBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $gen))
    $lBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $live))
    $a = [System.Security.Cryptography.SHA256]::Create()
    $gHash = [BitConverter]::ToString($a.ComputeHash($gBytes))
    $lHash = [BitConverter]::ToString($a.ComputeHash($lBytes))
    $a.Dispose()

    if ($gHash -eq $lHash) {
        $rows += [pscustomobject]@{ Lang = $f.lang; File = $f.name; Gen = $gLines.Count; Live = $lLines.Count; Verdict = "IDENTICAL (byte-exact)" }
        continue
    }

    # Bytes differ: describe WHERE, so the report stays useful instead of just saying "differ".
    $gm = ConvertTo-Map $gLines
    $lm = ConvertTo-Map $lLines
    $onlyGen = @($gm.Keys | Where-Object { -not $lm.ContainsKey($_) })
    $onlyLive = @($lm.Keys | Where-Object { -not $gm.ContainsKey($_) })
    $diffVal = @($gm.Keys | Where-Object { $lm.ContainsKey($_) -and $lm[$_] -ne $gm[$_] })

    $n = $onlyGen.Count + $onlyLive.Count + $diffVal.Count
    if ($n -eq 0) {
        $verdict = "order only (same keys and values, different sequence)"
    } else {
        $verdict = "DIFFERS gen=$($onlyGen.Count) live=$($onlyLive.Count) val=$($diffVal.Count)"
    }
    $rows += [pscustomobject]@{ Lang = $f.lang; File = $f.name; Gen = $gLines.Count; Live = $lLines.Count; Verdict = $verdict }
    $drift++
}

Write-Host ""
Write-Host "== drift report =="
$table = $rows | Format-Table -AutoSize | Out-String -Width 200
Write-Host $table

if ($drift -eq 0) {
    Write-Host "RESULT: generated output matches the repo exactly (0 drift)"
} else {
    Write-Host "RESULT: $drift file(s) drifted"
}

if ($WriteReport -ne "") {
    $md = @("# Dictionary drift report", "", "generated at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')", "",
            "| dialect | file | generated lines | repo lines | verdict |", "|---|---|---:|---:|---|")
    foreach ($r in $rows) {
        $md += "| $($r.Lang) | $($r.File) | $($r.Gen) | $($r.Live) | $($r.Verdict) |"
    }
    $md += "", "---", ""
    if ($drift -eq 0) { $md += "Verdict: no drift." } else { $md += "Verdict: drift present, needs attribution." }
    Set-Content -Path $WriteReport -Value ($md -join "`n") -Encoding UTF8
    Write-Host "report written to: $WriteReport"
}

if ($drift -eq 0) { exit 0 } else { exit 1 }
