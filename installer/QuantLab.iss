#define MyAppName "Quant Lab CN/HK"
#ifndef MyAppVersion
  #define MyAppVersion "2.0.0-rc.1"
#endif
#ifndef MyAppFileVersion
  #define MyAppFileVersion "2.0.0.0"
#endif
#define MyAppExeName "QuantLab.exe"

[Setup]
AppId={{1F4CE834-8E9B-4F8B-A228-FD09E48E60D3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppFileVersion}
AppPublisher=Quant Lab CN/HK
DefaultDirName={autopf}\Quant Lab CN-HK
DefaultGroupName=Quant Lab CN-HK
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
Source: "..\dist\QuantLab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Quant Lab CN-HK"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Quant Lab CN-HK"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 Quant Lab CN/HK"; Flags: nowait postinstall skipifsilent
