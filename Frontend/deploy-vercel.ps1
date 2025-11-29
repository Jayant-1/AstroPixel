# Deploy to Vercel Script
# Run this from the Frontend directory

Write-Host "🚀 AstroPixel Vercel Deployment Script" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the Frontend directory
if (-not (Test-Path "package.json")) {
    Write-Host "❌ Error: Please run this script from the Frontend directory" -ForegroundColor Red
    exit 1
}

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

# Check if Vercel CLI is installed
$vercelInstalled = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelInstalled) {
    Write-Host "📥 Vercel CLI not found. Installing..." -ForegroundColor Yellow
    npm install -g vercel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install Vercel CLI" -ForegroundColor Red
        Write-Host "💡 Try running: npm install -g vercel" -ForegroundColor Yellow
        exit 1
    }
}

# Build the project to test
Write-Host "🔨 Building project..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed. Please fix errors before deploying." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build successful!" -ForegroundColor Green
Write-Host ""

# Ask for backend URL
Write-Host "⚙️  Configuration" -ForegroundColor Cyan
Write-Host "=================" -ForegroundColor Cyan
$backendUrl = Read-Host "Enter your backend API URL (or press Enter to skip)"

if ($backendUrl) {
    Write-Host "📝 Backend URL will be set to: $backendUrl" -ForegroundColor Yellow
} else {
    Write-Host "⚠️  No backend URL provided. You'll need to set VITE_API_BASE_URL in Vercel dashboard." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Ready to deploy!" -ForegroundColor Green
Write-Host ""
$deploy = Read-Host "Deploy to production? (y/n)"

if ($deploy -eq 'y' -or $deploy -eq 'Y') {
    Write-Host "🚀 Deploying to Vercel..." -ForegroundColor Cyan
    
    if ($backendUrl) {
        # Deploy with environment variable
        vercel --prod -e VITE_API_BASE_URL=$backendUrl
    } else {
        # Deploy without environment variable
        vercel --prod
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Deployment successful!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📋 Next steps:" -ForegroundColor Cyan
        Write-Host "1. Visit your Vercel dashboard to get your deployment URL"
        if (-not $backendUrl) {
            Write-Host "2. Add VITE_API_BASE_URL environment variable in Vercel dashboard"
            Write-Host "3. Redeploy from the dashboard"
        }
        Write-Host "4. Update backend CORS_ORIGINS to include your Vercel URL"
        Write-Host "5. Test your application!" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Deployment failed. Please check the errors above." -ForegroundColor Red
    }
} else {
    Write-Host "❌ Deployment cancelled" -ForegroundColor Yellow
    Write-Host "💡 Run 'vercel --prod' manually when ready" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "📚 For more help, see DEPLOYMENT_CHECKLIST.md" -ForegroundColor Cyan
