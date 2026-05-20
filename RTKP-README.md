RTKP — small helper to run PowerShell commands through `rtk`
=============================================================

What
----
`scripts/rtkp.ps1` is a tiny wrapper that encodes a given PowerShell command
and runs it with `rtk pwsh -NoProfile -EncodedCommand <base64>`. It avoids
quoting issues when invoking PowerShell cmdlets through the `rtk` proxy.

Quick install (recommended)
---------------------------
1. Add this line to your PowerShell profile (`$PROFILE`) to create an `rtkp`
   function that uses the repository script (adjust path if you store it
   elsewhere):

   ```powershell
   function rtkp { & "${PWD}\scripts\rtkp.ps1" @args }
   Set-Alias rtkp rtkp -Scope Global
   ```

2. Restart your shell (or `.`-source your profile).

Examples
--------

Run a single cmdlet safely:

```powershell
rtkp Remove-Item -Path 'DeleteMe.md' -Force
```

Run a local script file:

```powershell
rtkp .\build\scripts\deploy.ps1
```

Open an interactive PowerShell under rtk (useful for debugging):

```powershell
rtkp
```

Notes
-----
- This wrapper depends on `rtk` being on your PATH. If `rtk` is not in PATH,
  use the full path to `rtk.exe` in the script or update your PATH.
- The script intentionally uses UTF-16LE encoding (PowerShell's `-EncodedCommand`
  expects Unicode) to avoid cross-shell quoting issues.
