Write-Host "Stopping and removing old containers..."
docker-compose down

Write-Host "Building new image..."
docker-compose build

Write-Host "Starting new containers..."
docker-compose up -d

Write-Host "Showing logs..."
docker-compose logs -f
