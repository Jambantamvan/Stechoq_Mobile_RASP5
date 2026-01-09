# PowerShell script untuk upload ke GitHub
# Run di PowerShell sebagai Administrator

Write-Host "🚀 Upload Mobil_raspy to GitHub Repository" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

$sourceDir = "d:\Folder Kerja\mobile-stechog\Mobile_Steckhoq_Windows-main\Mobil_raspy"
$repoUrl = "https://github.com/Jambantamvan/Stechoq_Mobile_RASP5.git"
$tempDir = "$env:TEMP\Stechoq_Mobile_RASP5"

Write-Host "📂 Source directory: $sourceDir" -ForegroundColor Cyan
Write-Host "🌐 Repository: $repoUrl" -ForegroundColor Cyan
Write-Host "📁 Temp directory: $tempDir" -ForegroundColor Cyan
Write-Host ""

# Check if Git is installed
try {
    git --version | Out-Null
    Write-Host "✅ Git is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Git not found! Please install Git first" -ForegroundColor Red
    Write-Host "   Download from: https://git-scm.com/" -ForegroundColor Yellow
    exit 1
}

# Check if source directory exists
if (-not (Test-Path $sourceDir)) {
    Write-Host "❌ Source directory not found: $sourceDir" -ForegroundColor Red
    exit 1
}

Write-Host "🔍 Checking source files..." -ForegroundColor Yellow
$sourceFiles = Get-ChildItem -Path $sourceDir -File
Write-Host "   Found $($sourceFiles.Count) files:" -ForegroundColor Cyan
foreach ($file in $sourceFiles) {
    Write-Host "   ✓ $($file.Name)" -ForegroundColor Gray
}
Write-Host ""

# Remove temp directory if exists
if (Test-Path $tempDir) {
    Write-Host "🧹 Cleaning up temp directory..." -ForegroundColor Yellow
    Remove-Item $tempDir -Recurse -Force
}

# Clone repository
Write-Host "📥 Cloning repository..." -ForegroundColor Yellow
try {
    git clone $repoUrl $tempDir
    if ($LASTEXITCODE -ne 0) {
        throw "Git clone failed"
    }
    Write-Host "✅ Repository cloned successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to clone repository!" -ForegroundColor Red
    Write-Host "   Make sure you have access to the repository" -ForegroundColor Yellow
    exit 1
}

# Copy files
Write-Host "📋 Copying files..." -ForegroundColor Yellow
$copiedCount = 0

foreach ($file in $sourceFiles) {
    $sourcePath = $file.FullName
    $destName = $file.Name
    
    # Rename README_GITHUB.md to README.md
    if ($destName -eq "README_GITHUB.md") {
        $destName = "README.md"
        Write-Host "   📝 Renaming README_GITHUB.md → README.md" -ForegroundColor Cyan
    }
    
    $destPath = Join-Path $tempDir $destName
    
    try {
        Copy-Item $sourcePath $destPath -Force
        Write-Host "   ✓ $destName" -ForegroundColor Gray
        $copiedCount++
    } catch {
        Write-Host "   ❌ Failed to copy: $($file.Name)" -ForegroundColor Red
    }
}

Write-Host "✅ Copied $copiedCount files" -ForegroundColor Green
Write-Host ""

# Change to repository directory
Set-Location $tempDir

# Add files to git
Write-Host "📝 Adding files to Git..." -ForegroundColor Yellow
git add .

# Check status
Write-Host "📊 Git status:" -ForegroundColor Cyan
git status --short

Write-Host ""
Write-Host "🎯 Ready to commit and push!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Ask user for confirmation
$confirm = Read-Host "Commit and push to GitHub? (y/N)"
if ($confirm -match "^[Yy]$") {
    Write-Host "📤 Committing and pushing..." -ForegroundColor Yellow
    
    # Commit
    $commitMessage = @"
Add AI Voice Robot Controller for Raspberry Pi 5

Features:
- Voice control dengan Faster-Whisper STT (Indonesian)
- AI processing dengan Ollama + Qwen2.5:1.5b model
- Piper TTS untuk Indonesian voice output  
- Dual serial communication (USB & GPIO UART)
- Complete automated setup untuk Raspberry Pi 5
- Real-time monitoring & debugging tools
- Comprehensive documentation & troubleshooting

Hardware Support:
- Raspberry Pi 5 (ARM64 optimized)
- ESP32 robot dengan motor control
- USB microphone & speaker/headphones
- GPIO status LEDs

Ready untuk production deployment!
"@

    git commit -m $commitMessage
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Committed successfully" -ForegroundColor Green
        
        # Push
        git push origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "🎉 Successfully uploaded to GitHub!" -ForegroundColor Green
            Write-Host "🌐 Repository: $repoUrl" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Next steps:" -ForegroundColor Yellow
            Write-Host "1. Test clone on Raspberry Pi 5" -ForegroundColor Gray
            Write-Host "2. Run ./quick_start.sh for setup" -ForegroundColor Gray  
            Write-Host "3. Connect ESP32 hardware" -ForegroundColor Gray
            Write-Host "4. Upload ESP32_Robot_RaspyPi5.ino" -ForegroundColor Gray
            Write-Host "5. Run ./run_raspy.sh" -ForegroundColor Gray
        } else {
            Write-Host "❌ Failed to push to GitHub!" -ForegroundColor Red
            Write-Host "   Check your GitHub permissions" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Failed to commit!" -ForegroundColor Red
    }
} else {
    Write-Host "ℹ️  Upload cancelled by user" -ForegroundColor Yellow
    Write-Host "   Files are ready in: $tempDir" -ForegroundColor Cyan
    Write-Host "   You can manually commit and push later" -ForegroundColor Gray
}

# Cleanup
Write-Host ""
Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
Set-Location $PSScriptRoot
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "✅ Done!" -ForegroundColor Green