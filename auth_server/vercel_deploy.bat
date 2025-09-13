@echo off
echo Installing Vercel CLI...
npm install -g vercel

echo Deploying to Vercel...
cd /d "%~dp0"
vercel --prod

echo Deployment complete!
pause
