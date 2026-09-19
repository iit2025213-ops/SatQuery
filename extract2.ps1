$content = Get-Content 'c:\Users\SHIVAM BHATT\Downloads\hero\spaceedu.html' -Raw

# Find the last </script> tag (the custom script)
$lastScript = $content.LastIndexOf('</script>')
# Find the <script> before it - this is the custom animation code
$customScriptStart = $content.LastIndexOf('<script>', $lastScript - 1)

# But there's only one <script> block. Let's find the IIFE
$iifeIdx = $content.LastIndexOf('(function(){')
if ($iifeIdx -gt 0) {
    $len = [Math]::Min(12000, $content.Length - $iifeIdx)
    $chunk = $content.Substring($iifeIdx, $len)
    Write-Host $chunk
} else {
    Write-Host "IIFE not found, searching for custom code markers..."
    # Search for KEYS or TEX
    $keysIdx = $content.IndexOf('KEYS')
    Write-Host "KEYS at: $keysIdx"
    $texIdx = $content.IndexOf('TEX_MAP')
    Write-Host "TEX_MAP at: $texIdx"
    $starsIdx = $content.IndexOf('stars')
    Write-Host "stars at: $starsIdx"
    
    # Show around TEX_MAP
    if ($texIdx -gt 0) {
        $start = [Math]::Max(0, $texIdx - 200)
        $chunk = $content.Substring($start, 2000)
        Write-Host "Around TEX_MAP:"
        Write-Host $chunk
    }
}
