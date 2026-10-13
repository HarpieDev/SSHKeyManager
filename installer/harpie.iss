#ifndef AppVersion
  #error AppVersion must be supplied by tools/build_installer.ps1
#endif
#ifndef PackageDir
  #error PackageDir must be supplied by tools/build_installer.ps1
#endif

[Setup]
AppId={{BE64FA2D-A7A8-4A75-989A-301247B25C3D}
AppName=Harpie
AppVersion={#AppVersion}
AppPublisher=HarpieDev
AppPublisherURL=https://github.com/HarpieDev/SSHKeyManager
AppSupportURL=https://github.com/HarpieDev/SSHKeyManager/issues
AppUpdatesURL=https://github.com/HarpieDev/SSHKeyManager/releases
DefaultDirName={localappdata}\Programs\Harpie
DefaultGroupName=Harpie
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\release
OutputBaseFilename=Harpie-{#AppVersion}-setup-x64
SetupIconFile=..\assets\icons\harpie.ico
UninstallDisplayIcon={app}\Harpie.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousLanguage=yes
VersionInfoVersion={#AppVersion}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Harpie"; Filename: "{app}\Harpie.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Harpie"; Filename: "{app}\Harpie.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Harpie.exe"; Parameters: "--language {language}"; Description: "{cm:LaunchProgram,Harpie}"; Flags: nowait postinstall skipifsilent

; User identities, metadata, logs, and preferences are outside {app}.
; No [UninstallDelete] entry removes user data.
