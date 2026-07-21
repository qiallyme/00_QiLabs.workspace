[CmdletBinding()]
param(
    [string]$Root = "C:\QiLabs",
    [string]$ConfigPath = "",
    [switch]$DryRun,
    [switch]$SkipHousekeeping,
    [switch]$SkipNode,
    [switch]$SkipGit,
    [switch]$NoCommit,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $ScriptRoot "qilabs.do-it-all.config.json"
}

function Normalize-InputPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    $clean = $PathValue.Trim()

    # Native Windows launchers can accidentally preserve quote characters
    # when a quoted path ends in a backslash.
    $clean = $clean.Trim([char]34)
    $clean = $clean.Trim()

    if ([string]::IsNullOrWhiteSpace($clean)) {
        throw "Path value is empty after normalization."
    }

    foreach ($invalidChar in [System.IO.Path]::GetInvalidPathChars()) {
        if ($clean.Contains([string]$invalidChar)) {
            throw "Path contains an illegal character after normalization: $clean"
        }
    }

    return [System.IO.Path]::GetFullPath($clean)
}

$Root = Normalize-InputPath -PathValue $Root
$ConfigPath = Normalize-InputPath -PathValue $ConfigPath

if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "QiLabs root does not exist: $Root"
}
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Configuration file not found: $ConfigPath"
}

$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$auditRoot = Join-Path $Root "00_QiLabs.workspace\90_audits\do_it_all"
New-Item -ItemType Directory -Path $auditRoot -Force | Out-Null
$logPath = Join-Path $auditRoot ("do-it-all-" + $timestamp + ".log")
$summaryPath = Join-Path $auditRoot ("do-it-all-" + $timestamp + ".json")
$lockPath = Join-Path $Root ".qilabs-do-it-all.lock"

$script:Failures = New-Object System.Collections.Generic.List[object]
$script:Warnings = New-Object System.Collections.Generic.List[object]
$script:Results = New-Object System.Collections.Generic.List[object]
$script:RemovedItems = 0

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO", "OK", "WARN", "ERROR", "STEP")]
        [string]$Level = "INFO"
    )

    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8

    switch ($Level) {
        "OK"    { Write-Host $line -ForegroundColor Green }
        "WARN"  { Write-Host $line -ForegroundColor Yellow }
        "ERROR" { Write-Host $line -ForegroundColor Red }
        "STEP"  { Write-Host "`n$line" -ForegroundColor Cyan }
        default { Write-Host $line }
    }
}

function Add-Result {
    param(
        [string]$Area,
        [string]$Target,
        [string]$Status,
        [string]$Message
    )

    $script:Results.Add([pscustomobject]@{
        area = $Area
        target = $Target
        status = $Status
        message = $Message
    })
}

function Add-Failure {
    param(
        [string]$Area,
        [string]$Target,
        [string]$Message
    )

    $script:Failures.Add([pscustomobject]@{
        area = $Area
        target = $Target
        message = $Message
    })
    Add-Result -Area $Area -Target $Target -Status "failed" -Message $Message
    Write-Log "$Area failed for ${Target}: $Message" "ERROR"
}

function Add-Warning {
    param(
        [string]$Area,
        [string]$Target,
        [string]$Message
    )

    $script:Warnings.Add([pscustomobject]@{
        area = $Area
        target = $Target
        message = $Message
    })
    Write-Log "$Area warning for ${Target}: $Message" "WARN"
}

function Invoke-GuardedPhase {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Action
    )

    try {
        & $Action | Out-Null
        return $true
    }
    catch {
        Add-Failure -Area "phase" -Target $Name -Message $_.Exception.Message

        if (-not [bool]$config.continue_on_error) {
            throw
        }

        Write-Log "Continuing after recoverable phase failure: $Name" "WARN"
        return $false
    }
}

function Test-CommandAvailable {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-OptionalProperty {
    param(
        [AllowNull()]
        [object]$InputObject,
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [AllowNull()]
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }

    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $DefaultValue
    }

    return $property.Value
}

