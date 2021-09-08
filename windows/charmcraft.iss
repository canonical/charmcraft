[Setup]
AppId={{05E40DED-CE0A-437E-B90C-25A32B47880F}
AppName=Charmcraft (Preview) for Windows
AppVersion=VERSION
AppPublisher=Canonical Ltd.
AppPublisherURL=https://charmhub.io/
AppSupportURL=https://charmhub.io/
AppUpdatesURL=https://charmhub.io/
DefaultDirName={autopf}\Charmcraft for Windows
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=charmcraft.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputBaseFilename=charmcraft-installer
OutputDir=..\dist
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: modifypath; Description: "Add charmcraft to the current user's PATH (Recommended)"

[Files]
Source: "..\dist\charmcraft.exe"; DestDir: "{app}"; Flags: ignoreversion

[Code]
const
  ModPathName = 'modifypath';
  ModPathType = 'user';

function ModPathDir(): TArrayOfString;
begin
  SetArrayLength(Result, 1);
  Result[0] := ExpandConstant('{app}');
end;
#include "modpath.iss"

procedure CurStepChanged(CurStep: TSetupStep);
var
  Success: Boolean;
begin
  Success := True;
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected(ModPathName) then
      ModPath();
  end;
end;
