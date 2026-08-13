// Copyright Echoes of the Architects. All Rights Reserved.

using UnrealBuildTool;

public class EchoesTarget : TargetRules
{
	public EchoesTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		// V6 matches the settings the installed 5.7.4 engine was compiled with.
		// Lower versions flip UndefinedIdentifierWarningLevel and UBT rejects the
		// target for sharing build products with the precompiled UnrealEditor.
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;

		ExtraModuleNames.Add("Echoes");
	}
}
