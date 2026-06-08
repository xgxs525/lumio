$env:PYTHONPATH = "$PSScriptRoot"
Set-Location $PSScriptRoot
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo
