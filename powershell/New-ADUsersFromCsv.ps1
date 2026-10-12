<#
.SYNOPSIS
    Create Active Directory users from an HR joiners CSV.

.DESCRIPTION
    Reads a CSV with columns: GivenName, Surname, Department, Title, Manager (sAMAccountName, optional).
    Creates enabled accounts in the target OU with "must change password at next logon".
    The initial password is supplied once as a SecureString and is never written to disk or the log.
    Supports -WhatIf so you can preview every change first. Existing users are skipped.

.EXAMPLE
    $pw = Read-Host "Initial password" -AsSecureString
    .\New-ADUsersFromCsv.ps1 -CsvPath .\joiners.csv -OuPath "OU=Staff,DC=example,DC=local" `
        -UpnSuffix "example.local" -InitialPassword $pw -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)][string]$CsvPath,
    [Parameter(Mandatory)][string]$OuPath,
    [Parameter(Mandatory)][string]$UpnSuffix,
    [Parameter(Mandatory)][securestring]$InitialPassword,
    [string]$LogPath = ".\ad-create-log.csv"
)

Import-Module ActiveDirectory -ErrorAction Stop

$log = New-Object System.Collections.Generic.List[object]

foreach ($row in (Import-Csv -Path $CsvPath)) {
    $given = $row.GivenName.Trim()
    $sur = $row.Surname.Trim()
    $sam = ("{0}.{1}" -f $given, $sur).ToLower() -replace '[^a-z0-9._-]', ''
    if ($sam.Length -gt 20) { $sam = $sam.Substring(0, 20) }

    if (Get-ADUser -Filter "SamAccountName -eq '$sam'" -ErrorAction SilentlyContinue) {
        $log.Add([pscustomobject]@{ Sam = $sam; Action = "Skipped"; Detail = "already exists" })
        continue
    }

    $params = @{
        Name                  = "$given $sur"
        GivenName             = $given
        Surname               = $sur
        SamAccountName        = $sam
        UserPrincipalName     = "$sam@$UpnSuffix"
        Path                  = $OuPath
        Department            = $row.Department
        Title                 = $row.Title
        AccountPassword       = $InitialPassword
        ChangePasswordAtLogon = $true
        Enabled               = $true
    }
    if ($row.Manager) { $params["Manager"] = $row.Manager }

    if ($PSCmdlet.ShouldProcess($sam, "Create AD user")) {
        try {
            New-ADUser @params
            $log.Add([pscustomobject]@{ Sam = $sam; Action = "Created"; Detail = $row.Department })
        }
        catch {
            $log.Add([pscustomobject]@{ Sam = $sam; Action = "Failed"; Detail = $_.Exception.Message })
        }
    }
    else {
        $log.Add([pscustomobject]@{ Sam = $sam; Action = "WhatIf"; Detail = "would create" })
    }
}

$log | Export-Csv -Path $LogPath -NoTypeInformation -Encoding UTF8
$log | Format-Table -AutoSize
Write-Host "Log written to $LogPath"
