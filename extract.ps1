$content = Get-Content 'c:\Users\SHIVAM BHATT\Downloads\hero\spaceedu.html' -Raw
$idx = $content.IndexOf('(function()')
if ($idx -gt 0) {
    $len = [Math]::Min(8000, $content.Length - $idx)
    $chunk = $content.Substring($idx, $len)
    Write-Host $chunk
}
