$files = Get-ChildItem -Path "I:\Xuguang-NexaOffice\templates" -Filter "*.html" -Recurse

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    
    if ($content -match 'href="#"') {
        $oldText = @"
<div class="nav-item has-dropdown">
                <a href="#">用户中心</a>
                <ul class="dropdown">
                    <li><a href="#">我的文件</a></li>
                    <li><a href="#">处理记录</a></li>
                    <li><a href="#">我的模板</a></li>
                    <li><a href="#">会员中心</a></li>
                    <li><a href="#">账号设置</a></li>
                </ul>
            </div>
"@
        
        $newText = @"
<div class="nav-item has-dropdown">
                <a href="/user/files">用户中心</a>
                <ul class="dropdown">
                    <li><a href="/user/files">我的文件</a></li>
                    <li><a href="/user/history">处理记录</a></li>
                    <li><a href="/user/templates">我的模板</a></li>
                    <li><a href="/user/member">会员中心</a></li>
                    <li><a href="/user/settings">账号设置</a></li>
                </ul>
            </div>
"@
        
        $content = $content.Replace($oldText, $newText)
        Set-Content -Path $file.FullName -Value $content -NoNewline
        Write-Host "Fixed: $($file.Name)"
    }
}

Write-Host "修复完成！"
