param(
    [string]$StudentId = '30103254',
    [switch]$Smoke,
    [switch]$CommitMilestones,
    [double]$PeakBandwidthGBs = 0,
    [double]$PeakGflops = 0
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed with exit code $LASTEXITCODE" }
}
function Save-Milestone([string]$Message, [string]$Tag) {
    if ($CommitMilestones) {
        Invoke-Checked git @('add', '--', 'src', 'results', 'README.md', 'RUNNING.md', 'requirements.txt', 'run_lab.ps1', 'verify_outputs.py', 'course_verifier.py', '.gitignore')
        Invoke-Checked git @('commit', '-m', $Message)
        Invoke-Checked git @('tag', $Tag)
    }
}
if ($Smoke -and $CommitMilestones) { throw 'Smoke results cannot be tagged as submission milestones.' }
if ($CommitMilestones) {
    foreach ($tag in @('M0-ENV','M1-LOCALITY','M2-SHARING','M3-SCALING','M4-FINAL')) {
        $existing = & git tag --list $tag
        if ($existing) { throw "Tag $tag already exists. Use a fresh run without tags or inspect existing history." }
    }
    Invoke-Checked git @('var', 'GIT_AUTHOR_IDENT')
}
$extra = @()
if ($Smoke) { $extra = @('--smoke') }
Invoke-Checked python (@('src/profile_env.py', '--student-id', $StudentId) + $extra)
Save-Milestone 'M0: Environment and salting configuration' 'M0-ENV'
Invoke-Checked python (@('src/stride_bench.py') + $extra)
Invoke-Checked python (@('src/dense_kernel.py') + $extra)
Save-Milestone 'M1: Memory stride and loop interchange benchmarking' 'M1-LOCALITY'
Invoke-Checked python (@('src/false_sharing.py') + $extra)
Save-Milestone 'M2: False sharing reproduction and Karp-Flatt analysis' 'M2-SHARING'
$peaks = @()
if ($PeakBandwidthGBs -gt 0) { $peaks += @('--peak-bandwidth-gbs', "$PeakBandwidthGBs") }
if ($PeakGflops -gt 0) { $peaks += @('--peak-gflops', "$PeakGflops") }
Invoke-Checked python (@('src/scaling_study.py') + $extra + $peaks)
Save-Milestone 'M3: Strong and weak scaling evaluation' 'M3-SCALING'
$verification = @()
if (-not $Smoke) { $verification = @('--update-readme') }
Invoke-Checked python (@('verify_outputs.py') + $extra + $verification)
Save-Milestone 'M4: Final verification and completed practicum submission' 'M4-FINAL'
Write-Host 'Finished. Nothing has been pushed.'

