; Buildado no Windows com Inno Setup 6 (ISCC.exe).
#define AppName "MARKYS - Controle de Folgas"
#define AppVersion "0.4.0"
#define AppPublisher "MARKYS"
#define AppExeName "MARKYS.exe"

[Setup]
AppId={{5F8B6A21-7F4B-4A0B-9C3A-1F4C67A0C2D8}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\MARKYS
DefaultGroupName=MARKYS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist-installer
OutputBaseFilename=MARKYS-Controle-de-Folgas-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
Uninstallable=yes
CloseApplications=yes
RestartApplications=no

[Dirs]
Name: "{localappdata}\MARKYS"; Flags: uninsneveruninstall

[Files]
Source: "..\dist\MARKYS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\USO-INSTALADOR.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\INSTALACAO-WINDOWS.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\MARKYS - Controle de Folgas"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{localappdata}\MARKYS"
Name: "{autoprograms}\MARKYS - Controle de Folgas"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{localappdata}\MARKYS"
Name: "{autoprograms}\MARKYS - Recuperar acesso"; Filename: "{app}\{#AppExeName}"; Parameters: "--reset-admin"; WorkingDir: "{localappdata}\MARKYS"; Comment: "Redefine a senha local sem apagar os dados"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar MARKYS"; Flags: postinstall nowait skipifsilent
