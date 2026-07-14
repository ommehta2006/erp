# Credentials And Access

This file explains where local credentials are stored for automation. Do not paste tokens into committed files.

## Local Credential Files

Use these existing local files:

- GitHub PAT file: `D:\Frappe-AI\erp\github`
- Railway/Vercel/Supabase details file: `D:\Frappe-AI\erp\all_details`

These files are intentionally outside this handoff as raw secret sources. Read them locally when deploying.

## Live Access

- Backend: `https://erp-production-8664.up.railway.app`
- Backend health: `https://erp-production-8664.up.railway.app/api/health`
- Frontend: `https://erp-factorypulse.vercel.app`
- Login email: `admin@gmail.com`
- Login password: `admin`

## GitHub Push Command Pattern

Use the token from `D:\Frappe-AI\erp\github` without printing it:

```powershell
$lines = Get-Content -LiteralPath 'D:\Frappe-AI\erp\github'
$pat = ($lines | Where-Object { $_ -match '^github_pat_' } | Select-Object -First 1).Trim()
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$pat"))
git -c safe.directory='D:/Frappe-AI/erp' -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $basic" -C 'D:\Frappe-AI\erp' push origin master
```

## Railway Deploy Pattern

Use the Railway token from `D:\Frappe-AI\erp\all_details`:

```powershell
$details = Get-Content -LiteralPath 'D:\Frappe-AI\erp\all_details' -Raw
$railwayToken = [regex]::Match($details, 'railway_token:([^\r\n]+)').Groups[1].Value.Trim()
$commit = (git -c safe.directory='D:/Frappe-AI/erp' -C 'D:\Frappe-AI\erp' rev-parse HEAD).Trim()
$query = @'
mutation Deploy($serviceId: String!, $environmentId: String!, $commitSha: String!) {
  serviceInstanceDeployV2(serviceId: $serviceId, environmentId: $environmentId, commitSha: $commitSha)
}
'@
$body = @{
  query = $query
  variables = @{
    serviceId = 'ed3bf283-5b9a-4466-b497-a5969c96afb7'
    environmentId = '6e28a927-4f52-4495-8329-d01b5ad6760f'
    commitSha = $commit
  }
} | ConvertTo-Json -Depth 6
$headers = @{ Authorization = "Bearer $railwayToken"; 'Content-Type' = 'application/json' }
Invoke-RestMethod -Uri 'https://backboard.railway.app/graphql/v2' -Method Post -Headers $headers -Body $body
```

## Vercel Deploy Pattern

Run from the frontend folder:

```powershell
cd D:\Frappe-AI\erp\frontend
npx.cmd vercel deploy --prod --yes
```

## Secret Safety

- Do not commit `github`, `all_details`, `.env`, or copied secret files.
- Do not print full tokens in final answers.
- If tokens were exposed in logs or chat, rotate them before production.

