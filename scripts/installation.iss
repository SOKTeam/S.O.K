; --- CONFIGURATION GENERALE ---
#define MyAppName "S.O.K"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SOK Team"
#define MyAppURL "https://www.example.com/"
#define MyAppExeName "SOK.exe"

; Chemin vers le dossier généré par Nuitka (main.dist)
#define MyNuitkaBuildPath "..\dist\main.dist"

[Setup]
AppId={{0AE69055-4736-406C-93BB-0086D3F0E38A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog

; Sortie de l'installeur
OutputDir=..\dist
OutputBaseFilename=SOK_Setup_v1.0.0
SetupIconFile=..\src\sok\resources\assets\logo.ico
SolidCompression=yes
WizardStyle=modern windows11

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyNuitkaBuildPath}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyNuitkaBuildPath}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\assets\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\assets\logo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
