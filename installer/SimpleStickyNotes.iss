#define MyAppName "Simple Sticky Notes"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Josh Whitk"
#define MyAppExeName "Simple Sticky Notes.exe"

[Setup]
AppId={{2A8422D1-D03D-4702-B66A-16E273A3F7C7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Simple Sticky Notes
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=Simple-Sticky-Notes-Setup

[Files]
Source: "..\dist\Simple Sticky Notes\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Simple Sticky Notes"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install-windows-integration"; Flags: runhidden waituntilterminated

[Code]
var
  StoragePage: TInputDirWizardPage;

function ReversePosEx(const SubText, S: String; StartIndex: Integer): Integer;
var
  I: Integer;
begin
  Result := 0;
  if StartIndex > Length(S) then
    StartIndex := Length(S);
  for I := StartIndex downto 1 do
  begin
    if Copy(S, I, Length(SubText)) = SubText then
    begin
      Result := I;
      exit;
    end;
  end;
end;

function JsonUnescape(const Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '\\', '\', True);
  StringChangeEx(Result, '\/', '/', True);
end;

function ExtractVaultPathFromObsidianConfig(const ConfigText: String): String;
var
  OpenPos: Integer;
  PathPos: Integer;
  StartPos: Integer;
  EndPos: Integer;
  RawValue: String;
begin
  Result := '';
  OpenPos := Pos('"open":true', ConfigText);
  if OpenPos > 0 then
    PathPos := ReversePosEx('"path":"', ConfigText, OpenPos)
  else
    PathPos := Pos('"path":"', ConfigText);

  if PathPos = 0 then
    exit;

  StartPos := PathPos + Length('"path":"');
  EndPos := StartPos;
  while (EndPos <= Length(ConfigText)) and (ConfigText[EndPos] <> '"') do
    EndPos := EndPos + 1;
  RawValue := Copy(ConfigText, StartPos, EndPos - StartPos);
  Result := JsonUnescape(RawValue);
end;

function DetectedObsidianStorageRoot(): String;
var
  ConfigPath: String;
  ConfigText: AnsiString;
  VaultPath: String;
begin
  Result := ExpandConstant('{userdocs}\Simple Sticky Notes');
  ConfigPath := ExpandConstant('{userappdata}\Obsidian\obsidian.json');
  if not FileExists(ConfigPath) then
    exit;

  if not LoadStringFromFile(ConfigPath, ConfigText) then
    exit;

  VaultPath := ExtractVaultPathFromObsidianConfig(ConfigText);
  if VaultPath = '' then
    exit;

  Result := AddBackslash(VaultPath) + 'Simple Sticky Notes';
end;

function EscapeJson(const Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '\', '\\', True);
end;

procedure InitializeWizard();
begin
  StoragePage := CreateInputDirPage(
    wpSelectDir,
    'Sticky Note Storage',
    'Choose where Simple Sticky Notes should store note files.',
    'If you already use Obsidian, keep this inside the detected vault unless you want a separate folder.',
    False,
    ''
  );
  StoragePage.Add('');
  StoragePage.Values[0] := DetectedObsidianStorageRoot();
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsDir: String;
  SettingsPath: String;
  SettingsJson: String;
begin
  if CurStep <> ssPostInstall then
    exit;

  SettingsDir := ExpandConstant('{userappdata}\SimpleStickyNotes');
  ForceDirectories(SettingsDir);
  SettingsPath := AddBackslash(SettingsDir) + 'settings.json';
  SettingsJson :=
    '{' + #13#10 +
    '  "storage_root": "' + EscapeJson(StoragePage.Values[0]) + '",' + #13#10 +
    '  "font_family": "Arial",' + #13#10 +
    '  "font_size": 14,' + #13#10 +
    '  "default_width": 360,' + #13#10 +
    '  "default_height": 260,' + #13#10 +
    '  "autosave_delay_ms": 700' + #13#10 +
    '}';
  SaveStringToFile(SettingsPath, SettingsJson, False);
end;
