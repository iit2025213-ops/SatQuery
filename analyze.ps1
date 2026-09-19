$lines = Get-Content 'c:\Users\SHIVAM BHATT\Downloads\hero\spaceedu.html'
Write-Host "Total lines: $($lines.Count)"
for($i=0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if($line.Length -lt 500) {
        Write-Host "$($i+1): $line"
    } else {
        Write-Host "$($i+1): [LINE LENGTH: $($line.Length)] $($line.Substring(0, 200))..."
    }
}
