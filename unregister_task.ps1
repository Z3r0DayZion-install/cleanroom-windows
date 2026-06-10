param(
    [string]$TaskName = "CleanroomDaily"
)
Write-Host "Deleting scheduled task: $TaskName"
Start-Process -FilePath schtasks -ArgumentList '/Delete','/TN',$TaskName,'/F' -NoNewWindow -Wait
Write-Host "Done."