function Invoke-ExternalCommand {
    param(
        [string]$Command,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $Root,
        [string]$Label = $Command,
        [switch]$AllowFailure
    )

    $displayArgs = ($Arguments -join " ")
    Write-Log "Running: $Command $displayArgs" "INFO"

    if ($DryRun) {
        Write-Log "Dry run: skipped $Label" "WARN"
        return 0
    }

    Push-Location $WorkingDirectory
    try {
        $output = & $Command @Arguments 2>&1
        $exitCode = $LASTEXITCODE

        foreach ($line in $output) {
            if ($null -ne $line) {
                Write-Log ([string]$line) "INFO"
            }
        }

        if ($exitCode -ne 0 -and -not $AllowFailure) {
            throw "$Label exited with code $exitCode"
        }

        return $exitCode
    }
    finally {
        Pop-Location
    }
}

function Test-PathUnder {
    param(
        [string]$Child,
        [string]$Parent
    )

    $childFull = [System.IO.Path]::GetFullPath($Child).TrimEnd("\")
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd("\")

    if ($childFull.Equals($parentFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }

    return $childFull.StartsWith(
        $parentFull + "\",
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-DirectoryDepth {
    param([string]$Path)
    return ([System.IO.Path]::GetFullPath($Path).TrimEnd("\").Split("\")).Count
}

function Get-GlobalSkipDirectoryNames {
    param([string[]]$AdditionalNames = @())

    $names = @(
        ".git",
        "node_modules",
        ".pnpm-store",
        ".yarn",
        ".next",
        "dist",
        "build",
        "coverage",
        "__pycache__",
        ".venv",
        "venv"
    )

    if ($null -ne $config.scope) {
        $names += @($config.scope.excluded_root_names)
        $names += @($config.scope.excluded_directory_names)
    }

    $names += @($AdditionalNames)
    return @($names | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Sort-Object -Unique)
}

function Get-SafeDirectoryWalk {
    param(
        [string]$StartPath,
        [string[]]$SkipDirectoryNames
    )

    $found = New-Object System.Collections.Generic.List[string]
    $stack = New-Object System.Collections.Generic.Stack[string]
    $stack.Push([System.IO.Path]::GetFullPath($StartPath))

    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        $found.Add($current)

        try {
            $children = Get-ChildItem `
                -LiteralPath $current `
                -Directory `
                -Force `
                -ErrorAction Stop
        }
        catch {
            Add-Warning `
                -Area "discovery" `
                -Target $current `
                -Message "Directory could not be scanned and was skipped: $($_.Exception.Message)"
            continue
        }

        foreach ($child in $children) {
            if ($SkipDirectoryNames -contains $child.Name) {
                continue
            }

            try {
                $stack.Push($child.FullName)
            }
            catch {
                Add-Warning `
                    -Area "discovery" `
                    -Target $child.FullName `
                    -Message "Directory path could not be queued and was skipped: $($_.Exception.Message)"
            }
        }
    }

    return @($found.ToArray())
}

function Remove-SafeBloat {
    Write-Log "Safe bloat cleanup" "STEP"

    $cleanupDirNames = @($config.cleanup.directory_names)
    $cleanupFilePatterns = @($config.cleanup.file_patterns)
    $skipTraversal = @(Get-GlobalSkipDirectoryNames -AdditionalNames @($config.cleanup.skip_traversal))

    Write-Log "Excluded roots/directories: $($skipTraversal -join ', ')" "INFO"

    $stack = New-Object System.Collections.Generic.Stack[string]
    $stack.Push($Root)

    while ($stack.Count -gt 0) {
        $current = $stack.Pop()

        $directories = Get-ChildItem -LiteralPath $current -Directory -Force -ErrorAction SilentlyContinue
        foreach ($directory in $directories) {
            if ($skipTraversal -contains $directory.Name) {
                continue
            }

            $isNextCache = (
                $directory.Name -eq "cache" -and
                $directory.Parent.Name -eq ".next"
            )

            if (($cleanupDirNames -contains $directory.Name) -or $isNextCache) {
                Write-Log "Remove directory: $($directory.FullName)" "INFO"
                if (-not $DryRun) {
                    try {
                        Remove-Item -LiteralPath $directory.FullName -Recurse -Force -ErrorAction Stop
                        $script:RemovedItems++
                    }
                    catch {
                        Add-Warning -Area "cleanup" -Target $directory.FullName -Message $_.Exception.Message
                    }
                }
                continue
            }

            $stack.Push($directory.FullName)
        }

        $files = Get-ChildItem -LiteralPath $current -File -Force -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            $matches = $false
            foreach ($pattern in $cleanupFilePatterns) {
                if ($file.Name -like $pattern) {
                    $matches = $true
                    break
                }
            }

            if ($matches) {
                Write-Log "Remove file: $($file.FullName)" "INFO"
                if (-not $DryRun) {
                    try {
                        Remove-Item -LiteralPath $file.FullName -Force -ErrorAction Stop
                        $script:RemovedItems++
                    }
                    catch {
                        Add-Warning -Area "cleanup" -Target $file.FullName -Message $_.Exception.Message
                    }
                }
            }
        }
    }

    if ($config.cleanup.prune_pnpm_store -and (Test-CommandAvailable "pnpm")) {
        try {
            [void](Invoke-ExternalCommand -Command "pnpm" -Arguments @("store", "prune") -WorkingDirectory $Root -Label "pnpm store prune")
        }
        catch {
            Add-Warning -Area "cleanup" -Target "pnpm store" -Message $_.Exception.Message
        }
    }

    if ($config.cleanup.verify_npm_cache -and (Test-CommandAvailable "npm")) {
        try {
            [void](Invoke-ExternalCommand -Command "npm" -Arguments @("cache", "verify") -WorkingDirectory $Root -Label "npm cache verify")
        }
        catch {
            Add-Warning -Area "cleanup" -Target "npm cache" -Message $_.Exception.Message
        }
    }

    Add-Result -Area "cleanup" -Target $Root -Status "completed" -Message "Removed $script:RemovedItems safe cache or log items."
    Write-Log "Safe cleanup completed. Removed items: $script:RemovedItems" "OK"
}

function Invoke-HousekeepingHooks {
    Write-Log "Housekeeping hooks" "STEP"

    foreach ($hook in @($config.housekeeping.hooks)) {
        if (-not $hook.enabled) {
            Write-Log "Housekeeping hook disabled: $($hook.name)" "INFO"
            continue
        }

        $workingDirectory = [string]$hook.working_directory
        if (-not [System.IO.Path]::IsPathRooted($workingDirectory)) {
            $workingDirectory = Join-Path $Root $workingDirectory
        }

        $command = [string]$hook.command
        if (-not [System.IO.Path]::IsPathRooted($command)) {
            $candidate = Join-Path $workingDirectory $command
            if (Test-Path -LiteralPath $candidate) {
                $command = $candidate
            }
        }

        if (-not (Test-Path -LiteralPath $workingDirectory -PathType Container)) {
            Add-Warning -Area "housekeeping" -Target $hook.name -Message "Working directory does not exist: $workingDirectory"
            continue
        }

        if (([System.IO.Path]::IsPathRooted($command)) -and (-not (Test-Path -LiteralPath $command))) {
            Add-Warning -Area "housekeeping" -Target $hook.name -Message "Command does not exist: $command"
            continue
        }

        try {
            Invoke-ExternalCommand `
                -Command $command `
                -Arguments @($hook.arguments) `
                -WorkingDirectory $workingDirectory `
                -Label $hook.name

            Add-Result -Area "housekeeping" -Target $hook.name -Status "completed" -Message "Hook completed."
            Write-Log "Housekeeping hook completed: $($hook.name)" "OK"
        }
        catch {
            Add-Failure -Area "housekeeping" -Target $hook.name -Message $_.Exception.Message
            if (-not $config.continue_on_error) {
                throw
            }
        }
    }
}

function Get-NodeProjectRoots {
    $skip = @(Get-GlobalSkipDirectoryNames)
    $directories = @(Get-SafeDirectoryWalk -StartPath $Root -SkipDirectoryNames $skip)
    $candidates = New-Object System.Collections.Generic.List[object]

    foreach ($directory in $directories) {
        try {
            $packagePath = Join-Path $directory "package.json"
            if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
                continue
            }

            try {
                $package = Get-Content `
                    -LiteralPath $packagePath `
                    -Raw `
                    -Encoding UTF8 `
                    -ErrorAction Stop |
                    ConvertFrom-Json -ErrorAction Stop
            }
            catch {
                Add-Warning `
                    -Area "node-discovery" `
                    -Target $packagePath `
                    -Message "Invalid package.json; project skipped: $($_.Exception.Message)"

                Add-Result `
                    -Area "node" `
                    -Target $directory `
                    -Status "skipped" `
                    -Message "Invalid package.json."
                continue
            }

            $manager = ""
            $lockFile = ""

            if (Test-Path -LiteralPath (Join-Path $directory "pnpm-lock.yaml")) {
                $manager = "pnpm"
                $lockFile = "pnpm-lock.yaml"
            }
            elseif (Test-Path -LiteralPath (Join-Path $directory "package-lock.json")) {
                $manager = "npm"
                $lockFile = "package-lock.json"
            }
            elseif (
                (Test-Path -LiteralPath (Join-Path $directory "yarn.lock")) -or
                (Test-Path -LiteralPath (Join-Path $directory ".yarnrc.yml"))
            ) {
                $manager = "yarn"
                $lockFile = "yarn.lock"
            }
            elseif (
                (Test-Path -LiteralPath (Join-Path $directory "bun.lock")) -or
                (Test-Path -LiteralPath (Join-Path $directory "bun.lockb"))
            ) {
                $manager = "bun"
                $lockFile = "bun.lock"
            }
            else {
                $packageManagerValue = Get-OptionalProperty `
                    -InputObject $package `
                    -Name "packageManager"

                if (
                    $null -ne $packageManagerValue -and
                    -not [string]::IsNullOrWhiteSpace([string]$packageManagerValue)
                ) {
                    $manager = ([string]$packageManagerValue).Split("@")[0]
                }
            }

            $workspacesValue = Get-OptionalProperty `
                -InputObject $package `
                -Name "workspaces"

            $hasWorkspaces = $null -ne $workspacesValue
            $hasAncestorPackage = $false
            $parent = Split-Path -Parent $directory

            while (
                -not [string]::IsNullOrWhiteSpace($parent) -and
                (Test-PathUnder -Child $parent -Parent $Root)
            ) {
                if (Test-Path -LiteralPath (Join-Path $parent "package.json") -PathType Leaf) {
                    $hasAncestorPackage = $true
                    break
                }

                $nextParent = Split-Path -Parent $parent
                if ($nextParent -eq $parent) {
                    break
                }

                $parent = $nextParent
            }

            if ($manager -or $hasWorkspaces -or (-not $hasAncestorPackage)) {
                $candidates.Add([pscustomobject]@{
                    path = $directory
                    package = $package
                    manager = $manager
                    lock_file = $lockFile
                    has_workspaces = $hasWorkspaces
                    depth = Get-DirectoryDepth $directory
                })
            }
        }
        catch {
            Add-Warning `
                -Area "node-discovery" `
                -Target $directory `
                -Message "Project discovery failed and was skipped: $($_.Exception.Message)"

            Add-Result `
                -Area "node" `
                -Target $directory `
                -Status "skipped" `
                -Message "Project discovery error."
            continue
        }
    }

    $workspaceRoots = @(
        $candidates.ToArray() |
        Where-Object { $_.has_workspaces } |
        Sort-Object depth
    )

    $selected = New-Object System.Collections.Generic.List[object]

    foreach ($candidate in ($candidates.ToArray() | Sort-Object depth)) {
        try {
            $coveredByWorkspace = $false

            foreach ($workspace in $workspaceRoots) {
                if (
                    $candidate.path -ne $workspace.path -and
                    (Test-PathUnder -Child $candidate.path -Parent $workspace.path)
                ) {
                    $nestedGitMarker = Join-Path $candidate.path ".git"

                    if (-not (Test-Path -LiteralPath $nestedGitMarker)) {
                        $coveredByWorkspace = $true
                        break
                    }
                }
            }

            if ($coveredByWorkspace) {
                continue
            }

            $alreadySelected = $false
            foreach ($existing in $selected.ToArray()) {
                if ($existing.path -eq $candidate.path) {
                    $alreadySelected = $true
                    break
                }
            }

            if (-not $alreadySelected) {
                $selected.Add($candidate)
            }
        }
        catch {
            Add-Warning `
                -Area "node-discovery" `
                -Target ([string]$candidate.path) `
                -Message "Workspace resolution failed and was skipped: $($_.Exception.Message)"
        }
    }

    return @($selected.ToArray())
}

function Get-PackageScriptNames {
    param([object]$Package)

    $scripts = Get-OptionalProperty -InputObject $Package -Name "scripts"
    if ($null -eq $scripts) {
        return @()
    }

    return @($scripts.PSObject.Properties.Name)
}

function Invoke-NodeProjects {
    Write-Log "Node dependency sync and builds" "STEP"

    $projects = @(Get-NodeProjectRoots)
    Write-Log "Node project roots found: $($projects.Count)" "INFO"

    foreach ($project in $projects) {
        $projectPath = [string]$project.path
        $manager = [string]$project.manager

        if ([string]::IsNullOrWhiteSpace($manager)) {
            $manager = [string]$config.node.default_manager
        }

        if (-not (Test-CommandAvailable $manager)) {
            Add-Failure -Area "node" -Target $projectPath -Message "Package manager is not installed or not on PATH: $manager"
            if (-not $config.continue_on_error) {
                throw "Missing package manager: $manager"
            }
            continue
        }

        try {
            switch ($manager) {
                "npm" {
                    $installArgs = @("install")
                    if (
                        $config.node.prefer_lockfile_install -and
                        (Test-Path -LiteralPath (Join-Path $projectPath "package-lock.json"))
                    ) {
                        $installArgs = @("ci")
                    }

                    try {
                        Invoke-ExternalCommand -Command "npm" -Arguments $installArgs -WorkingDirectory $projectPath -Label "npm dependency sync"
                    }
                    catch {
                        if ($config.node.allow_install_fallback -and ($installArgs[0] -eq "ci")) {
                            Add-Warning -Area "node" -Target $projectPath -Message "npm ci failed; falling back to npm install."
                            Invoke-ExternalCommand -Command "npm" -Arguments @("install") -WorkingDirectory $projectPath -Label "npm install fallback"
                        }
                        else {
                            throw
                        }
                    }
                }

                "pnpm" {
                    $installArgs = @("install")
                    if ($config.node.prefer_lockfile_install) {
                        $installArgs += "--frozen-lockfile"
                    }

                    try {
                        Invoke-ExternalCommand -Command "pnpm" -Arguments $installArgs -WorkingDirectory $projectPath -Label "pnpm dependency sync"
                    }
                    catch {
                        if ($config.node.allow_install_fallback) {
                            Add-Warning -Area "node" -Target $projectPath -Message "Frozen pnpm install failed; falling back to pnpm install."
                            Invoke-ExternalCommand -Command "pnpm" -Arguments @("install") -WorkingDirectory $projectPath -Label "pnpm install fallback"
                        }
                        else {
                            throw
                        }
                    }
                }

                "yarn" {
                    $installArgs = @("install")
                    if ($config.node.prefer_lockfile_install) {
                        $installArgs += "--immutable"
                    }

                    try {
                        Invoke-ExternalCommand -Command "yarn" -Arguments $installArgs -WorkingDirectory $projectPath -Label "yarn dependency sync"
                    }
                    catch {
                        if ($config.node.allow_install_fallback) {
                            Add-Warning -Area "node" -Target $projectPath -Message "Immutable yarn install failed; falling back to yarn install."
                            Invoke-ExternalCommand -Command "yarn" -Arguments @("install") -WorkingDirectory $projectPath -Label "yarn install fallback"
                        }
                        else {
                            throw
                        }
                    }
                }

                "bun" {
                    $installArgs = @("install")
                    if ($config.node.prefer_lockfile_install) {
                        $installArgs += "--frozen-lockfile"
                    }

                    try {
                        Invoke-ExternalCommand -Command "bun" -Arguments $installArgs -WorkingDirectory $projectPath -Label "bun dependency sync"
                    }
                    catch {
                        if ($config.node.allow_install_fallback) {
                            Add-Warning -Area "node" -Target $projectPath -Message "Frozen bun install failed; falling back to bun install."
                            Invoke-ExternalCommand -Command "bun" -Arguments @("install") -WorkingDirectory $projectPath -Label "bun install fallback"
                        }
                        else {
                            throw
                        }
                    }
                }

                default {
                    throw "Unsupported package manager '$manager' in $projectPath"
                }
            }

            $scriptNames = @(Get-PackageScriptNames -Package $project.package)
            $buildScript = [string]$config.node.build_script

            if ($scriptNames -contains $buildScript) {
                Invoke-ExternalCommand `
                    -Command $manager `
                    -Arguments @("run", $buildScript) `
                    -WorkingDirectory $projectPath `
                    -Label "$manager run $buildScript"

                Add-Result -Area "node" -Target $projectPath -Status "completed" -Message "Dependencies synchronized and build completed."
                Write-Log "Node project completed: $projectPath" "OK"
            }
            else {
                Add-Result -Area "node" -Target $projectPath -Status "completed" -Message "Dependencies synchronized; no build script found."
                Write-Log "Dependencies synchronized; no '$buildScript' script: $projectPath" "OK"
            }
        }
        catch {
            Add-Failure -Area "node" -Target $projectPath -Message $_.Exception.Message
            if (-not $config.continue_on_error) {
                throw
            }
        }
    }
}

function Get-GitRepositories {
    $skip = @(Get-GlobalSkipDirectoryNames)

    $repos = New-Object System.Collections.Generic.List[string]
    $stack = New-Object System.Collections.Generic.Stack[string]
    $stack.Push($Root)

    while ($stack.Count -gt 0) {
        $current = $stack.Pop()

        try {
            $gitMarker = Join-Path $current ".git"

            if (Test-Path -LiteralPath $gitMarker) {
                $repos.Add($current)
            }

            $children = Get-ChildItem `
                -LiteralPath $current `
                -Directory `
                -Force `
                -ErrorAction Stop

            foreach ($child in $children) {
                if ($skip -contains $child.Name) {
                    continue
                }

                $stack.Push($child.FullName)
            }
        }
        catch {
            Add-Warning `
                -Area "git-discovery" `
                -Target $current `
                -Message "Directory could not be scanned for repositories and was skipped: $($_.Exception.Message)"
            continue
        }
    }

    $unique = @($repos.ToArray() | Sort-Object -Unique)

    return @(
        $unique |
        Sort-Object { Get-DirectoryDepth $_ } -Descending
    )
}

function Test-RepositorySkipped {
    param([string]$Repository)

    foreach ($skipPath in @($config.git.skip_repositories)) {
        $fullSkipPath = [string]$skipPath
        if (-not [System.IO.Path]::IsPathRooted($fullSkipPath)) {
            $fullSkipPath = Join-Path $Root $fullSkipPath
        }

        if (
            [System.IO.Path]::GetFullPath($Repository).TrimEnd("\").Equals(
                [System.IO.Path]::GetFullPath($fullSkipPath).TrimEnd("\"),
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            return $true
        }
    }

    return $false
}

function Get-GitChangedPaths {
    param([string]$Repository)

    $statusOutput = & git -C $Repository status --porcelain=v1 -uall 2>$null
    $paths = New-Object System.Collections.Generic.List[string]

    foreach ($line in $statusOutput) {
        if ([string]::IsNullOrWhiteSpace([string]$line)) {
            continue
        }

        try {
            $lineText = [string]$line
            $startIndex = [Math]::Min(3, $lineText.Length)
            $pathText = $lineText.Substring($startIndex).Trim()

            if ($pathText -like '* -> *') {
                $pathText = ($pathText -split ' -> ')[-1]
            }

            $pathText = $pathText.Trim('"')
            $paths.Add($pathText)
        }
        catch {
            Add-Warning `
                -Area "git-discovery" `
                -Target $Repository `
                -Message "One Git status row could not be parsed and was skipped."
        }
    }

    return @($paths.ToArray())
}

function Find-ProtectedChanges {
    param([string]$Repository)

    $protected = New-Object System.Collections.Generic.List[string]
    $paths = @(Get-GitChangedPaths -Repository $Repository)

    foreach ($path in $paths) {
        $leaf = Split-Path -Leaf $path

        foreach ($pattern in @($config.git.protected_file_patterns)) {
            if (($path -like $pattern) -or ($leaf -like $pattern)) {
                $protected.Add($path)
                break
            }
        }
    }

    return @($protected | Sort-Object -Unique)
}

function Test-GitHasChanges {
    param([string]$Repository)

    & git -C $Repository diff --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $true
    }

    & git -C $Repository diff --cached --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $true
    }

    $untracked = & git -C $Repository ls-files --others --exclude-standard 2>$null
    return @($untracked).Count -gt 0
}

function Test-GitHasStagedChanges {
    param([string]$Repository)

    & git -C $Repository diff --cached --quiet 2>$null
    return $LASTEXITCODE -ne 0
}

function Get-GitCurrentBranch {
    param([string]$Repository)

    $branch = (& git -C $Repository branch --show-current 2>$null | Select-Object -First 1)
    return ([string]$branch).Trim()
}

function Test-GitRemoteExists {
    param(
        [string]$Repository,
        [string]$Remote
    )

    $remotes = @(& git -C $Repository remote 2>$null)
    return $remotes -contains $Remote
}

function Invoke-GitRepositories {
    Write-Log "Git repositories: nested first" "STEP"

    if (-not (Test-CommandAvailable "git")) {
        throw "Git is not installed or not on PATH."
    }

    $repositories = @(Get-GitRepositories)
    Write-Log "Git repositories found: $($repositories.Count)" "INFO"

    foreach ($repository in $repositories) {
        if (Test-RepositorySkipped -Repository $repository) {
            Write-Log "Skipped repository by configuration: $repository" "WARN"
            Add-Result -Area "git" -Target $repository -Status "skipped" -Message "Skipped by configuration."
            continue
        }

        Write-Log "Repository: $repository" "STEP"

        try {
            $isRepo = (& git -C $repository rev-parse --is-inside-work-tree 2>$null | Select-Object -First 1)
            if (([string]$isRepo).Trim() -ne "true") {
                throw "Not a valid Git work tree."
            }

            $branch = Get-GitCurrentBranch -Repository $repository
            if ([string]::IsNullOrWhiteSpace($branch)) {
                throw "Repository is in detached HEAD state."
            }

            $protectedChanges = @(Find-ProtectedChanges -Repository $repository)
            if ($protectedChanges.Count -gt 0) {
                throw "Protected or secret-like changed files detected: $($protectedChanges -join ', ')"
            }

            $hasChanges = Test-GitHasChanges -Repository $repository
            $autoCommit = [bool]$config.git.auto_commit -and (-not $NoCommit)

            if ($hasChanges -and $autoCommit) {
                Invoke-ExternalCommand -Command "git" -Arguments @("-C", $repository, "add", "-A") -WorkingDirectory $Root -Label "git add"

                Invoke-ExternalCommand -Command "git" -Arguments @("-C", $repository, "diff", "--cached", "--check") -WorkingDirectory $Root -Label "git staged diff check"

                if (Test-GitHasStagedChanges -Repository $repository) {
                    $commitTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
                    $commitMessage = ([string]$config.git.commit_message_template).Replace("{timestamp}", $commitTimestamp)

                    Invoke-ExternalCommand `
                        -Command "git" `
                        -Arguments @("-C", $repository, "commit", "-m", $commitMessage) `
                        -WorkingDirectory $Root `
                        -Label "git commit"
                }
            }
            elseif ($hasChanges -and (-not $autoCommit)) {
                Add-Warning -Area "git" -Target $repository -Message "Repository has changes, but automatic commit is disabled. Pull and push were skipped."
                Add-Result -Area "git" -Target $repository -Status "skipped" -Message "Dirty repository with auto-commit disabled."
                continue
            }

            $remote = [string]$config.git.remote
            if (-not (Test-GitRemoteExists -Repository $repository -Remote $remote)) {
                Add-Warning -Area "git" -Target $repository -Message "Remote '$remote' does not exist. Commit retained locally."
                Add-Result -Area "git" -Target $repository -Status "local-only" -Message "No configured remote."
                continue
            }

            Invoke-ExternalCommand `
                -Command "git" `
                -Arguments @("-C", $repository, "fetch", $remote, "--prune") `
                -WorkingDirectory $Root `
                -Label "git fetch"

            $upstream = (& git -C $repository rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null | Select-Object -First 1)
            if (-not [string]::IsNullOrWhiteSpace([string]$upstream)) {
                try {
                    Invoke-ExternalCommand `
                        -Command "git" `
                        -Arguments @("-C", $repository, "pull", "--rebase") `
                        -WorkingDirectory $Root `
                        -Label "git pull --rebase"
                }
                catch {
                    & git -C $repository rebase --abort 2>$null | Out-Null
                    throw "Pull/rebase failed and was aborted: $($_.Exception.Message)"
                }
            }

            $shouldPush = [bool]$config.git.push -and (-not $NoPush)
            if ($shouldPush) {
                Invoke-ExternalCommand `
                    -Command "git" `
                    -Arguments @("-C", $repository, "push", "-u", $remote, $branch) `
                    -WorkingDirectory $Root `
                    -Label "git push"
            }
            else {
                Write-Log "Push disabled for repository: $repository" "WARN"
            }

            if ($config.git.run_maintenance) {
                try {
                    Invoke-ExternalCommand `
                        -Command "git" `
                        -Arguments @("-C", $repository, "maintenance", "run", "--auto") `
                        -WorkingDirectory $Root `
                        -Label "git maintenance" `
                        -AllowFailure
                }
                catch {
                    Add-Warning -Area "git" -Target $repository -Message "Git maintenance failed: $($_.Exception.Message)"
                }
            }

            Add-Result -Area "git" -Target $repository -Status "completed" -Message "Repository synchronized on branch $branch."
            Write-Log "Repository completed: $repository" "OK"
        }
        catch {
            Add-Failure -Area "git" -Target $repository -Message $_.Exception.Message
            if (-not $config.continue_on_error) {
                throw
            }
        }
    }
}

function Write-RunSummary {
    $completed = @($script:Results | Where-Object { $_.status -eq "completed" }).Count
    $failed = $script:Failures.Count
    $warnings = $script:Warnings.Count

    $summary = [ordered]@{
        generated_at = (Get-Date).ToString("o")
        root = $Root
        dry_run = [bool]$DryRun
        log_path = $logPath
        completed_results = $completed
        failures = $failed
        warnings = $warnings
        removed_items = $script:RemovedItems
        results = @($script:Results | ForEach-Object { $_ })
        failure_details = @($script:Failures | ForEach-Object { $_ })
        warning_details = @($script:Warnings | ForEach-Object { $_ })
    }

    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

    Write-Log "Run summary" "STEP"
    Write-Log "Completed results: $completed" "INFO"
    Write-Log "Warnings: $warnings" $(if ($warnings -gt 0) { "WARN" } else { "INFO" })
    Write-Log "Failures: $failed" $(if ($failed -gt 0) { "ERROR" } else { "INFO" })
    Write-Log "Log: $logPath" "INFO"
    Write-Log "JSON summary: $summaryPath" "INFO"
}

if (Test-Path -LiteralPath $lockPath) {
    throw "Another QiLabs Do-It-All run may already be active. Lock file: $lockPath"
}

try {
    Set-Content -LiteralPath $lockPath -Value ("PID={0}`nStarted={1}" -f $PID, (Get-Date).ToString("o")) -Encoding ASCII

    Write-Log "QiLabs Do-It-All started" "STEP"
    Write-Log "Root: $Root" "INFO"
    Write-Log "Dry run: $([bool]$DryRun)" "INFO"
    Write-Log "Globally excluded roots: $(@($config.scope.excluded_root_names) -join ', ')" "INFO"
    Write-Log "Globally excluded directory names: $(@($config.scope.excluded_directory_names) -join ', ')" "INFO"

    if (-not $SkipHousekeeping) {
        [void](Invoke-GuardedPhase -Name "housekeeping" -Action {
            if ([bool]$config.cleanup.enabled) {
                Remove-SafeBloat
            }

            Invoke-HousekeepingHooks
        })
    }
    else {
        Write-Log "Housekeeping skipped by command-line switch." "WARN"
    }

    if (-not $SkipNode) {
        [void](Invoke-GuardedPhase -Name "node" -Action {
            Invoke-NodeProjects
        })
    }
    else {
        Write-Log "Node dependency sync and builds skipped by command-line switch." "WARN"
    }

    if (-not $SkipGit) {
        [void](Invoke-GuardedPhase -Name "git" -Action {
            Invoke-GitRepositories
        })
    }
    else {
        Write-Log "Git synchronization skipped by command-line switch." "WARN"
    }

    Write-RunSummary

    if ($script:Failures.Count -gt 0) {
        Write-Log "QiLabs Do-It-All completed with recoverable issues." "WARN"
        exit 2
    }

    Write-Log "QiLabs Do-It-All finished successfully." "OK"
    exit 0
}
catch {
    Add-Failure -Area "pipeline-fatal" -Target $Root -Message $_.Exception.Message

    try {
        Write-RunSummary
    }
    catch {
        Write-Host "Fatal error while writing the run summary: $($_.Exception.Message)" -ForegroundColor Red
    }

    exit 1
}
finally {
    if (Test-Path -LiteralPath $lockPath) {
        Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
    }
}
