<#
.SYNOPSIS
    Offboarding: disable AD users from an HR leavers CSV. Never deletes accounts.

.DESCRIPTION
    Reads a CSV with a single required column: SamAccountName (optional: TicketRef).
    For each user: disable the account, stamp the description with the date and ticket,
    optionally remove group memberships (-RemoveGroups) and move to a disabled OU.
    Run with -WhatIf first. Deletion is intentionally left as a separate, manual step
    after your retention period.

.EXAMPLE
    .\Disable-ADUsersFromCsv.ps1 -CsvPath .\leavers.csv `
        -DisabledOu "OU=Disabled,DC=example,DC=local" -RemoveGroups -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)][string]$CsvPath,
    [string]$DisabledOu,
    [switch]$RemoveGroups,
    [string]$LogPath = ".\ad-disable-log.csv"
)

Import-Module ActiveDirectory -ErrorAction Stop

$log = New-Object System.Collections.Generic.List[object]
$today = Get-Date -Format "yyyy-MM-dd"

foreach ($row in (Import-Csv -Path $CsvPath)) {
    $sam = $row.SamAccountName.Trim()
    $user = Get-ADUser -Filter "SamAccountName -eq '$sam'" -Properties MemberOf, Description -ErrorAction SilentlyContinue
    if (-not $user) {
        $log.Add([pscustomobject]@{ Sam = $sam; Action = "NotFound"; Detail = "" })
        continue
    }

    if ($PSCmdlet.ShouldProcess($sam, "Disable account")) {
        try {
            Disable-ADAccount -Identity $user
            $note = "Disabled $today"
            if ($row.TicketRef) { $note += " ref $($row.TicketRef)" }
            Set-ADUser -Identity $user -Description $note

            if ($RemoveGroups -and $user.MemberOf) {
                foreach ($group in $user.MemberOf) {
                    Remove-ADGroupMember -Identity $group -Members $user -Confirm:$false
                }
            }
            if ($DisabledOu) {
                Move-ADObject -Identity $user.DistinguishedName -TargetPath $DisabledOu
            }
            $log.Add([pscustomobject]@{ Sam = $sam; Action = "Disabled"; Detail = $note })
        }
        catch {
            $log.Add([pscustomobject]@{ Sam = $sam; Action = "Failed"; Detail = $_.Exception.Message })
        }
    }
    else {
        $log.Add([pscustomobject]@{ Sam = $sam; Action = "WhatIf"; Detail = "would disable" })
    }
}

$log | Export-Csv -Path $LogPath -NoTypeInformation -Encoding UTF8
$log | Format-Table -AutoSize
Write-Host "Log written to $LogPath"
