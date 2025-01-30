# Load environment variables from .env
$envContent = Get-Content .env
$envVars = @{}
foreach ($line in $envContent) {
    if ($line -match '^([^=]+)=(.*)$') {
        $envVars[$Matches[1]] = $Matches[2]
    }
}

# Configuration - Add your test URLs here
$TEST_CASES = @(
    @{
        name = "Playlist ID Only"
        query = "PLIKUS86KWNlaCU_zLQV9V6Xgozy3GSZfQ"
        description = "Testing with direct playlist ID"
    },
    @{
        name = "Full Playlist URL"
        query = "https://www.youtube.com/playlist?list=PLIKUS86KWNlaCU_zLQV9V6Xgozy3GSZfQ"
        description = "Testing with complete YouTube playlist URL"
    },
    @{
        name = "Video ID Only"
        query = "jvXc9hT8-zY"
        description = "Testing with direct video ID"
    },
    @{
        name = "Full Video URL"
        query = "https://www.youtube.com/watch?v=jvXc9hT8-zY"
        description = "Testing with complete YouTube video URL"
    },
    @{
        name = "Short Video URL"
        query = "https://youtu.be/jvXc9hT8-zY?si=KOhHys80MOfVKq1b"
        description = "Testing with shortened YouTube URL"
    }
)

# API Configuration
$API_URL = "http://localhost:8001/api/youtube-summary-agent"
$BEARER_TOKEN = $envVars["API_BEARER_TOKEN"]

if (-not $BEARER_TOKEN) {
    Write-Host "❌ Error: API_BEARER_TOKEN not found in .env file" -ForegroundColor Red
    exit 1
}

# Headers setup
$headers = @{
    "Authorization" = "Bearer $BEARER_TOKEN"
    "Content-Type" = "application/json"
}

# Run tests
Write-Host "`n🧪 Starting YouTube Summary Agent Tests`n" -ForegroundColor Cyan

foreach ($test in $TEST_CASES) {
    Write-Host "📌 Testing: $($test.name)" -ForegroundColor Yellow
    Write-Host "Description: $($test.description)"
    Write-Host "Query: $($test.query)"
    
    $body = @{
        query = $test.query
        user_id = "test-user"
        request_id = "test-request"
        session_id = "test-session-$($test.name.ToLower() -replace '\s+', '-')"
    } | ConvertTo-Json
    
    try {
        $response = Invoke-WebRequest -Uri $API_URL `
            -Method Post `
            -Headers $headers `
            -Body $body
        
        Write-Host "`n✅ Response:" -ForegroundColor Green
        $response.Content | ConvertFrom-Json | Select-Object -ExpandProperty response | Write-Host
    }
    catch {
        Write-Host "`n❌ Error:" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
    
    Write-Host "`n$("-" * 80)`n"
}

Write-Host "🏁 Testing Complete`n" -ForegroundColor Cyan 