; Inno Setup Script for Neology Average Speed
; Requires Inno Setup 6.x  -  https://jrsoftware.org/isinfo.php
;
; Build steps:
;   1. Run PyInstaller:  pyinstaller neology_average_speed.spec
;   2. Compile this script in the Inno Setup IDE, or from the command line:
;      "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" neology_average_speed_installer.iss

#define AppName      "Neology Average Speed"
#define AppVersion   "20260415.1434"
#define AppPublisher "Neology"
#define AppExeName   "NeologyAverageSpeed.exe"
#define BuildDir     "dist\NeologyAverageSpeed"

[Setup]
; Unique GUID - regenerate with Tools > Generate GUID if you fork the project
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://www.neology.net
AppSupportURL=https://www.neology.net
AppUpdatesURL=https://www.neology.net

; Default install location — per-machine so all users can run it
DefaultDirName={autopf}\{#AppPublisher}\{#AppName}
DefaultGroupName={#AppPublisher}\{#AppName}

; Allow the user to choose between per-machine and per-user install
PrivilegesRequiredOverridesAllowed=dialog

; Output installer details
OutputDir=installer_output
OutputBaseFilename=NeologyAverageSpeed_Setup_{#AppVersion}
SetupIconFile=neology2.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Minimum Windows version — Windows 10
MinVersion=10.0

; Show a license page if you have one (comment out if not)
; LicenseFile=LICENSE.txt

; Installer appearance
WizardStyle=modern
WizardSizePercent=120
DisableWelcomePage=no

; Version info embedded in the installer executable
VersionInfoVersion=0.1.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion=0.1.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop shortcut is opt-in — tick by default
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; --- Main application bundle (output of PyInstaller COLLECT) ---
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- Default JSON config ---
; Placed in the install folder so the app can find it via resourcesPath (os.getcwd()
; or the folder containing the exe). Marked excludedfromshown so it doesn't appear
; in the uninstaller file list prominently.  Use "onlyifdoesntexist" so a user's
; existing config is never overwritten on upgrade.
Source: "neology_average_speed.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

; --- Application icon (for Add/Remove Programs) ---
Source: "neology2.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}";        FileName: "{app}\{#AppExeName}"; IconFilename: "{app}\neology2.ico"
Name: "{group}\Uninstall {#AppName}"; FileName: "{uninstallexe}"

; Desktop shortcut (only created if the task above is ticked)
Name: "{autodesktop}\{#AppName}"; FileName: "{app}\{#AppExeName}"; IconFilename: "{app}\neology2.ico"; Tasks: desktopicon

[Run]
; Offer to launch the app after installation
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up log files or temp data written by the app to the install folder
Type: filesandordirs; Name: "{app}\logs"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
