#define MyAppName "Quant Lab"
#ifndef MyAppVersion
  #define MyAppVersion "2.3.0-rc.1"
#endif
#ifndef MyAppFileVersion
  #define MyAppFileVersion "2.3.0.0"
#endif
#define MyAppExeName "QuantLab.exe"
#ifndef MyPayloadDir
  #define MyPayloadDir "..\dist\QuantLab"
#endif

[Setup]
AppId={{1F4CE834-8E9B-4F8B-A228-FD09E48E60D3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppFileVersion}
AppPublisher=Quant Lab
DefaultDirName={autopf}\Quant Lab CN-HK
DefaultGroupName=Quant Lab
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\dist\installer
OutputBaseFilename=QuantLab-CN-HK-Setup
SetupIconFile=..\assets\quantlab.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "{#MyPayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Quant Lab"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Quant Lab"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 Quant Lab"; Flags: nowait postinstall skipifsilent
