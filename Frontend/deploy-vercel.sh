#!/bin/bash

# Deploy to Vercel Script (Bash version)
# Run this from the Frontend directory

echo "🚀 AstroPixel Vercel Deployment Script"
echo "======================================="
echo ""

# Check if we're in the Frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the Frontend directory"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📥 Vercel CLI not found. Installing..."
    npm install -g vercel
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Vercel CLI"
        echo "💡 Try running: npm install -g vercel"
        exit 1
    fi
fi

# Build the project to test
echo "🔨 Building project..."
npm run build
if [ $? -ne 0 ]; then
    echo "❌ Build failed. Please fix errors before deploying."
    exit 1
fi

echo "✅ Build successful!"
echo ""

# Ask for backend URL
echo "⚙️  Configuration"
echo "================="
read -p "Enter your backend API URL (or press Enter to skip): " backendUrl

if [ ! -z "$backendUrl" ]; then
    echo "📝 Backend URL will be set to: $backendUrl"
else
    echo "⚠️  No backend URL provided. You'll need to set VITE_API_BASE_URL in Vercel dashboard."
fi

echo ""
echo "🚀 Ready to deploy!"
echo ""
read -p "Deploy to production? (y/n): " deploy

if [ "$deploy" = "y" ] || [ "$deploy" = "Y" ]; then
    echo "🚀 Deploying to Vercel..."
    
    if [ ! -z "$backendUrl" ]; then
        # Deploy with environment variable
        vercel --prod -e VITE_API_BASE_URL=$backendUrl
    else
        # Deploy without environment variable
        vercel --prod
    fi
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Deployment successful!"
        echo ""
        echo "📋 Next steps:"
        echo "1. Visit your Vercel dashboard to get your deployment URL"
        if [ -z "$backendUrl" ]; then
            echo "2. Add VITE_API_BASE_URL environment variable in Vercel dashboard"
            echo "3. Redeploy from the dashboard"
        fi
        echo "4. Update backend CORS_ORIGINS to include your Vercel URL"
        echo "5. Test your application!"
    else
        echo "❌ Deployment failed. Please check the errors above."
    fi
else
    echo "❌ Deployment cancelled"
    echo "💡 Run 'vercel --prod' manually when ready"
fi

echo ""
echo "📚 For more help, see DEPLOYMENT_CHECKLIST.md"
