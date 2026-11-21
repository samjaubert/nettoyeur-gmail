# Crée la tâche planifiée Windows qui met à jour « Suivi finances » (Linxea) puis publie vers Mon Spirit 2.
# Usage (PowerShell, dans le dossier « Suivi finances ») :
#   .\installer_tache.ps1 -Commande "python maj_linxea.py" -Heure "07:43"
# La tâche tourne chaque jour à l'heure donnée et à l'ouverture de session (si l'heure a été manquée).
param(
  [Parameter(Mandatory=$true)][string]$Commande,
  [string]$Heure = "07:43",
  [string]$Nom = "Suivi finances - Linxea vers Mon Spirit 2"
)
$dossier = (Get-Location).Path
$journal = Join-Path $env:APPDATA "SpiritSync\maj.log"
New-Item -ItemType Directory -Force -Path (Split-Path $journal) | Out-Null
$action = New-ScheduledTaskAction -Execute "cmd.exe" -WorkingDirectory $dossier `
  -Argument "/c $Commande >> `"$journal`" 2>&1"
$declencheurs = @(
  (New-ScheduledTaskTrigger -Daily -At $Heure),
  (New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME)
)
$reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
  -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $Nom -Action $action -Trigger $declencheurs -Settings $reglages `
  -Description "Met à jour le contrat Linxea et le publie chiffré pour l'iPhone" -Force | Out-Null
Write-Host "Tâche « $Nom » créée (chaque jour à $Heure + à l'ouverture de session). Journal : $journal"
Write-Host "Tester tout de suite : Start-ScheduledTask -TaskName `"$Nom`""
