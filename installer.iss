; Inno Setup Script for Sticky Notes
; Configured for non-admin per-user installation in %LOCALAPPDATA%\Programs\StickyNotes

#define MyAppName "Sticky Notes"
#ifndef MyAppVersion
  #define MyAppVersion "1.5.6"
#endif
#define MyAppPublisher "David Alexander M."
#define MyAppURL "https://github.com/DavidAlexanderM/sticky_notes_releases"
#define MyAppExeName "StickyNotes.exe"

[Setup]
; Unique GUID for Sticky Notes
AppId={{E1F5C0B7-9654-4B42-B9E4-42861F9CF8DA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\StickyNotes
DisableDirPage=no
DisableProgramGroupPage=yes
; Per-user install: avoids Windows UAC administrator elevation prompts!
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=StickyNotes_Setup_v{#MyAppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\StickyNotes.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\StickyNotes\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "DavidAlexanderM.StickyNotes"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "DavidAlexanderM.StickyNotes"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
